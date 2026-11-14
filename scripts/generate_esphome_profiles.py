#!/usr/bin/env python3
"""Generate self-contained public ESPHome YAML from the package compositions.

Rendering inputs contain only synthetic credentials. ESPHome itself merges the
packages; this script converts those known marker values into !secret references
and verifies that the resulting standalone YAML validates to the same config.
"""

from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "examples" / "reference"
PACKAGE_DIR = ROOT / "packages"
OUTPUT_DIR = ROOT / "ESPHome"
PROFILES = {
    "normal": OUTPUT_DIR / "WaveshareESP32S3PhotoPainter73e6-example.yaml",
    "diagnostic": OUTPUT_DIR / "WaveshareESP32S3PhotoPainter73e6-diag.yaml",
}
MARKERS = {
    "wifi_ssid": "__REFERENCE_WIFI_SSID__",
    "wifi_password": "__REFERENCE_WIFI_PASSWORD__",
    "fallback_password": "__REFERENCE_FALLBACK_PASSWORD__",
    "web_server_password": "__REFERENCE_WEB_SERVER_PASSWORD__",
    "api_encryption_key": "UEhPVE9QQUlOVEVSLVJFRkVSRU5DRS1LRVktTUFSSyE=",
}
INCLUDE_RE = re.compile(r"!include\s+([^\s#]+)")


class SecretRef(str):
    """A YAML scalar emitted as !secret KEY, never as a resolved value."""


class LambdaRef(str):
    """ESPHome lambda expression retained after package flattening."""


class ConfigLoader(yaml.SafeLoader):
    pass


def construct_lambda(loader: ConfigLoader, node: yaml.ScalarNode) -> LambdaRef:
    return LambdaRef(loader.construct_scalar(node))


ConfigLoader.add_constructor("!lambda", construct_lambda)


class PublicDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: object) -> bool:
        return True

    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, indentless=False)


def represent_text(dumper: PublicDumper, value: str) -> yaml.ScalarNode:
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str", value, style="|" if "\n" in value else None
    )


def represent_secret(dumper: PublicDumper, value: SecretRef) -> yaml.ScalarNode:
    return dumper.represent_scalar("!secret", str(value))


def represent_lambda(dumper: PublicDumper, value: LambdaRef) -> yaml.ScalarNode:
    return dumper.represent_scalar(
        "!lambda", str(value), style="|" if "\n" in value else None
    )


PublicDumper.add_representer(str, represent_text)
PublicDumper.add_representer(SecretRef, represent_secret)
PublicDumper.add_representer(LambdaRef, represent_lambda)


def check_public_sources() -> None:
    """Keep the renderer's entire input graph within known public files."""
    sources = set(INPUT_DIR.glob("*.yaml")) | set(PACKAGE_DIR.rglob("*.yaml"))
    allowed = {path.resolve() for path in sources if not path.is_symlink()}
    if len(sources) != len(allowed):
        raise ValueError("Rendering sources may not be symlinks")
    for source in sorted(sources):
        contents = source.read_text(encoding="utf-8")
        if "!secret" in contents or "!env_var" in contents:
            raise ValueError(f"Private or environment value in renderer source: {source}")
        if "github://" in contents:
            raise ValueError(f"Remote package in renderer source: {source}")
        for included in INCLUDE_RE.findall(contents):
            target = (source.parent / included).resolve()
            if target not in allowed:
                raise ValueError(f"Include escapes public rendering sources: {source}: {included}")


