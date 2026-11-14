# Changelog

Releases of the PhotoPainter ESPHome package, newest first. Entries describe what
the board does differently, so a captured log can be read against the firmware
that produced it.

ESPHome prints the version in the first few lines of every boot log:

```text
[I][app]: Project edennelson.waveshare-esp32s3-photopainter version <x.y.z>
```

That line is what makes a capture evidence rather than an anecdote. Quote it when
reporting behaviour. Hardware-test builds ahead of a release carry an `-rc.N`
suffix; the release tag drops it.

## 1.0.0 — unreleased

First public release. The ESPHome package is the primary interface; the complete
normal and diagnostic profiles under [`ESPHome/`](ESPHome/) are rendered from the
same package source.

### Package structure

- A core entry point owns the fixed board definition: platform, buses, PMIC
  bring-up, telemetry, inputs, indicators, SD storage, audio, and display.
- Demo, diagnostic, and battery-oriented compositions layer over that same core
  rather than redefining the board.
- Device identity, Wi-Fi, API, OTA, credentials, and site policy stay in the
  consumer configuration. ESPHome's mapping merge combines them with the package;
  no substitution proxies or remote `!secret` lookups are involved.
- Externally customizable components carry stable IDs, so a consumer can
  `!extend` or `!remove` them without copying the package.

### Board behaviour

- **Both rails come up on every boot.** ALDO3 (audio) and ALDO4 (display) are
  energized during PMIC bring-up regardless of how the board was left, so the
  "Display: Enabled" and "Audio: Codecs Enabled" switches do not carry state
  across a reset.
- **ALDO3 is never disabled.** Dropping it clamps the shared I2C bus for the rest
  of the power cycle ([HARDWARE.md](HARDWARE.md)). ALDO2 is never modified.
- **Audio powers down logically, never by rail.** The ES8311 and ES7210 enter
  their documented low-power register states and the NS4150B amplifier is
  disabled on GPIO7. Restoring writes back every register the shutdown wrote.
- **The display rail can be cycled at runtime.** "Display: Enabled" stops the
  refresh poller, waits out any refresh in progress, confirms BUSY, issues the
  panel's safe shutdown, and only then clears ALDO4, and reverses that on the way
  back up.
- **No PMIC power-off or PMIC restart.** Both cycle ALDO3 with every other rail,
  which leaves the shared I2C bus clamped until a full power drain. The
  research-phase controls for them were removed; "PhotoPainter Restart" reboots
  the ESP32 only. Every boot still reports why the PMU last powered on and off.
- **Bounded shared-I2C recovery**, retried while the bus is down, with the PMIC
  and RTC verified independently.
- **All readings are ready before the first display refresh**, gated on the
  readings themselves rather than a delay; a component in an error state is
  exempted instead of blocking.
- **A machine-readable log.** Levels and edges are both stated, a periodic
  full-state line runs independently of any subsystem being powered on, and
  `nan`/`nostate=`/`-1` distinguish "no usable value" from "never published".
  [TESTING.md](TESTING.md) has the vocabulary.
- **Microphone gain defaults to 4**, measured against the ES7210 delivering
  roughly 12% of full scale in a normal room.

- **Display rail off no longer back-powers the panel.** CS, DC, and RESET are
  driven low before ALDO4 is cleared and restored after it returns; measured
  before/after in PPK2 runs 1 and 2 (8–49 mA removed while awake).
- **No refresh without a layout.** The panel is declared with an empty drawing
  lambda, so board-only and battery compositions never refresh it (ESPHome would
  otherwise force a test card every minute).
- **PWR button monitored, never acted on.** GPIO5 mirrors the AXP2101 `PWRON`
  pin; every press is logged with its hold time without touching I2C. Holding PWR
  for 6 s or more is the PMIC's own hardware power-off.

### Demo layer

- Readiness-gated six-colour status dashboard, RTTTL test tune, and five-second
  SD voice-note recording and playback. The first refresh never waits on network
  time; the clock appears on the next refresh.
- A sample-image page: Waveshare's own pre-dithered six-colour 800x480 bitmap,
  downloaded at compile time from a pinned vendor commit rather than
  redistributed. "PhotoPainter Display Page" selects it or the dashboard, and
  "PhotoPainter Rotate Pages" alternates them on each scheduled refresh.
- Manual ESP32 deep sleep: audio stops logically, ALDO4 is removed safely, the
  PMIC and running external RTC are verified, and the board sleeps until
  BOOT (GPIO0), KEY (GPIO4), or a configurable timer wakes it, using the same
  ext1 button wake as the vendor firmware. Boot restores ALDO4 and the codec
  registers before the dashboard readiness gate.

### Optional web UI grouping

- `-web-ui.yaml`, `-web-ui-demo.yaml`, and `-web-ui-diagnostic.yaml` group the
  web UI by function. They are separate opt-in layers because ESPHome rejects
  per-entity grouping on a device without `web_server:`. The speaker's media
  player cannot be grouped and stays in the default section.

### Security

- Requires ESPHome 2026.9.0, the first release with encrypted OTA; verified on
  2026.9.1 and 2026.10.2. The examples and standalone profiles encrypt OTA
  with the API key, require a web UI login, and no longer enable firmware upload
  through the web page. The diagnostic layer keeps Wi-Fi logging at INFO.

### Not claimed

The first PPK2 run (USB-C at 5.0 V) is recorded in
[`Measurements/`](Measurements/2026-11-14_ppk2-run1-usbc-5v0/README.md). The
battery-oriented composition and the deep-sleep demo are not battery-life claims
until the battery-input run backs them.

## Pre-release development

Development builds before 1.0.0 were numbered 0.9.100 through 0.10.x. They were
never released, so there is nothing to upgrade from. The sanitized captures under
[`Logs/`](Logs/) were taken with those builds and print those version strings;
[`Logs/README.md`](Logs/README.md) maps each capture to its purpose.
