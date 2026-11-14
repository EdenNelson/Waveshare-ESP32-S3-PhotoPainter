# PPK2 run 2 — USB-C at 5.0 V, display-rail fix (rc.12), 2026-11-14

A before/after measurement of one change: rc.12 drives the panel's control lines
low before switching ALDO4 off ([run 1](../2026-11-14_ppk2-run1-usbc-5v0/README.md)
showed that switching ALDO4 off while awake *raised* current). Same board, same
supply, same states as run 1; the sequence was automated so every repetition has
identical timing.

## Run header

| Field | Value |
| --- | --- |
| Firmware | `edennelson.waveshare-esp32s3-photopainter` **1.0.0-rc.12**, normal composition, plus a private test-only button that runs the sequence (not published) |
| ESPHome | 2026.10.2 |
| Change under test | `controls/display_power.yaml`: CS (GPIO9), DC (GPIO8), and RESET (GPIO12) driven low before ALDO4 is cleared; CS and RESET restored high after it returns |
| Supply | Nordic PPK2, source-meter mode, **5000 mV into USB-C** (power-only pigtail); output on 14:58:06 |
| Board | Rev 2.0; Li-ion removed; RTC backup cell removed; insulating back off; SD card fitted |
| Network | Wi-Fi associated; ESPHome API log client connected; **web UI tab closed during the sequence** (run 1 had it open) |
| Instrument | `ppk2-api`, ~100 kS/s, 10 ms windows on the host clock; 144.4 M samples |
| Sequence | `event=auto_test` button: A → B → C → D → E, three repetitions with 60 s holds, then F (2 min timer) and G (the wake) |

## Results

Steady windows run from 5 s after their `event=auto_test state=… phase=begin`
line to the next one. Mean current is at the 5.0 V input.

| State | Run 1 (rc.11) | **Run 2 (rc.12)** | Run 2 spread | Change |
| --- | --- | --- | --- | --- |
| A. Idle, everything on | 119.7 mA | **119.6 mA** | 119.2–120.0 | none (control) |
| B. Audio logical low power | 63.3 mA | **63.9 mA** | 63.5–64.4 | none (control) |
| C. ALDO4 off, audio on | 127.9 mA | **119.0 mA** | 118.8–119.4 | **−8.9 mA** |
| D. ALDO4 off, audio off | 113.8 mA | **64.5 mA** | 63.9–65.1 | **−49.3 mA** |
| E. One refresh | 1.29 mAh / 30.0 s from `render_begin` | 1.36 mAh / 33.3 s from the rail-on line | 145.6–148.1 mA mean | same refresh; run 2's window starts ~4 s earlier |
| F. Deep sleep, ALDO3 on, ALDO4 off | 16.07 mA | **16.07 mA** | 1 rep, 115 s | identical |
| G. One wake cycle | 2.01 mAh / ~41 s | 2.06 mAh / 43 s | 1 rep | same |

## Evidence

Every ALDO4 power-down logged all five panel lines low, and every power-up
restored CS and RESET:

```
15:01:57.761 photopainter_display event=panel_lines state=parked dc=0 cs=0 sclk=0 mosi=0 reset=0
15:01:57.775 photopainter_test event=auto_test state=C rep=1 phase=begin
15:03:58.499 photopainter_display event=panel_lines state=restored dc=0 cs=1 sclk=0 mosi=0 reset=1
15:15:53.148 photopainter_display event=panel_lines state=parked dc=0 cs=0 sclk=0 mosi=0 reset=0
15:15:53.149 deep_sleep: Sleeping for 120000000us
```

The full set of boundary lines is in `boundaries.log`; `trace-1s.csv` is the
trace reduced to 1 s.

## Findings

1. **The back-powering penalty is gone.** With the control lines low, ALDO4 off
   now matches ALDO4 on (C ≈ A, D ≈ B). SPI clock and data already idled low;
   CS, DC, and RESET were the paths.
2. **ALDO4 off saves almost nothing while the ESP32 is awake** (about 0.6 mA,
   within the repetition spread). The idle panel draws essentially nothing from
   its rail; the awake saving that matters is the audio path (about 56 mA).
3. **The monitoring overhead was not inflating idle numbers.** A and B match
   run 1 although run 1 had the web UI's event stream open.
4. **Deep sleep is unchanged at 16.07 mA**, as expected: in sleep the ESP32 does
   not drive the panel lines.
