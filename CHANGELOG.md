# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.03] - 2026-11-26

### Added
- The mic works right after installation: Chromium's public speech key is built
  in as the default.
- Installer build recipe in `installer/` (PyInstaller + Inno Setup), bundling
  Flet's window program so nothing is downloaded at start-up.
- Privacy policy (PRIVACY.md), shown by the installer, with an option to turn
  speech recognition off.
- GitHub Actions workflow that builds the installer from source, ready for
  free code signing via SignPath Foundation.
- Optional own Google Cloud Speech-to-Text key (`data/google_cloud_key.txt`
  or `GOOGLE_CLOUD_SPEECH_KEY`), used instead of the free endpoint when set.

### Changed
- When installed, user files live in `%LOCALAPPDATA%\Pinglish`; from source
  they stay in `data/`.
- Clearer status messages when a speech service refuses a request.

## [1.02] - 2026-11-26

First public release.

### Added
- Speech is also written into Pinglish Input as Pinglish, so typing can
  continue after dictation.
- Persian punctuation (`؟` `،` `؛`) in Persian Output, including spoken
  "علامت سوال" after a pause.
- Taskbar pin name "Pinglish" with the app icon and launcher.
- The free-endpoint key can be overridden with `GOOGLE_SPEECH_KEY` or `data/speech_key.txt`.

### Fixed
- Live speech results now appear without moving the mouse.
- The last words before stopping, and soft word endings, are no longer cut.
- A soft first word right after pressing the mic is kept.
- A silent headset no longer freezes the mic, and Stop always ends.
- A crash when the mic was pressed during the start-up check.
- Quit always ends the app, and the window never stays on "Working...".
- Live convert always starts switched on.
