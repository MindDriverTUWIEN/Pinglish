# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.02] - 2026-11-26

First public release.

### Added
- Speech is also written into Pinglish Input as Pinglish, so typing can
  continue after dictation.
- Persian punctuation (`؟` `،` `؛`) in Persian Output, including spoken
  "علامت سوال" after a pause.
- Taskbar pin name "Pinglish" with the app icon and launcher.
- The speech key is read from `GOOGLE_SPEECH_KEY` or `data/speech_key.txt`.

### Fixed
- Live speech results now appear without moving the mouse.
- The last words before stopping, and soft word endings, are no longer cut.
- A soft first word right after pressing the mic is kept.
- A silent headset no longer freezes the mic, and Stop always ends.
- A crash when the mic was pressed during the start-up check.
- Quit always ends the app, and the window never stays on "Working...".
- Live convert always starts switched on.
