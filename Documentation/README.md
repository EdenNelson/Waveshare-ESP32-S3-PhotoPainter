# Documentation provenance

The PDF files used during development are retained locally but intentionally
ignored by Git. This keeps the public repository focused and avoids implying
that the project’s GPL-3.0 license grants redistribution rights for third-party
manuals or data sheets.

The Waveshare product wiki is the authoritative starting point for the board
schematic, dimensions, display documentation, and firmware resources:

- <https://www.waveshare.com/wiki/ESP32-S3-PhotoPainter>
- <https://github.com/waveshareteam/ESP32-S3-PhotoPainter>

Every document below is linked to an upstream copy. On 2026-11-13 each linked
file was downloaded and its SHA-256 compared with the local research copy; a
match means the link serves the exact bytes the research used. The hashes do not
assert ownership or redistribution permission.

| Document | Subject | Upstream copy | Matches research copy | SHA-256 |
| --- | --- | --- | --- | --- |
| `ESP32-S3-PhotoPainter-Schematic.pdf` | PhotoPainter board schematic | [Waveshare](https://files.waveshare.com/wiki/ESP32-S3-PhotoPainter/ESP32-S3-PhotoPainter-Schematic.pdf) | Yes | `82472764688ed346dcb264a71b0260bb74de4efa6fc8843f8da0417e9f99c6ec` |
| `PhotoPainter_dimension.pdf` | Mechanical dimensions | [Waveshare](https://files.waveshare.com/wiki/PhotoPainter%20(B)/PhotoPainter_dimension.pdf) | Yes | `6f6e6b1251f9a5b432646519c643d0b6fb19ba95f567da7b0b0829f235e75985` |
| `7.3inch-e-Paper-(E)-user-manual.pdf` | Spectra E6 display | [Waveshare](https://files.waveshare.com/wiki/7.3inch-e-Paper-HAT-(E)/7.3inch-e-Paper-(E)-user-manual.pdf) | Yes | `28243726fb6c99ddbc6106ba91dff15ece1e9d9b6183ecd042a63f327ae5265c` |
| `Esp32-s3_datasheet_en.pdf` | ESP32-S3 | [Waveshare](https://files.waveshare.com/wiki/common/Esp32-s3_datasheet_en.pdf); current revisions from [Espressif](https://www.espressif.com/en/support/documents/technical-documents) | Yes (Waveshare copy) | `b79310e52e90599920fb067c9365263a18943c2efc4b9788edffc2b2d6cdefa1` |
| `ES7210_DS.pdf` | ES7210 audio ADC | [Waveshare](https://files.waveshare.com/wiki/common/ES7210_DS.pdf) | Yes | `e95f49299e8bc11f1bdc711c912c76879410f2201412849a201ed708188208ec` |
| `ES8311.DS.pdf` | ES8311 audio codec | [Waveshare](https://files.waveshare.com/wiki/common/ES8311.DS.pdf) | Yes | `be42a2cb09093378feaccf55c227be579edc5a17786a11cc34254ea91264538a` |
| `Pcf85063atl1118-NdPQpTGE-loeW7GbZ7.pdf` | PCF85063ATL RTC | [Waveshare](https://files.waveshare.com/wiki/common/Pcf85063atl1118-NdPQpTGE-loeW7GbZ7.pdf); product page at [NXP](https://www.nxp.com/products/PCF85063A) | Yes (Waveshare copy) | `93b384873539e770305b8982bcfa6387eac695650063b6a11279beae7a20602a` |
| `SHTC3_Datasheet.pdf` | SHTC3 temperature/humidity sensor | [Waveshare](https://files.waveshare.com/wiki/common/SHTC3_Datasheet.pdf); product page at [Sensirion](https://sensirion.com/products/catalog/SHTC3) | Yes (Waveshare copy) | `d315fe3d00282ece1d8901c0936f8bcbaa87b159bcd0e71f9002d1f03b57a8f1` |
| `AXP2101.pdf` | AXP2101 power management IC, "Single Cell NVDC PMU with E-gauge", 63 pages | [LCSC component datasheet](https://www.lcsc.com/search?q=AXP2101) | Source of the research copy; exact LCSC file URL not recorded | `9e51d16d84d905c32a001a123be8e6c58213ee21e42d5bdb1458b731dba10f6d` |
| `X-power-AXP2101_SWcharge_V1.0.pdf` | AXP2101, as hosted by Waveshare | [Waveshare](https://files.waveshare.com/wiki/common/X-power-AXP2101_SWcharge_V1.0.pdf) | No: a different file from the research copy; check register details against the copy above | `e3754322312be3b3bbddba880efa036bd6575d59aac8a58e603608bcbc19a795` |

To follow the register and schematic references in
[`HARDWARE.md`](../HARDWARE.md) against the same documents, download them from
the sources above using the listed names and check them:

```sh
shasum -a 256 Documentation/*.pdf
```

A hash that does not match means you have a different revision, and a register
map may have moved. When an upstream document changes, its new hash and revision
date are added here as a separate row rather than replacing the evidence an
earlier test relied on.
