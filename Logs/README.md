# Diagnostic logs

Sanitized serial and ESPHome logs captured from the physical Rev 2.0 unit
during bring-up and the hardware investigation, 2026-08-21 to 2026-09-01. Later
current measurements, with their boundary lines, are in
[`Measurements/`](../Measurements/).

These are raw evidence rather than curated examples. They span several
iterations of the configuration, including bring-up firmware that no longer
exists, so a given log shows what the board did at that moment and not
necessarily how the published profiles behave today. The node name in each log
tells you which firmware produced it.

When interpreting one, the context that matters is listed under "Record for
every run" in [`TESTING.md`](../TESTING.md): board revision, ESPHome version,
USB and battery state, reset source, and time unpowered. These captures predate
the version and power-on-reason lines that 1.0.0 prints at boot, so that context
comes from the capture's file name and this page.

## How these logs were sanitized

Raw ESPHome and serial output routinely contains Wi-Fi credentials, API and OTA
keys, hostnames, MAC addresses, and LAN IP addresses, so raw captures never
leave the development machine. Only sanitized logs are published here.

These logs were sanitized before publication by a local tool that is not part
of this repository. What that means for reading them:

- Literal secrets were harvested from the private working configuration — the
  Wi-Fi SSID and password, API encryption key, OTA and fallback access-point
  passwords — and removed by exact match.
- SSIDs, BSSIDs, MAC addresses, IPv4 addresses, and network `host:port` values
  are replaced by placeholders such as `<mac-1>` and `<ipv4-2>`. Each distinct
  value keeps one stable placeholder across every file, so you can still
  correlate an access point or address between runs.
- The development unit's node name and area were rewritten to the neutral
  `waveshare-photopainter` and `Waveshare` (the 1.0.0 examples use
  `photopainter`). Bring-up node names such as `photopainter-display-rail`
  are kept: they say which firmware produced a log and carry no installation
  identity.
- Absolute paths under the capturing user's home directory are replaced with a
  placeholder, keeping the repository-relative part so a build log is still
  traceable to the tree that produced it.
- Everything diagnostic is intact — timestamps, log levels, tags, register
  reads and writes, GPIO levels, timings, and error text. I2C addresses such as
  `Address: 0x51` are preserved; only network addresses were redacted.

A file was not published unless it passed a residual check for known secrets,
MAC addresses, IPv4 addresses, and un-redacted network names.

## Naming

Files are named from the capture's modification time plus its original name, so
runs sort chronologically and stay traceable to the raw file:

`YYYY-MM-DD_HHMMSS_<original-name>.log`

The original name goes through the same redaction as the contents before it
becomes a filename. A capture named after the development unit would otherwise
publish that name in the file listing while the contents themselves were clean.
