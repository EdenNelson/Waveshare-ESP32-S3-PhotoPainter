# Testing and verification

The hardware *behavior* investigation is finished; see
[HARDWARE.md](HARDWARE.md) for the settled results. This document is how those
results were reached and how to reproduce them on your own unit: how to capture a
log that means something, how to read it, the procedures that have a known-good
result to compare against, and what has not been done yet.

Current consumption is measured with a Nordic Power Profiler Kit II (PPK2) on
one board, through USB-C and through the battery connector; the records are in
[`Measurements/`](Measurements/). See [Current consumption](#current-consumption)
below for the procedure and for what a power statement needs before it counts
as a result.

One rule underpins all of it: **do not change multiple PMIC variables in the same
test.** A retained PMIC state can hide a missing initialization step, so a
successful warm reset never proves a rail mapping.

> [!CAUTION]
> Do not disable ALDO3 while running this configuration. It is the audio rail,
> and de-energizing it clamps the shared I2C bus through the audio codecs'
> unpowered I2C pins, taking the PMIC and RTC down with it for the rest of the
> power cycle. No software path recovers from that state, because re-enabling
> ALDO3 requires the bus that is being clamped — and this configuration needs
> the bus after boot.
>
> A clamped board logs `i2c.master: I2C software timeout` for every device on
> the bus, and the state survives reflashing. Recovery is a full power
> draindown: disconnect USB-C **and** the battery, and leave it disconnected for
> **at least one minute**. Ten seconds is reliably not enough.

## Package build verification

With ESPHome installed (the package requires 2026.9.0; verified on 2026.9.1 and 2026.10.2). On 2026.9.x the
build prints one `shtcx_type_to_string … defined but not used` warning from
ESPHome's own SHTC3 driver; it is not package code and is gone in 2026.10. Run:

```sh
python3 scripts/generate_esphome_profiles.py --check
python3 scripts/generate_esphome_profiles.py --check --compile
scripts/verify_esphome_packages.sh
scripts/verify_esphome_packages.sh --config-only
```

The generator's `--check` verifies both committed standalone downloads against
their package compositions and validates the resolved standalone YAML. Adding
`--compile` builds both standalone downloads with synthetic credentials and
writes logs under ignored `build/reference-verification/`. The package verifier
runs the generator's stale-output check, validates all six consumer fixtures
(minimal, demo, diagnostic, battery, web-ui, and web-ui-diagnostic), prints their
merged `esphome.includes` lists, checks each fixture's headers against both
standalone profiles, and compiles all six.
`--config-only` skips compilation. The script works from any working directory;
`ESPHOME_BIN` selects a different executable. It stops on the first failure and
reports the profile and log path. Logs and resolved configurations are retained
under `build/package-verification/`, which is ignored by Git.

Fixtures contain no real credentials. They test package merging through a
consumer-owned `esphome:` stanza; packages are not validated in isolation.
Compilation verifies generated C++ and dependencies, not hardware behavior. The
standalone generator checks configuration equivalence to its package source;
package-built images were also exercised on hardware: boot readiness, SD access,
audio off/on, ALDO4 cycles, deep sleep with timer, BOOT, and KEY wake, and the
PPK2 runs in [`Measurements/`](Measurements/).

## Capturing logs: serial is the wrong tool for power tests

**USB serial and USB power are the same cable.** Unplugging USB-C to test the
USB-present transition removes the logger at precisely the instant being
measured. This is causal, not intermittent, and no amount of retrying works
around it.

Capture power-path tests over the network instead. The API carries the same log
stream, and the AXP2101 keeps the board running from whichever source remains,
so the connection survives the transition that kills serial:

```text
esphome logs <your-config>.yaml --device OTA | tee <run-name>.log
```

`--device OTA` resolves over mDNS and skips the serial prompt. Confirmed on
hardware: a capture ran uninterrupted across a USB-C removal, more than two
minutes on battery, and the reconnect.

**Serial is the right tool for exactly one thing — a boot capture** — because
Wi-Fi is not associated for the first few seconds and the API stream starts after
it. Use serial for boots and the API for everything that touches power. Do not
try to make one session do both.

Each test also needs the two sources arranged so the *other* one keeps the board
alive:

| Test | USB-C | Battery |
| --- | --- | --- |
| Cell removal and reinsertion | **connected** | the variable |
| USB removal and reconnection | the variable | **installed** |

Raw captures contain Wi-Fi credentials, API and OTA keys, hostnames, MAC
addresses, and LAN IP addresses. Remove them before a log leaves your machine;
[`Logs/README.md`](Logs/README.md) describes what was stripped from the logs
published here and how they are named.

## Reading the log

Every package line uses a stable `photopainter_*` tag followed by `key=value`
pairs. `event=` names what happened, `result=` states the outcome, and
transitions state `old=` and `new=`. Levels and edges are both covered: the
transition lines below fire on change, and two periodic level lines restate the
whole state whether or not anything changed.

| Tag | Line | States |
| --- | --- | --- |
| `app` | `Project edennelson.waveshare-esp32s3-photopainter version …` | Which build produced the capture. Quote it in every report. |
| `photopainter_power` | `event=boot result=… dcdc1=…->… aldo3=…->… aldo4=…->…` | PMIC bring-up, with each rail register before and after |
| `photopainter_power` | `event=power_reason power_on=0x.. power_off=0x.. pwron_key= vbus= …` | Why this boot happened and how the last run ended |
| `photopainter_power` | `event=register_transition status1=…->… ldo_enable=…->…` | A change in the cached PMIC status or rail-enable registers |
| `photopainter_power` | `event=rtc_osc_flag old=running\|stopped new=… seconds=… rtc_ctrl1=… rtc_ctrl2=… axp_irq0..2=…` | The PCF85063 oscillator-stop flag changed, with the RTC control registers and the AXP2101 interrupt-status latches at that moment. `stopped` means the clock stopped at some point and its time is untrusted until the next SNTP write |
| `photopainter_state` | `event=level power_ready= bus= … display= audio= amplifier= sd= sda= scl=` | Core level line, every 60 s in every build |
| `photopainter_snapshot` | `event=snapshot seq=… usb= usb_v= bat= bat_v= … nostate=` | Diagnostic build only: every entity's value, at boot and every 60 s |
| `photopainter_i2c` | `event=poll`, `event=bus_transition`, `event=recovery_attempt`, `event=recovery` | Shared-bus failures, bounded recovery attempts, and their outcome |
| `photopainter_audio` | `event=transition old=… new=active\|low_power result=…` | Logical codec shutdown and restore; `aldo3=on` is always stated |
| `photopainter_display` | `event=shutdown_wait`, `event=safe_shutdown`, `event=rail_transition rail=aldo4 old=… new=…` | The ALDO4 safe-shutdown sequence and rail change |
| `photopainter_input` | `event=pwr_button state=pressed\|held\|released hold_ms=…` | Every PWR press, a `held` line each second while held, and the release. A run of `held` lines with no `released`, followed by a boot whose PMIC probe fails, means a long PWR press powered the board off and clamped the bus |
| `photopainter_storage` | `event=mount old=… new=… result=…`, `event=capacity` | SD mount transitions and capacity read failures |
| `photopainter_telemetry` | `event=read result=failed metric=…` | A failed battery or USB reading, with the stage that failed |
| `photopainter_registers` | `event=snapshot phase=start\|complete`, `event=register device= reg= value=` | Diagnostic build only: read-only register snapshot |
| `photopainter_dashboard` | `event=first_refresh_wait missing=… exempt=… elapsed_ms=…` | Demo only: the readiness gate is holding the first refresh, naming every reading still missing; logged on change and at most every 5 s |
| `photopainter_dashboard` | `event=first_refresh result=requested readings=ready\|exempted exempt=… clock=valid\|pending wait_ms=…` | Demo only: the gate released; WARN when a component in an error state was exempted rather than waited on. The clock is never waited on: a working screen comes first, and the time appears on the next refresh once SNTP or the RTC supplies it |
| `photopainter_dashboard` | `event=render_begin stamp_ms=… page=dashboard\|sample_image rotate=0\|1`, `event=render_values … voice_note=… nostate=…` | Demo only: each refresh starts with the page it draws; dashboard refreshes also log the values drawn |
| `photopainter_dashboard` | `event=page_select page=… redraw=requested\|deferred_to_first_refresh\|skipped_display_off`, `event=rotate_pages old=… new=…` | Demo only: page and rotation changes, and whether the change redrew the panel |
| `photopainter_voice_demo` | `event=record …`, `event=playback …` | Demo only: voice-note recording and playback results |
| `photopainter_deep_sleep` | `event=request`, `event=stage`, `event=pre_sleep`, `event=enter`, `event=wake`, `event=restore` | Demo only: each step into and out of deep sleep |
| `photopainter_deep_sleep` | `event=boot_button result=ignored reason=hold_too_short\|hold_too_long\|wake_guard hold_ms=…` | Demo only: a BOOT hold that did not request sleep, and why. The sleep window is 1.5–5 s |

ESPHome's own DEBUG lines (`'<entity>': Sending state …`, `New state is …`) carry
the per-entity edges in the diagnostic build.

Conventions in the snapshot line:

- **`nan` versus `nostate=`.** A float of `nan` means no usable value. If the key
  is also listed in `nostate=`, the entity has never published; if it is not,
  the entity published "unavailable" (for example, `bat_v=nan` with no cell
  fitted). `nostate=-` means every entity has published.
- **`-1` for a binary value** means it has never published, distinct from a real
  `0`, and the key appears in `nostate=`.
- **`seq=` detects a dropped snapshot.** It increments once per line, so a gap is
  unambiguous where `uptime_s` is not.
- **`bus=`** states the shared I2C bus independently of any one device.

### Pre-release vocabulary

Some expected output in the procedures below was recorded with pre-release
builds (through 0.9.112), which used an `obs` tag and a different line format.
The captures under [`Logs/`](Logs/) are older still and use their own diagnostic
tags; [`Logs/README.md`](Logs/README.md) explains them. To read the `obs` lines:

| Line | States |
| --- | --- |
| `state …` | Full level report, every 60 s and once at boot — independent of the display |
| `render …` | What the panel actually drew, one line per refresh |
| `bin <name>=ON (initial)` | First publish of a binary sensor; a level, not a transition |
| `bin <name>: OFF -> ON` | A real transition |
| `sen <name>=…` | A sensor value, including values forced by a presence change |
| `num <name>=…` | A number entity, including its restored value at boot |
| `btn <name>: PRESSED` | A button press, logged before any guard runs |
| `audiopath amp=… dac_mute=… mic_pd12=…` | Every stage between a sample and the speaker cone, at the start of each audio action |
| `wait <name> result=ok\|timeout bound=…` | A bounded wait and its outcome |
| `render begin stamp=… window_closes_in=…` | The start of a refresh |
| `pmic pwron_src=… pwroff_src=…` | Why this boot happened and how the last run ended |

The same three conventions applied:

- **`nan` versus `nostate=`.** A float reading of `nan` means either "no usable
  value" or "never published", and only `nostate=` separates them.
  `bat_v=nan nostate=-` is a genuine unavailable — no cell fitted. `bat_v=nan`
  with `bat_v` listed in `nostate=` means the reading has not arrived yet.
- **`seq=` detects a dropped snapshot.** `uptime` cannot: the uptime sensor
  republishes on its own timer and can repeat across consecutive snapshots. A
  gap in `seq` is unambiguous.
- **`-1` for a binary sensor** means it has never published, distinct from a
  real `0`.

## Procedures with a known-good result

These have all been run to a pass on the development unit. They are recorded so a
change can be regression-tested against a stated expectation rather than against
an impression.

### Power path, over the API

Cell out (USB stays connected), wait 10 s, reinsert:

```text
bin battery_connected: ON -> OFF
sen battery_voltage=nan
sen battery_level=nan
state … bat_present=0 bat_v=nan level=nan … nostate=-
```

Presence and value move in the same second, and `nostate=-` beside `bat_v=nan`
is what distinguishes a genuine unavailable from a missing reading. On
reinsertion both return in the same second; the percentage will then re-estimate
over a few seconds, which is expected.

USB out (cell stays installed), wait 30 s, reconnect:

```text
bin usb_connected: ON -> OFF   /  sen usb_voltage=0.00
bin battery_charging: ON -> OFF /  sen battery_voltage=4.16
```

The second pairing is the useful one: charging stops, and the cell voltage is
re-read immediately rather than waiting out a poll. Off charge it reads ~4.16-4.18 V
and on charge ~4.21 V.

### Display refresh window

The panel's safe shutdown waits for the display component to report idle, with a
45 s timeout as the last-resort bound. Refreshes are 900 s apart, so the wait is
never exercised by accident. To reach it:

1. Toggle **PhotoPainter Display Enabled** ON — in a build that draws to the panel
   (the demo dashboard), this starts a refresh within a few seconds.
2. Wait for `render begin stamp=…`.
3. Toggle **PhotoPainter Display Enabled** OFF before `Display update took …` is logged.

```text
wait display_idle idle=no refresh_age=112ms timeout=45000ms expect=hold
Display update took 29094 ms
wait display_idle result=waited elapsed=29011ms idle=yes failed=no safe=yes
```

`expect=hold` is the marker that the timing landed. `expect=immediate` means the
attempt missed the refresh and proves nothing — retry rather than recording it.

The wait releases when the component reaches idle, so `elapsed` should track the
remaining refresh time rather than a fixed bound. This is the observable
difference from the previous 40 s render-stamp wait, which released on a clock
and held ~10.8 s past a 29094 ms refresh in the trace above.

`result=TIMEOUT` means the panel never reached idle inside 45 s. The safe-shutdown
hook is then skipped and `photopainter_display_power_down` refuses to clear ALDO4:

```text
wait display_idle result=TIMEOUT elapsed=45001ms idle=no failed=no safe=no
Display did not reach idle within 45000 ms; busy_gpio13=low. Safe-shutdown hook SKIPPED and the display rail must stay on.
Cannot disable ALDO4: the panel never reached idle. Refresh polling restored; no boot state was changed.
```

The switch springs back ON, which is the true runtime state. `failed=yes` is the
one case where a non-idle component still reports `safe=yes`: a component marked
FAILED is not driving the panel and never will, so the rail may be removed.

### Microphone level

A recording states its own level, so no listening is required:

```text
Voice note saved (160768 bytes); peak=32768 (100.0% FS) peak_raw=4079 (12.4% FS)
    gain=21 max_gain_before_clip=8 CLIPPED by our digital gain - lower Audio: Mic Gain
```

`peak_raw` is what the codec delivered, `peak` is after the digital multiplier,
and `max_gain_before_clip` is the largest multiplier that would not have clipped
at that input level. `peak=0` means digital silence — a dead or powered-down
microphone — which a byte count alone cannot show, and the `audiopath` line
immediately above it says which stage is responsible.

### Playback drain

Playback ends by asking the speaker to drain rather than by waiting on the ring
buffer and guessing at the DMA tail. Play a voice note and read the last two lines:

```text
wait spk_drain result=ok bound=10000ms
Playback complete
```

`result=ok` means `speaker.finish` reached STATE_STOPPED, which the driver sets
only after the audio source is empty, the ring buffer is empty, every real-audio
DMA buffer it submitted has been confirmed played, and the I2S driver has been
torn down. That last term is what the old `!has_buffered_data()` check plus a
200 ms delay was approximating, so a truncated tail here is a regression, not a
tuning problem.

`result=timeout` means the graceful stop never completed. The tail may be clipped
and a hard stop is forced so the shared I2S driver is released for the
microphone — without it the next recording would find the bus held:

```text
wait spk_drain result=timeout bound=10000ms; the tail of the note may be truncated.
    Forcing a hard stop so the I2S driver is released. spk_run=1
```

### PMIC power off — removed

Pre-release builds offered a PMIC soft power-off. The command itself completed
without I2C faults, but that only proved the shutdown. **Operator finding, 2026-11-14:** after a PMIC power-off the board powers back
up, but the shared I2C bus stays clamped. Power-off de-energizes ALDO3 along with
every other rail, and recovery needs a full power drain of at least one minute
with USB and battery disconnected. PMIC power-off and PMIC restart (which cycles
the same rails) are therefore not part of the supported configuration; the
package offers only an ESP32 restart, which leaves every rail untouched.

## Record for every run

- Board revision and any visible assembly revision
- ESPHome version and the firmware version from the boot log
- USB connected or disconnected
- Main battery connected or disconnected
- RTC backup cell state, when relevant
- Reset source: first power application, PWR button, USB-C reconnect, software
  restart, watchdog, or deep-sleep wake. The
  `photopainter_power event=power_reason` line at boot states this without
  guesswork (`pmic pwron_src=` in pre-release captures)
- ESP32 reset reason and deep-sleep wakeup cause, captured before other startup
  work obscures the event
- Time completely unpowered before startup
- AXP2101 registers before and after initialization
- GPIO levels for the AXP2101 interrupt, PWR button, display BUSY and RESET,
  and amplifier enable when relevant
- Downstream I2C probe results
- Display initialization and first-refresh result
- Audio, SD, buttons, and LED results
- Supply current for every power-characterization run
- The log filename

Boot power state needs no recording: every reset brings both rails up, so `0x90`
has one expected baseline with `bit 2` and `bit 3` set. Any other value at boot
is a finding rather than a saved preference to be looked up.

### Required PMIC snapshot

Capture at least these registers before changing them and after stabilization:

`0x00`, `0x01`, `0x03`, `0x10`, `0x20` through `0x2B`, `0x30`, `0x40` through
`0x42`, `0x48` through `0x4A`, `0x80` through `0x82`, `0x90`, `0x91`,
`0x94`, `0x95`, and `0xA4`.

Registers `0x20`/`0x21` report power-on/power-off events, `0x26` controls
sleep/wake behavior, `0x40`-`0x42` enable interrupts, and `0x48`-`0x4A`
contain interrupt status. Register `0x10` is the common-config register the
pre-release firmware used for soft power-off (bit 0) and PMIC restart (bit 1),
and holds internal off-discharge (bit 5). The supported configuration issues
neither command; the register is captured read-only in diagnostic snapshots. Capture event and interrupt status before clearing
or otherwise acknowledging it. Treat status registers according to the AXP2101
data sheet rather than feeding them through a generic read/write dump.

For battery and VBUS ADC diagnosis, also capture `0x34`, `0x35`, `0x38`, and
`0x39` after allowing enough time for a new conversion.

## Power-state matrix

| Case | USB | Main battery | Starting condition | Purpose |
| --- | --- | --- | --- | --- |
| U1 | Connected | Disconnected | Complete power loss | USB-only cold boot |
| U2 | Connected | Connected | Complete power loss | USB cold boot with battery/charger |
| B1 | Disconnected | Connected | PMIC fully off | Battery-only cold boot |
| R1 | Same as prior run | Same as prior run | ESP software restart | Warm reset with retained PMIC state |
| P1 | Disconnected | Connected | PWR short press (under 6 s) | Press logged with hold time; no action taken. Never hold PWR 6 s or longer: that is a hardware power-off and clamps the bus |
| S1 | Disconnected | Connected | Intentional sleep/wake | Low-power restoration |
| W1 | Connected | Connected | Watchdog reset | Fault recovery with retained rails |

Repeat a case if its baseline registers differ; that is a distinct state even
if the visible cabling is unchanged. Run each case twice where it is meaningful:
once normally, and once with the display switched off before the reset, so the
ALDO4-off path gets the same coverage.

## Rail isolation — closed

Both isolation questions were tested to conclusion. Neither needs further
exploratory testing; this section is the record of what was established.

**ALDO3 (audio) — characterized, do not retest.** Exhaustive testing established
the cost of disabling ALDO3: the two audio codecs' I2C pins lose their supply,
their ESD/input-protection diodes clamp the shared SDA/SCL lines to that
de-energized rail, and the bus fails for every device on it — the AXP2101 PMIC
and PCF85063 RTC included — for the rest of the power cycle. The board does not
recover in software; it requires the power draindown described above.

The rail can be dropped; what cannot be done is dropping it and continuing to
use the bus. Because this configuration reads the PMIC, RTC, SHTC3, and codec
status after boot and switches ALDO4 at runtime, keeping ALDO3 on is a
requirement here, and further ALDO3-disable tests are not scheduled. Use the
documented ES8311/ES7210 low-power register states plus the GPIO7 amplifier
disable for audio power-down instead. A configuration that never touches the
shared bus after boot is a different trade, out of scope here and untested.

**ALDO4 (display) — confirmed working.** ALDO4 is not on the shared I2C bus, and
hardware testing confirmed it can be disabled and re-enabled with no ill effects
once the panel has reached a safe shutdown point. What remains is
characterization and regression coverage, not proving feasibility:

1. Preserve every unrelated bit in AXP2101 registers `0x90` and `0x91`, and
   record actual readback rather than only the intended write.
2. ~~Measure supply current with ALDO4 on and off, at otherwise identical
   state.~~ Done: PPK2 runs 1–3, states A/C and B/D.
3. Repeat several cycles in a row and confirm each restore produces a clean full
   refresh.
4. Repeat under USB-only and battery-only operation; watch for USB or signal-pin
   back-powering that can disguise the actual rail behavior. Signal-pin
   back-powering was found in run 1 and fixed in rc.12 (run 2); runs 2 and 3
   cover USB-C and battery input.
5. Confirm the display returns correctly after a cold boot taken with the display
   switched off, where ALDO4 was de-energized before the reset.

## Shutdown and restoration coverage

The logical shutdown path — codecs into their documented low-power states with
ALDO3 left energized, and the panel brought to a safe point before ALDO4 is
gated — is implemented and working. What is worth capturing is state at each
boundary, so a regression can be located rather than just noticed:

1. Immediately on boot, before any PMIC writes or interrupt acknowledgement.
2. After ESPHome has initialized every component and the board is idle.
3. After logical peripheral shutdown, while both ALDO rails remain enabled.
4. After disabling ALDO4.
5. After restoring ALDO4 but before reinitializing the display.
6. After peripheral reinitialization and a complete functional test.

Also record SHTC3 wake/measurement/CRC success, SD card identity and mount
state, display BUSY timing and last completed refresh, and amplifier-enable
state. The display and amplifier do not expose a useful readable register map,
and SHTC3 is command-oriented, so behavioral state is more useful than a
nominal full-register dump for those devices.

The ordering that makes the sequence safe:

1. Stop voice recording, playback, microphone capture, speaker output, media
   playback, and any automation that could restart them.
2. Disable the NS4150B amplifier through GPIO before powering down either audio
   codec.
3. Put ES8311 and ES7210 into their documented mute/standby/power-down states,
   one device at a time, verifying register readback after each operation.
4. Allow an e-paper refresh to finish, verify BUSY is inactive, and put the panel
   into its documented power-off or sleep state before removing its rail.
5. Put SHTC3 to sleep. Keep the RTC running unless a separate RTC retention test
   explicitly requires otherwise.
6. If a rail test affects the SD interface, close files and cleanly unmount the
   filesystem before removing power.
7. Restore in dependency order: rail voltage and enable, settling delay, hardware
   reset where applicable, clocks/bus, component reinitialization, then amplifier
   enable or normal polling.

**Do not gate a rail until every ESPHome consumer of that rail can be suspended.**
An I2C or SPI transaction against an unpowered device can hang a bus, back-power
the device through an I/O pin, or trigger watchdog and component-state failures.

## Power measurement and open procedures

### Current consumption

Four runs are recorded, all on one board:

| Run | Date | Supply | Firmware | What it covers |
| --- | --- | --- | --- | --- |
| [1](Measurements/2026-11-14_ppk2-run1-usbc-5v0/README.md) | 2026-11-14 | USB-C 5.0 V | rc.11 | States A–G, and the clamped comparison X |
| [2](Measurements/2026-11-14_ppk2-run2-usbc-5v0-rc12/README.md) | 2026-11-14 | USB-C 5.0 V | rc.12 | A–G after the display back-powering fix |
| [3](Measurements/2026-11-16_ppk2-run3-battery-4v0/README.md) | 2026-11-16 | battery connector 4.0 V | rc.12 | A–G on battery input |
| [4](Measurements/2026-11-16_ppk2-run4-battery-4v0-clamp/README.md) | 2026-11-16 | battery connector 4.0 V | rc.12 | X on battery input |

A power statement not backed by a recorded run is data-sheet inference. A new
claim needs the procedure below: firmware version, supply topology, the time
window, and the PPK2 result that isolates the state being claimed.

#### Procedure

**Run header**, recorded before the first sample: firmware version (boot log
`Project … version`), ESPHome version, supply (PPK2 source mode at 5.0 V into
USB-C, or 4.0 V into the battery connector with USB-C unplugged), board state
(insulating back on or off, Li-ion fitted or not, RTC backup cell fitted or not,
SD card fitted or not), Wi-Fi network and RSSI, PPK2 sample rate.

**Instrument.** The PPK2 is driven from the host with `ppk2-api` (quit nRF
Connect first; only one program can hold it). Current is recorded as 10 ms
windows (mean, max, min) against host wall-clock time. State boundaries come
from the log lines below, which the API log stamps on the same host clock. Logs
travel over Wi-Fi; the supply leads carry no data.

**States**, each held 60 s (steady states) or captured as a whole event, three
repeats each. A steady state is measured from 5 s after its boundary line to the
next boundary, so switching transients are excluded:

| State | Actuation | Opening boundary |
| --- | --- | --- |
| A. Baseline idle, everything on | none, after the first refresh has finished | `photopainter_state event=level` with `display=active audio=active amplifier=on` (only the diagnostic layer has a snapshot line) |
| B. Audio logical low power | "PhotoPainter Audio Codecs Enabled" off | `photopainter_audio event=transition new=low_power result=ok` |
| C. Display rail off, audio on | audio on, then "PhotoPainter Display Enabled" off | `photopainter_display event=rail_transition old=on new=off result=ok` |
| D. Display rail and audio off | "PhotoPainter Audio Codecs Enabled" off with the display off | the audio `new=low_power` line |
| E. One display refresh | "PhotoPainter Display Enabled" on | `event=render_begin`; the end is taken from the trace (the panel plateau ends), because `Display update took` is DEBUG-only |
| F. ESP32 deep sleep, ALDO4 off | "Deep Sleep", 2 min timer | `photopainter_deep_sleep event=enter`; the sleep window ends at the current rise of the wake |
| G. One wake cycle | timer wake from F | the wake current rise to the end of the first refresh, taken from the trace as for E |
| X. Deep sleep, ALDO3 and ALDO4 off, bus clamped (comparison only) | private test build, "TEST X" button; ends the session | `deep_sleep: Sleeping for …`, which follows `photopainter_test event=clamp_test phase=enter_deep_sleep` |

State X is **not a supported configuration**. It reproduces the failure mode of
firmware that de-energizes ALDO3 in sleep, so that **X − F** states the
relative sleep-current cost of keeping the shared I2C bus working (ALDO3 up,
codecs in logical low power). Only ALDO3 and ALDO4 are cleared; ALDO2 is never
modified. The build that enters it is private and unpublished. X runs last: the
bus stays clamped after the timer wake, and the board needs a full power drain
of at least one minute.

E and G are reported as charge per event (mAh) and duration; A–D, F, and X as
mean and peak current. PMIC power-off is not measured: it is not part of the
supported configuration (see [PMIC power off — removed](#pmic-power-off--removed)).

**Run order:** A, B, C, D, E, F (which ends in G), then the second and third
repeats, then X once at the very end. A private test build can run A–E ×3 then
F/G from one button, logging `photopainter_test event=auto_test state=… rep=…`
at each boundary (see run 2); automated timing gave a spread under ±0.6 mA. State C needs audio switched back **on**
before the display rail goes off; it is easy to skip, so call each step out.
Record whether a web UI or API log client is connected. Run 2 found no
measurable difference in idle current from closing the web UI; the API client's
effect has not been isolated. USB-C first; the battery-input run repeats the same
table, since USB power can disguise the battery-side figure.

**Result record:** per state, the opening and closing log lines quoted
verbatim, window length, mean and peak current, and for E/G the charge. A
number without its boundary lines is not a result.

### ESP32 deep sleep

The demo implements a manually requested sleep sequence. It leaves ALDO3 and the
PCF85063 RTC running, puts the ES8311/ES7210 and GPIO7 amplifier into logical
shutdown, waits for the display's safe ALDO4-off sequence, verifies AXP2101
register `0x90` and RTC readback, then enters ESP32 deep sleep.

Wake sources are ext1, ANY_LOW, on BOOT (GPIO0) and KEY (GPIO4), plus a timer
fallback. This matches the vendor firmware's shipped Basic mode, which wakes on
the same two buttons through ext1. The vendor's current deep sleep leaves every
AXP2101 rail on; this demo additionally removes ALDO4. PWR (GPIO5) and the
AXP2101 interrupt (GPIO21) are not wake sources, in the vendor firmware or here.

The demo exposes **PhotoPainter Deep Sleep**, **PhotoPainter Deep Sleep Fallback
Minutes** (default 2), and **PhotoPainter Last Wake Cause**. A 1.5–5 s BOOT hold
requests sleep on release, and a wake press is guarded from immediately
re-entering sleep. Sleep is deferred up to 10 s while either button is held,
because ANY_LOW would wake at once. GPIO0 is a boot strap, but straps latch only
on power-on class resets, not on a deep-sleep wake (`reset_raw=8`).

Capture over the API. The one-shot `event=wake` and `event=restore` lines are
logged before a client can connect after wake, so the 60 s `event=level` line
restates them: `wake=`, `ext1=`, `reset_raw=`, `restore=`, and `slept_s=`, the
sleep length measured by the external RTC.

Expected sequence, per cycle:

| Step | Actuation | Evidence |
| --- | --- | --- |
| Entry | UI sleep button, or BOOT held 1.5–5 s | `event=request result=accepted`, `event=stage stage=audio result=ok`, `event=stage stage=display result=ok`, `event=pre_sleep result=ok aldo3=1 aldo4=0 entry_rtc_s=…`, `event=enter … gpio4_rtc_pullup=ok` |
| Timer wake | none | `photopainter_power event=boot` showing ALDO4 re-enabled (`ldo_enable` bit 3 0→1) with ALDO3 already on, then `event=level wake=timer wake_raw=4 reset_raw=8 restore=ok slept_s≈120` |
| BOOT wake | short BOOT press while asleep | `wake=boot_gpio0 wake_raw=3 ext1=0x01 reset_raw=8 restore=ok`, `slept_s` shorter than the timer |
| KEY wake | short KEY press while asleep | `wake=key_gpio4 wake_raw=3 ext1=0x10 reset_raw=8 restore=ok` |
| BOOT held through wake | hold BOOT ~2 s from asleep | still `reset_raw=8` (normal boot, not download mode), `button_armed=0`, then `event=boot_button state=rearmed gpio0=1` |
| GPIO0 after wake | BOOT hold 1.5–5 s after a button wake | `event=request result=accepted`: BOOT still works after an ext1 wake |
| PWR while asleep | PWR press | no button wake; the timer wakes it (`wake=timer`) |

Repeat at least five cycles alternating timer, BOOT, and KEY wake, on USB and on
battery, and once with a longer timer. `restore=degraded` or `slept_s=-1` after a
real sleep is a failure to diagnose, not to retry past. The PPK2 matrix above is
separate from this functional validation.

Recorded so far: on USB-C (2026-11-14), timer, BOOT, and KEY wake, BOOT sleep
requests after a button wake, and settings that survive a wake; the BOOT wakes
in PPK2 run 1 and the timer wakes in runs 2–4 repeat it. Button wake on battery
input has not been recorded.

### Battery ADC enable

The configuration reads battery voltage without setting ADC control bit 0, and it
reads correctly from a cold PMIC state. Whether the enable is genuinely
unnecessary — or merely left set by something earlier — needs testing across the
power-state matrix:

1. Confirm battery presence in status register `0x00`.
2. Capture ADC control register `0x30` before any measurement write.
3. Read `0x34`/`0x35` without changing bit 0 and record the result.
4. Enable only ADC control bit 0, wait for conversion, and read again.
5. Compare both readings with a multimeter at the battery connector.
6. Confirm that fuel-gauge percentage at `0xA4` is treated separately from raw
   battery voltage.

This produces the evidence needed to decide whether an upstream default should
enable battery-voltage measurement automatically.

### Native image dithering

ESPHome's native `image:` conversion and dithering has not been compared against
the manual ordered dithering this configuration uses for the panel. Waveshare's
sample image is the obvious subject:

- Source page: <https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/main/02_SDCARD/06_user_Foundation_img/480x480.jpg>
- Direct URL for ESPHome: <https://raw.githubusercontent.com/waveshareteam/ESP32-S3-PhotoPainter/main/02_SDCARD/06_user_Foundation_img/480x480.jpg>

Use the direct URL — the GitHub `/blob/` URL returns an HTML page. Worth
recording: the `image:` type, resize settings, dithering mode, resulting palette,
build-time download behavior, refresh time, and appearance on the physical
Spectra E6 panel.

### Native microphone plumbing

As of 2026-08-31 (ESPHome 2026.8.2) ESPHome provides no native runtime WAV-file
recording and no arbitrary SD-file playback, which is why the voice note is
implemented in C++. Whether the capture side can move to ESPHome's native
microphone `on_data`, `microphone.capture`, and `microphone.stop_capture` — and
whether native channel and gain configuration can replace the manual
stereo-to-mono mixing and digital gain — is untested. Recheck against the ESPHome
release in use before starting, and compare both implementations on the same
hardware across cold boot, warm restart, USB power, and battery power.
