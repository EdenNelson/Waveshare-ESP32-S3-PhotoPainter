# PPK2 run 4 — clamped sleep (state X) on battery input at 4.0 V, 2026-11-16

The battery-input counterpart to state X in
[run 1](../2026-11-14_ppk2-run1-usbc-5v0/README.md). It pairs with state F in
[run 3](../2026-11-16_ppk2-run3-battery-4v0/README.md) to give the cost of keeping
the shared I2C bus working in deep sleep, measured at the battery.

**State X is not a supported configuration.** It reproduces the failure mode of
firmware that clears ALDO3 before sleep, and it needs a full power drain to
recover.

## Run header

| Field | Value |
| --- | --- |
| Firmware | `edennelson.waveshare-esp32s3-photopainter` **1.0.0-rc.12**, normal composition plus one private test-only button (not published, not supported); compiled 2026-11-16 10:00:04 |
| ESPHome | 2026.10.2 |
| Test button | Safe panel shutdown and ALDO4 off through the package's display-power path, then REG90 bit 2 (ALDO3) cleared by read-modify-write, then ESP32 deep sleep on a 2 min timer. ALDO2 is not modified. |
| Supply | Nordic PPK2, source-meter mode, **4000 mV into the battery connector**, USB-C unplugged; output on 10:13:49 |
| Supply as seen by the PMIC | `status1=0x18` (battery present, no VBUS) |
| Board | Same as run 3 |
| Instrument | `ppk2-api`, ~100 kS/s, 10 ms windows on the host clock; 26.9 M samples |

## Result

| State | Battery 4.0 V | USB-C 5.0 V (run 1) |
| --- | --- | --- |
| F. Deep sleep, ALDO3 on, ALDO4 off (run 3 / run 1) | 14.46 mA = 57.8 mW | 16.07 mA = 80.4 mW |
| **X. Deep sleep, ALDO3 and ALDO4 off, bus clamped** | **3.18 mA = 12.7 mW** (five 20 s blocks, 3.182–3.184; peak 4.1 mA) | 4.79 mA = 24.0 mW |
| **F − X: cost of keeping I2C working** | **11.27 mA = 45.1 mW** | 11.28 mA = 56.4 mW |

The X window runs from 5 s after `Sleeping for 120000000us` (10:15:47.769) to the
wake current rise (10:17:46.7): 101.7 s.

## Evidence

```
10:15:43.760 photopainter_display event=rail_transition old=on new=off result=ok rail=aldo4 reg90=0xFF->0xF7 aldo3=on
10:15:43.760 photopainter_test event=clamp_test phase=aldo3_off reg90=0xF7->0xF3 aldo4=0 display_power_down_ok=1 gpio7_amp=0
10:15:43.761 photopainter_test event=clamp_test phase=after_write write_ok=1 readback_ok=1 readback=0xF3 sda=1 scl=1
10:15:46.236 photopainter_i2c event=poll result=failed device=axp2101 rtc=failed sda=0 scl=0
10:15:47.769 deep_sleep: Sleeping for 120000000us
10:18:04.277 photopainter_i2c event=recovery result=exhausted bus=unavailable
```

After the wake, every poll failed with SDA and SCL low and bounded recovery ended
`exhausted`. The PPK2 output was then switched off for 104 s (10:18:19 to
10:20:03). On power-up the board reported `bus=available axp_valid=1
rtc_valid=1 ldo_enable=0xFF sda=1 scl=1` (10:21:05).

## Findings

1. **Keeping I2C working costs 11.27 mA of battery current in deep sleep.** That
   is the same current as through USB-C (11.28 mA), so the cost is a fixed
   current rather than a fixed power. One reading (an inference, not tested
   here): ALDO3 is a linear regulator, so its load current passes straight
   through to the input whatever the supply.
2. **In relative terms**, clearing ALDO3 cuts deep-sleep current from 14.46 mA
   to 3.18 mA, about 4.5× less, at the price of the PMIC, RTC, SHTC3, and
   codecs being unreachable until a full power drain.
3. **The clamp onset is now bracketed at 1 ms to 2.48 s after ALDO3 is cleared.**
   The read-back 1 ms after the write succeeded with both lines high. The next
   poll, 2.48 s later, failed with both lines low. Run 1's bracket was 3 ms to
   4.07 s.
