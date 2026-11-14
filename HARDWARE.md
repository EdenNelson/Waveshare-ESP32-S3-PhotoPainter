# Hardware research notes

This document is the hardware reference for the Waveshare ESP32-S3
PhotoPainter Rev 2.0. It underpins this repository's ESPHome package but does not
depend on ESPHome, and it is intended as source material for any firmware written
for this board. The behavior investigation is complete: the rail map, the registers this
configuration touches, and the shared-I2C failure mode have all been identified
and verified on a physical Rev 2.0 unit. What follows is the settled result, with
the evidence behind it. See [TESTING.md](TESTING.md) before changing the PMIC
initialization sequence.

**Nothing here has been measured on a current meter yet.** Rail identity, register
behavior, and failure modes are established on hardware; what any of it *costs*
in current is not. A Nordic Power Profiler Kit II is now on hand (as of
2026-09-23), but no current measurement has been taken with it yet. Where this
document reasons about power saved, it is reasoning from data sheets and is
labeled as such.

The single most important fact is in
[the README](README.md#the-one-thing-that-makes-this-board-different):
ALDO3 must be enabled at boot and stay enabled, or the entire shared I2C bus is
clamped and unusable.

## Main devices

| Function | Device | Bus/address | Status |
| --- | --- | --- | --- |
| Controller | ESP32-S3 with 16 MB flash and octal PSRAM | — | Working |
| Power management | AXP2101 | I2C `0x34` | Working; rail mapping confirmed |
| Real-time clock | PCF85063ATL | I2C `0x51` | Working |
| Environment | SHTC3 | I2C `0x70` | Working |
| Audio DAC | ES8311 | I2C `0x18` | Working |
| Audio ADC | ES7210 | I2C `0x40` | Working |
| Speaker amplifier | NS4150B | GPIO enable | Working |
| Display | 7.3-inch Spectra E6, 800 × 480, six color | SPI | Working |
| Storage | microSD/TF | SPI in the ESPHome configuration | Working |

“Working” means demonstrated on the development unit with the complete working
configuration, published here as the diagnostic profile in
[`ESPHome/`](ESPHome/) and built with ESPHome 2026.8.2 (pre-release builds; the
1.0.0 package is verified on 2026.10.2). It does not imply that
every power state in the test matrix has been completed.

## GPIO map

| Function | GPIO |
| --- | --- |
| I2C SDA / SCL | 47 / 48 |
| E-paper DC / CS / CLK / MOSI / RESET / BUSY | 8 / 9 / 10 / 11 / 12 / 13 |
| I2S MCLK / BCLK / LRCLK / DOUT / DIN | 14 / 15 / 16 / 17 / 18 |
| NS4150B amplifier enable | 7 |
| SD CS / CLK / MISO / MOSI | 38 / 39 / 40 / 41 |
| BOOT / KEY buttons | 0 / 4 |
| PWR button (read-only mirror of AXP2101 `PWRON`, active high) | 5 |
| ACT / PWR LEDs | 42 / 45 |
| AXP2101 interrupt in vendor firmware (not claimed by ESPHome) | 21 |

The [board schematic](https://files.waveshare.com/wiki/ESP32-S3-PhotoPainter/ESP32-S3-PhotoPainter-Schematic.pdf)
shows BOOT shorting `ESP_BOOT` to ground, with that net connected to ESP32-S3
GPIO0 through `R34` (0 Ω) and pulled up to 3.3 V by `R36` (10 kΩ). GPIO0 is
RTC-capable, so the demo uses it, with KEY on GPIO4, as an active-low ext1
deep-sleep wake, as the vendor firmware does. GPIO0
is also a boot strap: holding BOOT during a reset may enter the ROM download
mode. The schematic and ESPHome support establish the intended electrical and
software path, but the actual BOOT wake behavior on this board still requires
the timed-fallback physical test in [TESTING.md](TESTING.md#esp32-deep-sleep).

The vendor SD implementation also identifies GPIO1 and GPIO2 as D1 and D2 for
four-bit SDMMC operation. The ESPHome diagnostic configuration currently uses
the compatible SPI subset: CS/D3 on GPIO38, CLK on GPIO39, MISO/D0 on GPIO40,
and MOSI/CMD on GPIO41.

## Boot dependency

The AXP2101 must be available on I2C before dependent components initialize.
The current ESPHome configuration runs PMIC setup in an `on_boot` automation at
priority **790**, chosen deliberately: ESPHome restores `restore_value` globals
at priority 800, so 790 is the first point at which restored globals are
readable, and it still precedes the audio components (priority 600) and the
display component (priority 400). It:

1. Retries the AXP2101 chip-ID read at register `0x03`, up to ten times at
   20 ms intervals, and records whether the shared bus came up at all.
2. Captures DCDC1 voltage (`0x82`), ALDO3 voltage (`0x94`), ALDO4 voltage
   (`0x95`), and the first LDO enable register (`0x90`).
3. Programs DCDC1 to 3.3 V (`0x82` = `0x12`), ALDO3 to 3.3 V
   (`0x94[4:0]` = `0x1C`) and ALDO4 to 3.3 V (`0x95[4:0]` = `0x1C`) when the
   expected state is absent.
4. Sets `0x90` bit 2 (ALDO3) and bit 3 (ALDO4), preserving every other bit, then
   verifies readback. Both rails come up on every boot.
5. Waits for downstream rails to stabilize before components start.

This sequence resolves the observed situation where the ESP32-S3 boots but the
display or downstream peripherals are not ready after a cold power state.

The vendor firmware follows the same broad order: initialize I2C and the
AXP2101, establish its startup and wake settings, configure the 3.3 V rails, and
only then initialize the e-paper and other peripherals. Its sleep path disables
both ALDO3 and ALDO4 — the condition described below under ALDO3, and the reason
retained PMIC state matters when comparing a warm reset with a true cold start.

## Boot power state

**Every boot brings both rails up.** ALDO3 (audio) and ALDO4 (display) are
energized during PMIC bring-up regardless of how the board was left, so `0x90`
has one expected baseline — `bit 2` and `bit 3` both set — and any other value
is worth investigating rather than explaining away.

The "Display: Enabled" and "Audio: Codecs Enabled" switches work normally while
the board is running; they simply do not carry their state across a reset. A
board demonstrating hardware should not come back from a reset with the panel
dark or the codecs down. What persisting an off state would have saved is
unknown — it has not been measured — so the demonstration default wins by
default rather than by argument.

One consequence worth knowing when comparing captures: a reset always returns
the board to the same power state, so two logs taken minutes apart are directly
comparable without recording which switches were touched in between.

Persisting either switch across a reset is not simply a `restore_mode` away.
`TemplateSwitch` restores at setup priority 798, which is *before* the
priority-790 PMIC bring-up and well before the audio and display components a
restored state would have to act on.

## AXP2101 register notes

| Register | Use in this project |
| --- | --- |
| `0x00` | VBUS and battery-presence status (bit 5 VBUS, bit 3 battery) |
| `0x01` | Charger state (bits 6:5 == `01` while charging) |
| `0x03` | PMIC identification/probe |
| `0x10` | Common config — full bit map below |
| `0x12` | BATFET control; bit 3 = keep BATFET enabled when powered off on battery alone |
| `0x20` | PWRON status: why the PMU last powered **on** |
| `0x21` | PWROFF status: why it last powered **off** (bit 1 = software command) |
| `0x22` | PWROFF_EN: bit 1 enables the PWRON long-press as a power-off source, bit 0 selects power-off vs restart for it |
| `0x25` | PWROK setting and power-off sequence; bit 2 selects reverse-of-startup ramp-down |
| `0x26` | Sleep and wake configuration; written only by an unused routine in an older vendor snapshot |
| `0x27` | IRQLEVEL `[5:4]`, OFFLEVEL `[3:2]`, ONLEVEL `[1:0]` press-duration thresholds |
| `0x30` | ADC channel enables (bit 0 battery voltage, bit 2 VBUS voltage) |
| `0x34` / `0x35` | Battery-voltage ADC result, 14-bit (`0x34[5:0]` high, `0x35` low) |
| `0x38` / `0x39` | VBUS-voltage ADC result, 14-bit, same layout |
| `0x80` | DCDC output enable/DVM control; capture during tests |
| `0x82` | DCDC1 voltage control (`0x12` = 3.3 V) |
| `0x90` | ALDO output enables (bit 2 ALDO3, bit 3 ALDO4) |
| `0x94` | ALDO3 voltage control (`[4:0]` = `0x1C` for 3.3 V) |
| `0x95` | ALDO4 voltage control (same encoding) |
| `0xA4` | Fuel-gauge battery percentage |

### `0x10` in full, from the data sheet

Register `0x10` is the only one the firmware writes that can remove board power,
so it is worth reading in full rather than by the two bits this project drives.
From `Documentation/AXP2101.pdf` §6.13.2.7:

| Bit | Meaning | POR default | Observed on this board |
| --- | --- | --- | --- |
| 7:6 | undocumented, read/write | 0 | 0 |
| 5 | internal off-discharge for DCDC, LDO and SWITCH | 1 | set |
| 4 | undocumented, read/write | **1** | **set** |
| 3 | PWROK pulled low restarts the system | 0 | clear |
| 2 | PWRON held 16 s shuts the PMIC | 0 | **set** |
| 1 | restart the SoC — auto-clearing | 0 | — |
| 0 | soft power-off — auto-clearing | 0 | — |

Two practical consequences. **Bit 4 defaults set and is undocumented**, so any
write to `0x10` must be read-modify-write; a blind byte clears it. And **bit 2 is
set on this board**, which means holding PWR for 16 seconds shuts the PMIC
regardless of software — the hardware escape hatch if firmware ever stops
responding.

Bits 0 and 1 are auto-clearing (`RWAC`). Reading `0x00` back after writing one
proves nothing, because the PMU clears the bit whether or not it acted. `0x21`
bit 1 on the *next* boot is the evidence that a software power-off happened.

### Powering off, and what it does not require

A soft power-off is a single write of `0x10` bit 0. **The host does not need to
bring any rail down first** — the PMU sequences and discharges every rail itself.
That matters here specifically because a host-side teardown would have to drop
ALDO3, which clamps the shared bus and would make the terminal command
unsendable. The bus is lost as a *consequence* of the power-off, at the point it
is no longer needed; the command itself completed without I2C faults.

**Operator finding, 2026-11-14:** after a PMIC power-off the board powers back
up, but the shared I2C bus stays clamped. Power-off de-energizes ALDO3 along with
every other rail, and recovery needs a full power drain of at least one minute
with USB and battery disconnected. PMIC power-off and PMIC restart (which cycles
the same rails) are therefore not part of the supported configuration; the
package offers only an ESP32 restart, which leaves every rail untouched.

`0x25` bit 2 defaults **clear**, meaning the PMU drops every rail simultaneously.
Setting it before the terminal command gives a ramp-down in the reverse of the
startup order, which is the orderly behavior and costs one register write.

`0x12` bit 3 was found **set**: powered off on battery alone, BATFET stays
enabled and the cell continues to feed VSYS. "Off" is therefore not electrically
absolute on this board. Clearing that bit would make USB the only way back on a
battery-only unit, so it is documented rather than changed.

### Powering back on

The board powers back up by either route below, but after a PMIC power-off the
shared bus comes back clamped and needs a full drain (see above). Confirmed on
hardware, both routes:

- a press of the **PWR** button — the AXP2101 `PWRON` pin; the required hold is
  `0x27[1:0]`, observed as **128 ms** on this board;
- **reconnecting USB-C**, which powers the board up even with a battery already
  installed.

`0x20` records which of these happened, so the next boot log states it.

### ADC enables

Bit 2 of `0x30` (VBUS measurement) is enabled explicitly before reading VBUS.
Bit 0 (battery-voltage measurement) is **not** written by this configuration and
battery voltage reads correctly from a cold PMIC state across many boots, so an
explicit enable appears unnecessary in practice. That is an observation about
this board rather than a data-sheet guarantee.

## PWR button and the long-press hazard (schematic, 2026-11-14)

The PWR button (K2) pulls the AXP2101 `PWRON` pin to ground through R26
(510 ohm). Transistor T1 (BSS138, gate via R25 1 kohm from `PWRON`) mirrors it
onto GPIO5: with PWR up, `PWRON` is high, T1 conducts, and GPIO5 reads low;
pressed, T1 turns off and R24 (10 kohm) pulls GPIO5 high. The vendor firmware
reads GPIO5 the same way (active high). GPIO5 is a plain input, not on the I2C
bus, so it stays readable while the bus is clamped.

The PMIC acts on `PWRON` directly. A long hold is a hardware power-off. Read
from this board on 2026-11-14 (diagnostic snapshot) and decoded against the
AXP2101 datasheet (sections 6.13.2.19 and 6.13.2.24):

| Register | Value | Meaning |
| --- | --- | --- |
| `0x22` | `0x06` | bit 1 = 1: PWRON held past OFFLEVEL is a power-off source; bit 0 = 0: power-off, not restart; bit 2 = 1: die over-temperature (145 C) also powers off |
| `0x27` | `0x14` | OFFLEVEL `[3:2]` = `01`: **6 s**; IRQLEVEL `[5:4]` = `01`: 1.5 s; ONLEVEL `[1:0]` = `00`: 128 ms |

So holding PWR for 6 s or longer powers the board off, and like a software PMIC
power-off it de-energizes ALDO3 and leaves the shared bus clamped until a full
power drain. Firmware cannot intercept it. The supported configuration leaves
the PMIC setting unchanged and instead **documents it (do not hold PWR) and
monitors it**: every press is logged with its hold time, once per second while
held, so a power cut mid-press still leaves its duration in the log. The values
of `0x22` and `0x27` on this board are captured read-only by the diagnostic
register snapshot.

## RTC supply and backup cell (schematic, 2026-11-14)

The PCF85063 is not powered from the 3.3 V system rail. Per the
[board schematic](https://files.waveshare.com/wiki/ESP32-S3-PhotoPainter/ESP32-S3-PhotoPainter-Schematic.pdf):

- PCF85063 `VDD` (pin 10) is net `VRTC`, the AXP2101's always-on `RTCLDO`
  output (pin 28, 2.2 uF on C46; 1 uF local on C5).
- The coin-cell connector J3 feeds the AXP2101 `VBACKUP` input (pin 27) through
  R61 (0 ohm), not the RTC directly. The PMIC derives `VRTC` from whichever
  source it has: USB, the Li-ion cell, or `VBACKUP`.
- The RTC interrupt pin is not connected, so the PCF85063 cannot be a wake
  source. The vendor firmware does not use it either.
- The oscillator is a 32.768 kHz crystal (Y1) with 22 pF load capacitors.

The backup cell cannot be measured from firmware. The observable consequence is
the PCF85063 oscillator-stop flag (seconds register bit 7): it is set whenever
the oscillator stops and stays set until the time is next written, which this
configuration does on every SNTP sync. On 2026-11-14 the flag set once under
continuous USB power, with the backup cell unplugged and the board's insulating
back removed. The leading explanation is handling near the exposed crystal; it
has not been reproduced under controlled conditions, so it is recorded here as
an observation, not a characterization.

## Unconnected AXP2101 outputs (operator, 2026-10-06)

On the PhotoPainter these AXP2101 pins are not connected (NC): BLDOIN, BLDO1, BLDO2, DLDO2/DC4SW,
CPUSLDO, DLDO1/DC1SW, and the DCDC2–DCDC4 converter pins (FB2/LX2/VIN2, FB3/LX3/VIN3,
FB4/LX4/VIN4). Disabling the BLDO1/BLDO2/CPUSLDO/DLDO1 enables (`0x90` bits 4–7), DLDO2 (`0x91`
bit 0), or DCDC2–4 (`0x80` bits 1–3) therefore powers nothing down on this board. The rails that matter remain DCDC1,
ALDO3 (audio, and the shared I2C bus) and ALDO4 (display); ALDO1/ALDO2 are not described here.

## ALDO3 and ALDO4: rail identity and isolation, both settled

Both the current ESPHome diagnostic work and vendor implementations configure
ALDO3 and ALDO4 to 3.3 V. The board schematic explicitly connects `Audio_VCC`
to ALDO3; ALDO4 is the display rail. Voltage programming and output enable are
separate AXP2101 operations, so both must be recorded when interpreting a test.

### ALDO3 (audio) takes the shared bus with it — do not retest

Repeated isolation testing established what disabling ALDO3 costs: the shared
I2C bus (AXP2101 PMIC, PCF85063 RTC, SHTC3, ES8311, ES7210) becomes unusable for
the rest of the power cycle. De-energizing ALDO3 removes the supply from the two
audio codecs' I2C pins; their ESD/input-protection diodes then clamp the shared
SDA/SCL lines to that de-energized rail, and the bus fails for every device on
it, including the PMIC and RTC.

The rail can be dropped. What cannot be done is dropping it and continuing to
use the bus, or bringing the bus back without removing power from the board.

The failure is not softly recoverable. Once the bus is clamped this way, no
software action restores it — including the configuration's own I2C recovery
script, because reaching the PMIC to re-enable ALDO3 requires the very bus that
is being clamped. A "display-only" power state — audio rail off, display and
shared bus still live — is therefore not available: the shared bus goes down
with the audio rail, so it is not pursued here.

**Observable symptom.** A board in this state logs `i2c.master: I2C software
timeout` continuously, for every device on the bus rather than only the audio
codecs. This is the expected signature of the clamp, not of a bad configuration.
Any firmware that powers the board down with ALDO3 disabled leaves it this way;
as of 2026-08-31 OpenDisplay does. Waveshare's shipped firmware does not: its
deep sleep leaves every AXP2101 rail on. An older vendor snapshot contains a
routine that clears ALDO3 among other rails, but every call to it is commented
out and it is absent from the pinned repository and the factory image. The
clamp survives reflashing, because flashing does not de-energize the rail.

**Onset is not instant (measured 2026-11-14).** Clearing ALDO3 alone
(`0x90` `0xF7 -> 0xF3`) left the bus working 3 ms later: the read-back succeeded
with SDA and SCL high. By the next poll, 4.07 s later, both lines were held low
(`sda=0 scl=0`) and the PMIC and RTC were unreachable, and after an ESP32 deep
sleep and wake every poll and bounded recovery failed. A write that succeeds
does not show the bus survived it.

**Recovery requires a full power draindown.** Disconnect USB-C *and* the
battery, and leave the board disconnected for at least one minute so the bulk
capacitance drains. A ten-second power-down is reliably not enough; the timeouts
continue until the board has been unpowered long enough. On the next power-up
this configuration enables ALDO3 during PMIC bring-up and the bus comes back
clean.

Audio power-down instead uses the documented ES8311/ES7210 low-power register
states plus the GPIO7 amplifier disable, with ALDO3 always enabled. That path is
implemented as `pmic_audio_power_action_script` with action 0 and is reversible
in software via `audio_logical_power_up_script`.

**Scope of that decision.** Keeping ALDO3 on is a requirement of *this*
configuration, which reads the PMIC, RTC, SHTC3, and codec status after boot and
switches ALDO4 at runtime — all of which need the bus. A configuration that
genuinely never touches the shared bus after boot could treat the loss of the
bus as an acceptable trade and go further: place the components in their
documented low-power states and drop rails, including VRTCLDO. That has not been
tested here and is not supported. The rail map, register table, and evidence in
this document are enough to start from; anything past that point is unverified
territory.

### ALDO4 (display) can be cycled independently — confirmed working

ALDO4 is not on the shared I2C bus, so removing it does not disturb the PMIC,
RTC, or codecs. Hardware testing confirmed that the display rail can be disabled
and re-enabled with no ill effects, provided the panel is brought to a safe
shutdown point first. This is implemented and exposed as the “Display: Enabled”
switch:

- `display_power_down_script` stops the display poller, waits out the refresh
  window, confirms BUSY/GPIO13, issues the driver's safe-shutdown hook, and only
  then clears `0x90` bit 3.
- `display_power_up_script` reprograms `0x95` to 3.3 V, sets `0x90` bit 3,
  allows the rail to settle, and restarts the poller so a reset-driven full
  refresh runs.

The full demo now combines this safe ALDO4 shutdown with ESP32 deep sleep in
firmware. Physical sleep/wake regression and current characterization remain;
the independent rail cycle itself is already established.

The demo leaves the PCF85063 RTC running across ESP32 deep sleep to preserve
time continuity and provide an independently readable I2C check before entry.
An RTC-stop UI switch is intentionally absent until there is a measured reason
for it and a tested resume sequence. This choice does not affect ALDO3: the
audio rail remains enabled for shared-I2C safety.

## Audio codecs: what setup() does not restore

Both codecs sit on the shared bus and stay powered by ALDO3 at all times. The
logical audio shutdown drives them into low-power register states instead, and
bringing them back is **not** symmetric with `setup()`:

| Chip | Register | Shutdown writes | Restored by the component's `setup()`? |
| --- | --- | --- | --- |
| ES8311 | `0x31` DAC mute | `0x60` (DSM + DEM mute) | **No** |
| ES8311 | `0x00`, `0x01` | `0x00` | yes |
| ES7210 | `0x4B` / `0x4C` mic power-down | `0xFF` (all down) | **No** |
| ES7210 | `0x06` | bits `0x07` set | **No** |
| ES7210 | `0x00`, `0x01`, `0x40` | — | yes, incidentally |

The general rule this establishes: **a power-down sequence that writes a register
must have a power-up sequence that writes it back.** Relying on a component's own
`setup()` to undo a register it never writes leaves the chip fully clocked,
answering on I2C with the right chip ID, and silent. A chip-ID probe returning OK
says the device is reachable, not that audio can come out of it.

`0x4B` / `0x4C` decode as `bit 7` VREF_PDN, `bit 6` MICBIAS_PDN, `bits 5:4`
PGA_PDN, `bits 3:2` MOD_PDN, where a set bit means powered **down**. `0xFF` is
everything down; `0x0F` leaves the modulators down and is the post-`setup()`
resting value; `0x00` is everything up. The value moves from `0x0F` to `0x00` on
the first audio activity of a boot — including playback, which touches no ADC —
most likely the ES7210's own `setup()` running. Either non-`0xFF` value records
successfully.

## Microphone signal path

- **Stream format:** mono, 32-bit slot, 16 kHz. The meaningful sample is the
  **high half-word**; the low half is ADC least-significant bits and is noise at
  this scale.
- **Analog gain:** the ES7210 PGA is at **+30 dB** (`0x43`-`0x46` = `0x1A`), and
  its ADC digital scale adds more.
- **Practical ceiling:** a normal room produces a raw peak around **12% of full
  scale**. Any digital multiplier above roughly **8** clips on top of that, so
  headroom is in the analog path, not the digital one. A capture that clips every
  sample regardless of input is a saturated channel, not a loud one.

## Speaker signal path

- Mono, 16-bit, 16 kHz, through the ES8311 to an NS4150B enabled by GPIO7.
- The I2S ring buffer is **16000 bytes**, about 500 ms of audio.
- The microphone and speaker share one `i2s_audio` bus and therefore one driver
  mutex: only one direction can be active at a time, and anything that starts
  the other direction mid-operation contends for it.

## Measured timings

Repeatable figures from the development unit, useful as pass/fail bounds:

| Operation | Time |
| --- | --- |
| Full e-paper refresh | **~29.1 s** (29054-29099 ms across seven runs) |
| First refresh after reset | ~35 s, gated on every panel reading being present |
| Five-second voice note, playback | ~5 s |
| RTTTL "Final Countdown" | ~12 s |
| Display safe shutdown, panel already idle | ~1 s |
| Display safe shutdown during a refresh | up to 40 s, waiting the refresh out |

## Battery telemetry behavior

- Loaded cell reads **~4.18 V** off charge and **~4.21 V** on charge; VBUS reads
  **5.05-5.08 V**.
- **The fuel gauge re-estimates after a cell change.** Removing and reinserting a
  battery has produced 100% → 67%, 100% → 83% and 100% → 26% within seconds,
  settling afterwards. This is normal coulomb-counter behavior after the cell is
  swapped, not a fault, and it is why battery percentage is deliberately not
  re-read on every charging transition — doing so would publish the settling
  noise as real readings.
- Battery voltage *is* re-read on charge transitions, because it genuinely moves
  (the ~4.18/~4.21 pair above).
- With no cell installed, both battery entities report unavailable rather than
  holding their last reading.

## Settled

- Rail identity: DCDC1 and ALDO3 are required for the shared bus and audio;
  ALDO4 is the display rail
- Dropping ALDO3 costs the shared I2C bus for the rest of the power cycle, so
  any configuration that needs the bus after boot must keep ALDO3 on — closed
- ALDO4 can be cycled independently, with a safe shutdown and restore sequence
- The registers listed above, and their encodings, as used by this configuration
- Cold-boot ordering: PMIC bring-up must precede audio and display setup
- PMIC soft power-off needs no host-side rail teardown, but it de-energizes ALDO3
  and the bus stays clamped after power-up until a full drain, so the supported
  configuration does not use it (operator, 2026-11-14)
- Powering back on: a PWR press or a USB-C reconnect, either with a cell fitted
- Codec restore is not symmetric with `setup()`; the registers a shutdown writes
  must be written back explicitly
- Microphone headroom sits in the analog path; digital gain above ~8 clips

## Remaining characterization

None of these are open questions about how the hardware works; they are
measurements and additions that have not been made yet.

- Current-consumption measurements for each power state, including ALDO4 off.
  **No longer blocked on equipment.** A Nordic Power Profiler Kit II was
  acquired (on hand as of 2026-09-23); no current measurement has been taken
  with it yet. Nothing else in this document is blocked on it, and no power-saving choice
  here should be argued from estimates until the numbers exist.
- Repeat-cycle regression coverage for ALDO4 under battery-only operation
- Shared-I2C recovery behavior against faults other than the closed ALDO3 case
- GPIO21 PMIC-interrupt support in ESPHome
- Physical repeat-cycle regression of the new demo deep-sleep path, especially
  BOOT/KEY ext1 wake versus timer fallback and post-wake codec restoration
- **Measured 2026-11-14 (PPK2 run 1):** switching ALDO4 off while the ESP32 is
  awake *raised* input current (about +8 mA with audio on, +50 mA with audio off),
  consistent with the hypothesis below; deep sleep with ALDO4 off is 16.07 mA.
  See [the run record](Measurements/2026-11-14_ppk2-run1-usbc-5v0/README.md).
- Whether the e-paper signal lines back-power the panel while ALDO4 is off. The
  ESP32 keeps driving the panel's SPI and control pins, and ESPHome's shutdown
  hook sends the panel's deep-sleep command during a reboot or deep-sleep entry
  even when ALDO4 is already off. The panel is not on the shared bus, so this
  cannot clamp I2C; whether it draws measurable current is a PPK2 question.

## Evidence hierarchy

Use evidence in this order:

1. Repeatable measurements and serial logs from the physical Rev 2.0 board
2. The board schematic and component data sheets listed in
   [`Documentation/README.md`](Documentation/README.md)
3. Immutable vendor-source links in [`References/README.md`](References/README.md)
4. Current upstream source, noting its commit and date
5. Inference, explicitly labeled as such
