# PPK2 run 3 — battery input at 4.0 V, 2026-11-16

The battery-input repeat of [run 2](../2026-11-14_ppk2-run2-usbc-5v0-rc12/README.md):
same board, same firmware image, same automated sequence. The only change is the
supply. The PPK2 stands in for the Li-ion cell at the battery connector and
USB-C is unplugged, so these are the figures that map to battery life. They do
not include the PMIC's USB input path.

## Run header

| Field | Value |
| --- | --- |
| Firmware | `edennelson.waveshare-esp32s3-photopainter` **1.0.0-rc.12**, normal composition plus the private test-only sequence button; the same image as run 2 (compiled 2026-11-14 14:49:58) |
| ESPHome | 2026.10.2 |
| Supply | Nordic PPK2, source-meter mode, **4000 mV into the battery connector** through a purpose-built lead; **USB-C unplugged**; output on 09:14:29 |
| Supply as seen by the PMIC | `status1=0x18` throughout (battery present, no VBUS); `USB-C Voltage 0.00 V`; `Battery Voltage` 3.99–4.03 V |
| Board | Rev 2.0; Li-ion removed (the PPK2 replaces it); RTC backup cell not fitted (the RTC oscillator-stop flag was set at power-up); SD card fitted (14,902 MB); insulating back as in run 2, not re-recorded |
| Network | Wi-Fi associated; ESPHome API log client connected; the web UI was used to start the sequence (run 2 showed monitoring clients have no measurable effect on these states) |
| Instrument | `ppk2-api`, ~100 kS/s, 10 ms windows on the host clock; 176.4 M samples |
| Sequence | `event=auto_test` button pressed 09:20:55: A → B → C → D → E, three repetitions with 60 s holds, then F (2 min timer) and G (the wake) |

## Results

Steady windows run from 5 s after their `event=auto_test state=… phase=begin`
line to the next one. Current is at the battery connector. Power is current ×
supply voltage, which compares the two supply topologies directly.

| State | Run 3, battery 4.0 V | Spread | Power | Run 2, USB-C 5.0 V | Power |
| --- | --- | --- | --- | --- | --- |
| A. Idle, everything on | **134.9 mA** | 134.7–135.1 | **540 mW** | 119.6 mA | 598 mW |
| B. Audio logical low power | **74.6 mA** | 74.1–75.5 | **298 mW** | 63.9 mA | 320 mW |
| C. ALDO4 off, audio on | **136.5 mA** | 134.6–138.1 | **546 mW** | 119.0 mA | 595 mW |
| D. ALDO4 off, audio off | **72.2 mA** | 71.2–74.0 | **289 mW** | 64.5 mA | 323 mW |
| E. One refresh, from `render_begin` | **1.32 mAh / 30 s** | 1.283–1.334 mAh | **5.3 mWh** | 1.29 mAh / 30 s (run 1) | 6.5 mWh |
| E. One refresh, from the rail-on line | 1.37 mAh / 33 s | 1.305–1.409 mAh | 5.5 mWh | 1.36 mAh / 33.3 s | 6.8 mWh |
| F. Deep sleep, ALDO3 on, ALDO4 off | **14.46 mA** | five 20 s blocks, 14.453–14.461 | **57.8 mW** | 16.07 mA | 80.4 mW |
| G. One wake cycle (boot, Wi-Fi, first refresh) | **2.04 mAh / 44 s** | 1 rep | **8.2 mWh** | 2.06 mAh / 43 s | 10.3 mWh |

E is measured to the end of the panel's activity plateau (five consecutive 1 s
means below 100 mA). G runs from the wake current rise (09:39:30.8) until five
consecutive 1 s means fall below 155 mA (state A + 20 mA). The F window is 99.5 s
of the 120 s timer; peak 21.6 mA.

## Evidence

```
09:37:31.759 photopainter_display event=panel_lines state=parked dc=0 cs=0 sclk=0 mosi=0 reset=0
09:37:31.763 photopainter_display event=rail_transition old=on new=off result=ok rail=aldo4 reg90=0xFF->0xF7 aldo3=on
09:37:31.782 photopainter_deep_sleep event=enter source=manual wake=ext1_any_low pins=gpio0,gpio4 timer=on gpio4_rtc_pullup=ok … aldo3=on aldo4=off
09:37:31.788 deep_sleep: Sleeping for 120000000us
09:39:39.663 photopainter_dashboard event=render_begin stamp_ms=8118 page=sample_image rotate=0
09:40:35.089 photopainter_deep_sleep event=level wake=timer wake_raw=4 ext1=0x00 reset_raw=8 restore=ok slept_s=121 … aldo3=1 aldo4=1 rtc_valid=1
```

The full set of boundary lines is in `boundaries.log`; `trace-1s.csv` is the
trace reduced to 1 s.

## Findings

1. **Deep sleep draws 14.46 mA from the battery** (57.8 mW at 4.0 V). Each hour
   asleep costs about 14.5 mAh; one wake cycle (2.04 mAh) equals about 8.5 minutes
   of sleep.
2. **The battery input costs less power than USB-C in every state.** It saves
   22 mW in deep sleep (28 %), 59 mW idle, and about 1.2 mWh per refresh. The
   difference is the PMIC's USB input path, which run 1 and run 2 include and
   this run does not.
3. **The awake ordering is the same on battery.** The audio path costs about
   60 mA (A → B). With the rc.12 fix, ALDO4 off changes awake current by no more
   than the repetition spread (C − A +1.6 mA, D − B −2.4 mA).
4. **The PMIC's battery percentage is a charge counter, not a voltage reading.**
   With the supply held at 4.0 V, `Battery Level` fell from 98 % to 90 % between
   09:17:32 and 09:42:32. The PPK2 measured 43.0 mAh over the same interval:
   about 5.4 mAh per percent, so the gauge's full scale is roughly 540 mAh
   (±12 % from 1 % resolution). This describes the PMIC gauge's model as
   configured, not the capacity of any real cell.

## Sequencing note

In repetitions 1 and 2 the test button's restore step, after E, switches the
display on again and starts a second refresh (09:26:27, 09:32:03). Run 2 shows
the same at the same point. The trace returns to idle before the next A window
opens, so the A windows are not affected, and E is computed from the first
refresh only.

## Not measured

- **The ALDO3-off clamped sleep (state X) on battery input.** The F − X cost of
  keeping I2C working (≈ 11.3 mA) was measured on USB-C only.
- More than one repetition of F and G on battery input.
- Battery voltages other than 4.0 V. A real cell falls toward 3.0 V as it
  discharges, and the current at a lower voltage was not measured.
