# Changelog

All notable changes to Tech2 Card Writer for Linux are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-10-25

### Added

- GTK4/libadwaita desktop app for writing Saab/GM Tech 2 PCMCIA card images.
- Automatic detection of `/dev/ttyUSB*`, `/dev/ttyACM*`, and `/dev/ttyS*`
  serial ports, with access-status reporting.
- Card image validation: `T2  ` header, exact 10 MB or 32 MB size, version
  hints from the filename, and per-version warnings (v44.000 on a 9-5,
  English-only v143.000, 32 MB-only images).
- Private Wine prefix creation and automatic `COM1` mapping for the selected
  adapter.
- Guided pre-write checklist: 12 V supply, correct PCMCIA card, backup/risk.
- Bundled Wine 11.20 amd64-wow64 runtime and unmodified Card Writer
  (`Card_writer.exe` by AlexRE, 2011) in the `.deb` and release builds.
- Command-line options: `--list-ports`, `--inspect`, `--image`, `--port`,
  `--launch`, `--debug`, `--version`.
- Per-run logs under `~/.local/state/tech2-cardwriter/logs/`.
- Desktop entry, AppStream metainfo, scalable icon, and man page.
- Makefile targets: `check`, `fetch`, `install`, `install-bundled`,
  `uninstall`, `deb`, `run`, `dev`, `man`, `clean`, `distclean`.
- Debian packaging with bundled runtime and launcher at
  `/usr/bin/tech2-cardwriter`.
- Documentation: README, hardware guide, Saab card-version guide, changelog.

### Notes

- No card images or proprietary binaries are included in the git repository;
  `make fetch` downloads and checksum-verifies them.
- Card Writer is © 2011 AlexRE and remains freeware. Tech 2 card images are
  © Saab/GM and must be supplied by the user.
