# PPK2 run 1 — USB-C at 5.0 V, 2026-11-14

First current measurement on this board, taken with the procedure in
[TESTING.md](../../TESTING.md#current-consumption). One board, one supply
topology, one session. Treat these as a first characterization, not as
battery-life claims: the battery-input run has not been done, and two monitoring
clients were connected throughout (see the run header).

## Run header

| Field | Value |
| --- | --- |
| Firmware | `edennelson.waveshare-esp32s3-photopainter` **1.0.0-rc.11**, normal composition (demo + web UI, INFO logging); factory image SHA-256 `7be1beaf8457ad01…` |
| ESPHome | 2026.10.2 |
| State X firmware | private comparison build: the same composition plus one test-only button (not published, not supported) |
| Supply | Nordic PPK2 in source-meter mode, **5000 mV into the board's USB-C** through a power-only pigtail; PPK2 output enabled at 14:03:00 |
| Board | Rev 2.0; Li-ion **removed**; RTC backup cell **removed**; insulating back **off**; SD card fitted (14,902 MB) |
| Network | Wi-Fi associated; **web UI open in a browser (live event stream)** and an **ESPHome API log client connected** for the whole run |
| Instrument | `ppk2-api`, ~100 kS/s, recorded as 10 ms windows (mean/max/min) on the host clock; 240.9 M samples, 14:03:00–14:43:00 |
| Display page | Sample image (left selected from an earlier test); refresh cost is not content-dependent to first order |
| Logging | Boundaries from the API log on the same host clock — see `boundaries.log` (device IP redacted) |

`trace-1s.csv` is the full trace reduced to 1 s means with the 10 ms peak and
minimum. The PMIC itself reported the supply as `USB-C Voltage 5.00 V`.

## Results

Steady states exclude the first 5 s after their opening boundary. Mean current
is at the 5.0 V input, so it includes the PMIC's conversion losses.

| State | Reps | Mean current | Spread | Peak (10 ms) |
| --- | --- | --- | --- | --- |
| A. Idle, everything on | 3 | **119.7 mA** | 119.4–120.2 | ~0.8–1.4 A transients |
| B. Audio in logical low power | 3 | **63.3 mA** | 60.6–66.0 | ~0.8 A |
| C. Display rail (ALDO4) off, audio on | 2 | **127.9 mA** | 127.0–128.8 | ~0.8 A |
| D. Display rail off, audio off | 3 | **113.8 mA** | 113.3–114.3 | ~0.8 A |
| E. One display refresh | 3 | **1.29 mAh** over **30.0 s** (154 mA mean) | 1.279–1.292 mAh | ~1.7 A |
| F. ESP32 deep sleep, ALDO3 on, ALDO4 off | 3 | **16.07 mA** | 16.03–16.11 | 31 mA |
| G. One wake cycle (boot, Wi-Fi, first refresh) | 3 | **2.01 mAh** over **~41 s** | 1.85–2.11 mAh | ~1.2–1.4 A |
| X. Deep sleep, ALDO3 **and** ALDO4 off, bus clamped | 1 | **4.79 mA** (five 20 s blocks, 4.786–4.791) | — | 53 mA |

Repetition 2 has no state C: the display rail was switched off with audio still
off, so that window is a D. The log shows every transition, so no window is
ambiguous.

### Boundary lines

Each window opens on a log line quoted from `boundaries.log`:

| State | Rep 1 | Rep 2 | Rep 3 |
| --- | --- | --- | --- |
| A | `14:04:06.167 photopainter_state event=level … audio=active` | after G1 settles (~14:15:00) | after G2 settles (~14:23:05) |
| B | `14:06:21.339 photopainter_audio event=transition old=active new=low_power result=ok` | `14:16:36.545` (same line) | `14:24:16.387` (same line) |
| C | `14:08:02.266 photopainter_display event=rail_transition old=on new=off result=ok` (audio restored at `14:07:17.880 … new=active result=ok`) | — | `14:26:01.799` (audio restored `14:25:17.214`) |
| D | `14:09:08.238 … old=active new=low_power result=ok` (rail already off) | `14:17:17.058 … rail_transition old=on new=off` (audio already off) | `14:27:07.598 … new=low_power result=ok` |
| E | `14:10:13.329 photopainter_dashboard event=render_begin` (rail on `14:10:08.723`) | `14:18:34.746` | `14:28:14.659` |
| F | `14:11:11.311 deep_sleep: Sleeping for 900000000us` | `14:19:36.857` | `14:29:14.322` |
| G | wake current rise 14:14:18.171 (trace) | wake rise ~14:22:20 | wake rise ~14:32:12 |
| X | `14:39:50.539 deep_sleep: Sleeping for 120000000us` after `14:39:46.457 photopainter_test event=clamp_test phase=aldo3_off reg90=0xF7->0xF3` | — | — |

E ends when the panel's activity plateau ends (five consecutive 1 s means below
100 mA); G ends when consecutive 1 s means fall below 140 mA after the refresh.
F ends at the wake current rise.

## Findings

1. **The audio path is the largest avoidable idle load.** Logical shutdown
   (codec low-power registers and amplifier off, ALDO3 kept on) removes about
   **56 mA** at 5 V while awake (A → B).
2. **Switching the display rail off while awake increases current.** A → C adds
   about 8 mA, and B → D adds about 50 mA. The leading hypothesis, recorded in
   [HARDWARE.md](../../HARDWARE.md#remaining-characterization) before this run,
   is that the ESP32 keeps driving the panel's SPI and control pins into the
   unpowered panel, back-powering it through its input protection. In deep sleep
   those pins are not driven, which fits F. Until it is fixed and re-measured,
   **"Display Enabled" off does not save power while the ESP32 is awake.**
3. **Keeping the shared I2C bus working costs about 11.3 mA in deep sleep**
   (F − X = 16.07 − 4.79 mA at the 5 V input). F is the supported state; X is
   the failure mode of firmware that de-energizes ALDO3 in sleep.
4. **The clamp takes hold after the rail is cleared, not instantly.** The
   `0x90` read-back 3 ms after clearing ALDO3 succeeded (`readback_ok=1
   readback=0xF3 sda=1 scl=1`, 14:39:46.460). By the next poll at 14:39:50.531
   (+4.07 s), the PMIC and RTC both failed with `sda=0 scl=0`. After the timer
   wake, every poll failed and bounded recovery was exhausted (`14:42:05.814
   event=recovery result=exhausted bus=unavailable`). The board was then drained.
5. **A wake cycle costs about 1.6× a plain refresh** (2.01 versus 1.29 mAh):
   boot and Wi-Fi association add about 0.7 mAh per wake.

## Not yet done

- The battery-input run (PPK2 at ~4.0 V into the battery connector, USB-C
  unplugged), which is the figure that maps to battery life.
- A repeat with no web UI or log client connected, for idle numbers that match an
  unattended installation.
- A fix for finding 2, followed by C and D re-measured.
