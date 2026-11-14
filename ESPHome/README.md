# ESPHome package design

The ESPHome package is the primary deliverable for this board. The complete
normal and diagnostic YAML files are generated reference implementations and
optional independent downloads. The package is the maintained hardware source;
consumers do not need to copy its inline lambdas.

`Office-PhotoPainter.yaml` and `Office-PhotoPainter.bk.yaml` are private,
ignored working files. The public profile generator does not read or update
them. The old private-source renderer, `scripts/sync_esphome_profiles.py`, is
retained locally for historical work and is not part of the public workflow.
The new deep-sleep behavior was first added to the private
`Office-PhotoPainter.yaml` for bench testing, then mirrored into the package
demo fragment. Until the private test is retired, changes to either sleep path
must be reviewed against the other; only the package generates the public
normal and diagnostic downloads.

## Package structure

The stable public entry points live at the top of [`packages/`](../packages/):

| Entry point | Adds |
| --- | --- |
| [`waveshare-esp32-s3-photopainter.yaml`](../packages/waveshare-esp32-s3-photopainter.yaml) | Platform, buses, PMIC initialization/recovery, telemetry, SD storage, buttons, LEDs, audio/display hardware, and safe power controls. |
| [`waveshare-esp32-s3-photopainter-demo.yaml`](../packages/waveshare-esp32-s3-photopainter-demo.yaml) | Dashboard with readiness-gated first refresh, RTTTL, SD voice-note recording/playback, and manually requested deep sleep. |
| [`waveshare-esp32-s3-photopainter-diagnostic.yaml`](../packages/waveshare-esp32-s3-photopainter-diagnostic.yaml) | DEBUG logging, runtime state reporting, and read-only register snapshots at boot and on request. |
| [`waveshare-esp32-s3-photopainter-battery.yaml`](../packages/waveshare-esp32-s3-photopainter-battery.yaml) | Slower polling and logical codec/amplifier shutdown after boot. This is not yet a measured low-power profile. |

The directory below the entry points is an implementation detail organized as
`core/`, `hardware/`, `controls/`, `demos/`, `diagnostics/`, and `policies/`. Consumers
should include an entry point rather than individual internal fragments, so the
implementation can be reorganized without changing their configuration.

Representative local consumers live in [`examples/`](../examples/). They omit
Wi-Fi, API, OTA, and secrets on purpose; an installation adds those stanzas in
its own file.

## Standalone downloads

[`scripts/generate_esphome_profiles.py`](../scripts/generate_esphome_profiles.py)
renders the two complete YAMLs in this directory using ESPHome's package merge.
Its rendering inputs live in [`examples/reference/`](../examples/reference/):
normal composes the demo entry point; diagnostic composes the diagnostic entry
point and the same demo dashboard/audio fragments. The diagnostic composition
includes core only once. The synthetic site input supplies identity, API, OTA,
Wi-Fi, and the fallback access point; the script converts its known credential
markers to `!secret` references before publishing either download.

Run from any directory:

```sh
python3 /path/to/repo/scripts/generate_esphome_profiles.py
python3 /path/to/repo/scripts/generate_esphome_profiles.py --check
python3 /path/to/repo/scripts/generate_esphome_profiles.py --check --compile
```

The generator needs ESPHome and PyYAML. `ESPHOME_BIN` selects another ESPHome
executable. Every run validates the rendering inputs and checks that each
standalone file resolves to the same configuration. `--check` also fails if
either committed download is stale. `--compile` builds both downloads with
synthetic credentials; its logs are under ignored `build/reference-verification/`.
The package verification script runs `--check` before its own four consumer
checks. Source changes that affect a download therefore require regeneration.

The generated files have concrete values for package substitutions. Installers
can edit a standalone copy, while package consumers should set their own
substitutions in the local consumer configuration.

## Consumer and package ownership

The consumer owns installation-specific configuration:

- `esphome.name`, `friendly_name`, and `area`;
- Wi-Fi credentials and fallback access-point policy;
- API encryption credentials;
- OTA credentials or other site security policy; and
- local integrations or overrides that are not properties of the board.

The package owns the reusable board implementation:

- ESP32 variant, framework, flash, and PSRAM requirements;
- fixed GPIO, I2C, SPI, I2S, display, and other supplied peripheral definitions;
- early PMIC and rail initialization;
- board-safety constraints and package-provided display or audio state machines;
- board entities, telemetry, recovery behavior, and diagnostics; and
- `esphome.project`, required headers, and package-owned boot automations.