def esphome_config(executable: str, path: Path) -> dict:
    environment = os.environ.copy()
    # All rendering inputs share the package fixture's font cache. ESPHome's
    # default cache otherwise follows each temporary config directory.
    environment.setdefault("ESPHOME_DATA_DIR", str(ROOT / "examples" / ".esphome"))
    result = subprocess.run(
        [executable, "config", "--show-secrets", "--no-defaults", str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    if result.returncode:
        # Sources and staged outputs carry synthetic values only. Keep any
        # diagnostics out of the generated public files.
        raise RuntimeError(
            f"ESPHome rejected {path.name} (exit {result.returncode}):\n"
            f"{result.stdout[-4000:]}\n{result.stderr[-4000:]}"
        )
    config = yaml.load(result.stdout, Loader=ConfigLoader)
    if not isinstance(config, dict):
        raise ValueError(f"ESPHome did not return a mapping for {path}")
    if "packages" in config:
        raise ValueError(f"ESPHome did not flatten packages for {path}")
    # The CLI has already expanded the package substitutions into concrete
    # fields; retaining a substitutions block would imply they still work.
    config.pop("substitutions", None)
    return config


def make_standalone(config: dict, profile: str) -> str:
    config = copy.deepcopy(config)
    fields = (
        (config["wifi"], "ssid", "wifi_ssid"),
        (config["wifi"], "password", "wifi_password"),
        (config["wifi"]["ap"], "password", "fallback_password"),
        (config["api"]["encryption"], "key", "api_encryption_key"),
        (config["web_server"]["auth"], "password", "web_server_password"),
    )
    for mapping, field, secret_name in fields:
        expected = MARKERS[secret_name]
        if mapping.get(field) != expected:
            raise ValueError(f"Unexpected {secret_name} marker in {profile} profile")
        mapping[field] = SecretRef(secret_name)

    rendered = yaml.dump(
        config, Dumper=PublicDumper, sort_keys=False, allow_unicode=True, width=100
    )
    # An empty mapping such as `ota: encryption:` (encrypt with the API key) dumps
    # as `encryption: null`, which reads as "disabled". Emit the bare key the
    # ESPHome documentation uses; verify_standalone() proves it is equivalent.
    rendered = re.sub(r"^(\s+encryption): null$", r"\1:", rendered, flags=re.MULTILINE)
    if any(marker in rendered for marker in MARKERS.values()):
        raise ValueError(f"Synthetic credential marker survived in {profile} output")
    header = (
        "# Generated from packages/ by scripts/generate_esphome_profiles.py.\n"
        f"# Composition: examples/reference/{profile}.yaml.\n"
        "# Edit the package or rendering input and regenerate; this is a standalone download.\n"
        "# Supply wifi_ssid, wifi_password, fallback_password, api_encryption_key, and\n"
        "# web_server_password in the ESPHome installation's secrets.yaml.\n\n"
    )
    return header + rendered


def verify_standalone(executable: str, rendered: str, expected: dict, profile: str) -> None:
    """Validate generated YAML and prove the package merge survived rendering."""
    with tempfile.TemporaryDirectory(prefix="photopainter-reference-") as directory:
        stage = Path(directory)
        config_path = stage / f"{profile}.yaml"
        config_path.write_text(rendered, encoding="utf-8")
        (stage / "secrets.yaml").write_text(
            yaml.safe_dump(MARKERS, sort_keys=True), encoding="utf-8"
        )
        actual = esphome_config(executable, config_path)
        if actual != expected:
            raise ValueError(f"Generated {profile} profile differs from the package merge")


def write_output(path: Path, rendered: str) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing to replace symlink: {path}")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
        suffix=".tmp", delete=False
    ) as output:
        temporary_path = Path(output.name)
        try:
            output.write(rendered)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
    os.replace(temporary_path, path)


def compile_standalone(executable: str, profile: str, rendered: str) -> None:
    stage = ROOT / "build" / "reference-verification" / profile
    stage.mkdir(parents=True, exist_ok=True)
    config_path = stage / "config.yaml"
    secrets_path = stage / "secrets.yaml"
    log_path = stage / "compile.log"
    config_path.write_text(rendered, encoding="utf-8")
    secrets_path.write_text(yaml.safe_dump(MARKERS, sort_keys=True), encoding="utf-8")
    environment = os.environ.copy()
    environment.setdefault("ESPHOME_DATA_DIR", str(ROOT / "examples" / ".esphome"))
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            [executable, "compile", str(config_path)], cwd=ROOT,
            stdout=log, stderr=subprocess.STDOUT, text=True, env=environment,
            check=False,
        )
    if result.returncode:
        tail = "\n".join(log_path.read_text(encoding="utf-8").splitlines()[-50:])
        raise RuntimeError(
            f"{profile} standalone compile failed (exit {result.returncode}); "
            f"log: {log_path}\n{tail}"
        )
    print(f"Compiled {profile} standalone profile; log: {log_path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail if committed downloads are stale"
    )
    parser.add_argument(
        "--compile", action="store_true",
        help="also compile each standalone download using synthetic credentials",
    )
    parser.add_argument(
        "--esphome-bin", default=os.environ.get("ESPHOME_BIN", "esphome"),
        help="ESPHome executable (default: ESPHOME_BIN or esphome)",
    )
    args = parser.parse_args()
    executable = shutil.which(args.esphome_bin)
    if executable is None:
        raise ValueError(f"ESPHome executable not found: {args.esphome_bin}")

    check_public_sources()
    generated: dict[Path, str] = {}
    for profile, destination in PROFILES.items():
        source = INPUT_DIR / f"{profile}.yaml"
        merged = esphome_config(executable, source)
        rendered = make_standalone(merged, profile)
        verify_standalone(executable, rendered, merged, profile)
        generated[destination] = rendered

    if args.check:
        stale = [path for path, content in generated.items()
                 if not path.is_file() or path.read_text(encoding="utf-8") != content]
        if stale:
            names = ", ".join(str(path.relative_to(ROOT)) for path in stale)
            raise ValueError(f"Generated profile(s) are stale: {names}; run {__file__}")
        print("Generated standalone profiles are current and match package merges.")
        if args.compile:
            for profile, destination in PROFILES.items():
                compile_standalone(executable, profile, generated[destination])
        return 0

    for path, content in generated.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            write_output(path, content)
            print(f"Updated {path.relative_to(ROOT)}")
        else:
            print(f"Current {path.relative_to(ROOT)}")
    if args.compile:
        for profile, destination in PROFILES.items():
            compile_standalone(executable, profile, generated[destination])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
