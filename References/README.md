# Upstream source references

The full Waveshare demonstration tree is useful when tracing why this board
behaves as it does, but it is not vendored here. The links below are pinned to an
exact commit so a claim in [`HARDWARE.md`](../HARDWARE.md) can be checked against
the source it came from, whatever upstream does later.

## Primary vendor source

- Repository: <https://github.com/waveshareteam/ESP32-S3-PhotoPainter>
- Pinned reference: [`a5e8f757ba0cafbb5586f07d3e83bda3184c0845`](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/tree/a5e8f757ba0cafbb5586f07d3e83bda3184c0845)
- Upstream release noted at that commit: 1.5.0
- Commit date: 2026-05-19 +08:00
- Pin last checked against upstream: 2026-08-31. The pin is deliberate, not a
  claim that it is upstream's newest commit; re-check before relying on it.

Relevant immutable paths:

- [PhotoPainter board pin definitions](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/01_Example/xiaozhi-esp32/main/boards/waveshare-s3-PhotoPainter/config.h)
- [PhotoPainter board integration](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/01_Example/xiaozhi-esp32/main/boards/waveshare-s3-PhotoPainter/esp32-s3-PhotoPainter.cc)
- [AXP2101 PMIC initialization](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/01_Example/xiaozhi-esp32/components/pmicpower/power_bsp.cpp)
- [Display implementation and e-paper pins](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/01_Example/xiaozhi-esp32/components/port_bsp/display_bsp.cpp)
- [SD card implementation](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/01_Example/xiaozhi-esp32/components/port_bsp/sdcard_bsp.cpp)
- [Audio codec implementation](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/01_Example/xiaozhi-esp32/components/port_bsp/codec_bsp.cpp)
- [Button implementation](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/01_Example/xiaozhi-esp32/components/port_bsp/button_bsp.c)
- [LED implementation](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/01_Example/xiaozhi-esp32/components/port_bsp/led_bsp.c)
- [Standalone Arduino PMIC/audio example](https://github.com/waveshareteam/ESP32-S3-PhotoPainter/blob/a5e8f757ba0cafbb5586f07d3e83bda3184c0845/05_ArduinoExample/01_Audio_Test/power_bsp.cpp)

The vendor project contains an MIT-licensed Xiaozhi-based application plus
components with their own licenses. Refer to the licenses in that repository;
the GPL-3.0 license of this ESPHome research project does not replace them.

## Secondary upstream

The vendor application is derived from the Xiaozhi ESP32 project:

- Repository: <https://github.com/78/xiaozhi-esp32>
- Reference observed during this curation, as of 2026-08-31:
  [`bb9122ab08c3083eeb4f67b3974b7afe771723b8`](https://github.com/78/xiaozhi-esp32/tree/bb9122ab08c3083eeb4f67b3974b7afe771723b8)

Use the Waveshare repository for PhotoPainter-specific evidence; use Xiaozhi
only to trace shared framework behavior or licensing.

## Vendor downloads

These archives are linked from the Waveshare product wiki and were cached locally
during the research. They are not republished here.

- [ESP32-S3-PhotoPainter-Demo.zip](https://files.waveshare.com/wiki/ESP32-S3-PhotoPainter/ESP32-S3-PhotoPainter-Demo.zip):
  the vendor demo source, SD card assets, and the factory firmware image
  (`ESP32-S3-PhotoPainter-factory.bin`).
- [PhotoPainter_B-BMP.zip](https://files.waveshare.com/wiki/PhotoPainter%20(B)/PhotoPainter_B-BMP.zip):
  eight sample six-colour bitmaps at 800 x 480 and 480 x 800. The 480 x 480
  dithering test image is a separate file in the vendor repository; see
  [TESTING.md](../TESTING.md#native-image-dithering).

## One caveat on early evidence

Some early diagnostics were informed by an older vendor snapshot with different
directory names and PMIC code (`components/axpPower/axp_prot.cpp`), whose exact
upstream commit could not be established. Nothing stated in this repository rests
on it alone — everything was rechecked against the pinned source above or against
the physical board.

## Demo sample image

The demo's sample-image page shows a rainbow lorikeet: a photo by
[David Clode on Unsplash](https://unsplash.com/photos/G7Jd9fMuRHs) (Unsplash
licence), reduced to the panel's six colours with Atkinson dithering by
[PhotoPainter E-Ink Spectra 6 image converter](https://github.com/Toon-nooT/PhotoPainter-E-Ink-Spectra-6-image-converter)
(MIT; its readme states the sample images are Unsplash-licensed). The build
downloads
[`samples/david-clode-G7Jd9fMuRHs-unsplash_scale_ATK_output.bmp`](https://github.com/Toon-nooT/PhotoPainter-E-Ink-Spectra-6-image-converter/blob/74a575d3871230ab7981992ade5fc3a035bf79ef/samples/david-clode-G7Jd9fMuRHs-unsplash_scale_ATK_output.bmp)
at compile time from immutable commit `74a575d` (2025-09-06): 800 x 480, 24-bit,
exactly the panel's six colours (SHA-256
`1000f22ec6b308d27f52652a3327a67abc7de0d67adb06132036531971e02af0`). It is not
stored in this repository.