This division does not require either side to declare a complete set of ESPHome
stanzas. A package is a configuration fragment. Its correctness is tested by
merging it into a representative consumer configuration.

## Merge contract

ESPHome merges package definitions into the consumer configuration:

- mappings are merged key by key;
- component-list entries with the same explicit `id` are merged;
- lists without mergeable component IDs are concatenated; and
- for other conflicting values, the later value replaces the earlier value.

Consequently, both the package and consumer may declare `esphome:`. For example,
the package can provide:

```yaml
esphome:
  project:
    name: edennelson.waveshare-esp32s3-photopainter
    version: "1.0.0"
  on_boot:
    - priority: 790
      then:
        # Board initialization supplied by the package.
```

The consumer can provide:

```yaml
esphome:
  name: office-photopainter
  friendly_name: Office PhotoPainter
  area: Office
```

The resolved `esphome:` mapping contains all of those keys. Consumer boot
automations may coexist with package boot automations because the list is
combined; explicit priorities must be used whenever their order matters.

The same pattern applies to other mappings. A package may set
`api.reboot_timeout`, while the consumer supplies `api.encryption.key`.

## Secrets and substitutions

A remote package cannot contain `!secret` lookups. Secrets remain in the local
consumer configuration:

```yaml
packages:
  photopainter: github://edennelson/Waveshare-ESP32-S3-PhotoPainter/packages/waveshare-esp32-s3-photopainter.yaml@v1.0.0

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

api:
  encryption:
    key: !secret api_encryption_key
```

Those component mappings merge with any non-secret keys supplied by the package.
There is no need to proxy credentials, device identity, or other naturally
mergeable settings through package substitutions.

Substitutions are appropriate only when the package implementation directly
references a value that consumers are expected to select, such as a default
polling interval or a feature option. Package defaults may be provided for those
values, and a consumer substitution with the same name overrides the default.

## Extensibility rules

Every package component that consumers may reasonably customize must have a
stable, documented `id`. This makes ESPHome's component-list merge behavior
predictable and permits targeted `!extend` and `!remove` operations. Anonymous
list entries should be used only where concatenation is intentional.

Consumer overrides must not be allowed to violate settled board-safety
constraints. In particular, the supported configuration keeps ALDO3 energized
because removing that audio rail clamps the shared I2C bus through the unpowered
audio codecs. Audio power-down uses the documented ES8311/ES7210 low-power
states and GPIO7 amplifier disable. ALDO4 remains independently switchable after
the display reaches its safe shutdown point.

## Migration and validation

The package foundation now preserves the board bring-up behavior while separating
hardware support from demonstrations:

- [x] Extract the fixed platform, bus, power initialization, telemetry, input,
      indicator, audio, and display definitions into the core package.
- [x] Remove installation identity, credentials, and site policy.
- [x] Add and compile a minimal merged consumer fixture.
- [x] Layer demo, diagnostic, and battery-oriented behavior over the same core.
- [x] Migrate safe live ALDO4 control, logical audio control, terminal PMIC
      commands, and SD hardware support into core; put RTTTL and voice-note
      recording/playback in the optional demo layer.
- [x] Add a repeatable validation/compilation script in `scripts/`, including
      resolved header reporting and reference-header parity checking.
- [x] Render and validate the complete normal and diagnostic standalone
      profiles from the package source, with a stale-output check.

Moving stable implementation areas into named external components can happen
incrementally when it materially improves maintenance or diagnostics. It is not
a prerequisite for package delivery, and packaging alone is not presented as a
claim that the underlying inline lambdas have become tutorial material.

## Battery-oriented composition

A battery-oriented entry point is a policy composition over the same core
hardware package, not a separate hardware implementation. It may reduce polling,
keep the amplifier disabled while idle, and put both audio codecs into their
documented low-power states. It must keep ALDO3 energized because the supported
configuration needs the shared I2C bus after boot.

The current battery composition does those three things but leaves ALDO4 on by
default. The core now provides safe display-rail controls; automatic display
shutdown between application updates remains a separate workload policy. The
rail must never be removed during a refresh.

The battery entry point must remain distinct from demo behavior such as the
dashboard, test tones, and voice-note recording. Deep sleep and wake restoration
also remain outside its supported claims until their complete state transitions
have been verified.

A Nordic Power Profiler Kit II is available as of 2026-09-23, but no current
measurements have been taken yet. Until a controlled measurement campaign records
the firmware version, supply topology, state boundaries, and results, describe
this composition as **battery-oriented**, not as a measured low-power profile.
