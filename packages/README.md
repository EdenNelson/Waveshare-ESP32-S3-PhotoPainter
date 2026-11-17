# ESPHome package entry points

A consumer includes one board entry point from this directory (core, demo,
diagnostic, or battery) and, if it runs `web_server:`, the optional web UI files
that match the layers it uses. Files under `waveshare-esp32-s3-photopainter/` are
internal fragments, not public entry points.

| File | Intended use |
| --- | --- |
| `waveshare-esp32-s3-photopainter.yaml` | The core: reusable board support without installation policy or demo UI. |
| `waveshare-esp32-s3-photopainter-demo.yaml` | Board support plus a readiness-gated dashboard, RTTTL, SD voice-note recording/playback, and manually requested deep sleep. |
| `waveshare-esp32-s3-photopainter-diagnostic.yaml` | Board support plus DEBUG logging, runtime diagnostic state, and read-only register snapshots. |
| `waveshare-esp32-s3-photopainter-battery.yaml` | Board support plus slower polling and audio placed in logical low power after boot. Battery-oriented; this composition as a whole has not been measured. |
| `waveshare-esp32-s3-photopainter-web-ui.yaml` | Optional, only with `web_server:`. Web UI version 3, served from the firmware (`local: true`), with the board's entities grouped (Display, Power, Audio, Storage, Environment, Buttons & LEDs, Diagnostics). |
| `waveshare-esp32-s3-photopainter-web-ui-demo.yaml` | Optional companion to the demo layer: groups its page, sleep, and voice-note controls (adds Deep Sleep and Voice Notes). Requires `-web-ui.yaml`. |
| `waveshare-esp32-s3-photopainter-web-ui-diagnostic.yaml` | Optional companion to the diagnostic layer: places its memory sensors and register-snapshot button under Diagnostics. Requires `-web-ui.yaml`. |

## Consumer example

```yaml
packages:
  photopainter: github://edennelson/Waveshare-ESP32-S3-PhotoPainter/packages/waveshare-esp32-s3-photopainter.yaml@v1.0.0

esphome:
  name: photopainter
  friendly_name: PhotoPainter

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

api:
  encryption:
    key: !secret api_encryption_key
```

The `@v1.0.0` suffix pins a release tag; a commit SHA works as well.
Pinning a release or commit avoids an installation changing when the repository's
default branch changes.

The consumer's `esphome:` mapping merges with the package mapping. The same is
true for other mapping-valued stanzas, so local secrets do not need substitution
proxies. Remote package files intentionally contain no `!secret` references.

See [`examples/`](../examples/) for local validation fixtures and
[`ESPHome/README.md`](../ESPHome/README.md) for the merge and ownership contract.

## Scope boundaries

**Display without a layout.** The board package declares the panel with an
empty drawing lambda and `update_interval: never`, so a composition without a
layout (core, battery, diagnostic) never refreshes the panel, including after
"PhotoPainter Display Enabled" is switched off and on: the power-up script
resumes the panel with its own interval. Without that lambda, ESPHome's
`epaper_spi` would force a test card refreshed every minute. Add your own layout
with `!extend photopainter_display`, a `lambda:`, and your `update_interval:`.

The core package owns the fixed board definition, initialization, SD mounting
and capacity telemetry, logical audio power controls, safe ALDO4 controls, and an
ESP32-only restart (no PMIC power-off or restart; see HARDWARE.md). It does not choose device identity, credentials,
OTA/API policy, a display layout, physical-button application actions, or a
workload. The demo layer adds the dashboard, test tune, KEY-to-tune action, and
five-second recording/playback at `/sdcard/voice.wav`, and a deep-sleep button.
Recording replaces that demo file; the storage mount itself never formats a
card. Deep sleep is opt-in: it stops audio logically, safely removes ALDO4,
then sleeps until BOOT/GPIO0, KEY/GPIO4, or the configurable timer wakes the
ESP32. The
boot path restores ALDO4 and codec registers before the demo dashboard starts.
The external RTC remains running; its time and the shared I2C bus are checked
before entry. There is deliberately no RTC-stop switch: stopping the clock
would remove time continuity and is not needed for ESP32 deep sleep. Its power
cost can be evaluated separately with the PPK2 before adding an opt-in control.
Timer, BOOT, and KEY wake are verified on hardware, and the sleep current is
measured (see [`Measurements/`](../Measurements/)). GPIO0 is also a boot strap:
do not hold BOOT through a reset.

The supported configuration never disables ALDO3: doing so de-energizes the
audio codecs' I2C pins and clamps the shared bus for the rest of the power cycle.
Audio power-down uses codec register states plus the GPIO7 amplifier disable. ALDO2 is
never modified. The core's live ALDO4 control waits for the display's safe
shutdown point before removing the rail.

Measured current for the demo composition's power states, through USB-C and
the battery connector, is in [`Measurements/`](../Measurements/).

## Validation

All seven C++ headers in the standalone profiles are declared once in
the public core entry point: `esp_vfs_fat.h`, `sdmmc_cmd.h`,
`driver/i2c_master.h`, `esp_flash.h`, `esp_partition.h`, `esp_sleep.h`, and
`driver/rtc_io.h`. Every variant
inherits them. The storage fragment also supplies the required ESP-IDF
components (`fatfs`, `sdmmc`, `esp_driver_sdspi`). Optional demo selection does
not change the available board APIs.

Run from any working directory:

```sh
/path/to/repo/scripts/verify_esphome_packages.sh
# For a faster configuration/merge check:
/path/to/repo/scripts/verify_esphome_packages.sh --config-only
```

The script reports the merged C++ include lists, checks every fixture's headers
against both standalone profiles, and validates and compiles all six consumers in
[`examples/`](../examples/). It first checks that the two standalone profiles are
current with the package source. Regenerate them with `python3 scripts/generate_esphome_profiles.py` (PyYAML required)
when the check reports a stale file; use `--check --compile` to build both
standalone profiles as well.
Resolved configurations and compiler logs go to the ignored
`build/package-verification/` directory. A failure returns a nonzero status and
identifies the profile and log. `ESPHOME_BIN` selects another ESPHome executable,
and `PYTHON` selects a Python with PyYAML (ESPHome's own interpreter works).

For 1.0.0, all six consumers and both standalone profiles were validated and
compiled with ESPHome 2026.10.2, and validated with 2026.9.1, the minimum. These
checks prove configuration merging and generated-C++ compilation. They do
not replace flashing and physical regression testing when hardware behavior is
changed.
