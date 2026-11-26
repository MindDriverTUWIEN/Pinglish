<div align="center">

<img src="assets/icon.png" alt="Pinglish icon" width="96">

# Pinglish

**Type Persian in Latin letters, or just speak it, and get proper Persian script.**

A Windows desktop app that converts Pinglish / Finglish (`salam chetori?`) into
Persian (`سلام چطوری؟`) as you type, lets you fix any word from a list of
alternative spellings, and turns spoken Persian into text live.

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![UI](https://img.shields.io/badge/UI-Flet%200.85-02569B)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Speech key](#speech-key)
- [Configuration and data files](#configuration-and-data-files)
- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Improving the dictionary](#improving-the-dictionary)
- [Building a standalone app](#building-a-standalone-app)
- [Troubleshooting](#troubleshooting)
- [Privacy](#privacy)
- [Contributing](#contributing)
- [Credits](#credits)
- [License](#license)

## Features

- **Live conversion.** Persian Output updates on every keystroke.
- **Suggested alternatives.** Click any word in Persian Output to see other
  spellings and pick the right one. Your choice is remembered from then on.
- **Persian punctuation.** `?` `,` `;` become `؟` `،` `؛` in the Persian text,
  while numbers such as `1,000` keep their comma.
- **Speech to text (fa-IR).** Press the mic and speak Persian. Words appear
  while you talk, and each phrase is replaced by the recognizer's final result.
  - Your speech is also written into Pinglish Input as Pinglish
    (`این هدفونی که گرفتی خیلی گرونه` → `in hedfooni ke gerefti kheili gerooneh`),
    so you can keep typing after what you said.
  - Spoken punctuation: say **علامت سوال** for `؟`, **علامت تعجب** for `!`,
    **نقطه** for `.` and **فاصله** for a space.
- **Clipboard tools.** Convert the clipboard, copy the Persian (or both texts),
  or paste the result straight back into the app you were using.
- **Runs in the background.** Closing the window hides it to the system tray.
  A global hotkey brings it back from any program.
- **Taskbar friendly.** Pins as *Pinglish* with its own icon.

## Requirements

- Windows 10 or 11 (the app uses WASAPI audio and Win32 window APIs)
- Python 3.11 or newer
- For speech only: a microphone, an internet connection and a
  [speech key](#speech-key)

## Installation

```powershell
git clone https://github.com/MindDriverTUWIEN/Pinglish.git
cd Pinglish

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Dependencies are pinned. The UI is written for the Flet 0.85 API, and Flet 1.x
is not compatible.

## Usage

Start the app with one of:

| Launcher | When to use it |
|---|---|
| `launch-hidden.vbs` | Everyday use. No console window. |
| `create-desktop-shortcut.ps1` | Run once to add a desktop shortcut to the launcher above. |
| `run.bat` | Debugging. Shows errors and tracebacks in a console. |
| `python main.py` | From an activated virtual environment. |

The window has three sections, top to bottom:

1. **Pinglish Input**: type or paste Latin-script Persian.
2. **Suggested Alternatives**: empty until you click a word in Persian Output.
   Pick the correct spelling from the dropdown.
3. **Persian Output**: the converted text, with the mic button in its header.

The **Live convert** switch is on whenever the app starts. Turn it off to
convert only when you press **Convert**.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl` + `D` (`Strg` + `D`) | Show the window from any program |
| `Esc` | Stop the microphone |
| `Ctrl` + `Shift` + `Q` | Quit completely (the window's X only hides it to the tray) |

### Speaking

Press the mic and wait for the status line to say **Listening on …**. A
Bluetooth headset needs about a second to switch into its call mode. Speak
naturally: a short pause finishes a phrase, and the mic stays on until you
press it again or press `Esc`. The last words before you stop are kept.

## Speech key

Speech recognition sends audio to `www.google.com/speech-api/v2/recognize`
(`fa-IR`), the undocumented endpoint Chrome uses for its own dictation. It is
not Google Cloud's paid Speech-to-Text API.

**You do not need a Google account or your own API key.** The endpoint only
asks for a key parameter, and the app uses the public key that ships in the
Chromium source code, as many open-source dictation tools do. It is not linked
to any Google account, so no costs can arise.

The key is kept out of this repository only because GitHub flags any key-like
string in code. Add it once in either way:

```powershell
# Option 1: a local file that git ignores
Set-Content data\speech_key.txt "<Chromium speech key>"

# Option 2: an environment variable
setx GOOGLE_SPEECH_KEY "<Chromium speech key>"
```

> [!NOTE]
> This endpoint is unofficial. Google publishes no limits or guarantees for it
> and may restrict or switch it off at any time. If that happens, the mic stops
> working, but text conversion is unaffected. A key from Google Cloud's
> Speech-to-Text API does not work here, because that service uses a different
> address and request format.

Text conversion works fully without a key and without internet access.

## Configuration and data files

Everything in `data/` except the shipped dictionary is created on your PC and
is ignored by git.

| File | Contents |
|---|---|
| `data/community_dict.txt` | Main Pinglish → Persian dictionary (shipped) |
| `data/user_corrections.txt` | Spellings you picked in Suggested Alternatives |
| `data/settings.json` | Hotkey, auto-copy and window size |
| `data/speech_key.txt` | Speech key for the mic (see above) |
| `data/finglish_launch.log` | Start-up and microphone log for troubleshooting |

## How it works

**Text conversion** works in three layers, and later layers win:

1. The rule and word-frequency engine of [finglish](https://github.com/elektito/finglish)
2. The community dictionary in `data/community_dict.txt` (about 2,700 entries)
3. Built-in patches and your own corrections

**Speech** is captured with `sounddevice` in WASAPI shared mode, preferring a
headset. A small voice-activity gate splits it into phrases; interim and final
results come from the recognizer and are drawn on Flet's event loop as they
arrive. Recognized Persian is turned back into Pinglish by `to_finglish()` in
`converter.py`, which reuses the dictionaries in reverse and checks that each
spelling converts back to the same word.

## Project structure

```text
Pinglish/
├── main.py                    # Flet UI, tray icon, hotkeys, mic wiring
├── converter.py               # Pinglish ⇄ Persian conversion and punctuation
├── speech_fa.py               # Microphone capture and Persian speech recognition
├── community_patches.py       # Hand-curated spellings merged at runtime
├── data/
│   ├── community_dict.txt     # Shipped dictionary
│   └── community_dict_meta.json
├── assets/                    # Icons and the Vazirmatn font
├── scripts/
│   └── build_community_dict.py
├── launch-hidden.vbs          # Console-free launcher
├── create-desktop-shortcut.ps1
├── run.bat / run.ps1          # Launchers with a console, for debugging
├── build_windows.ps1          # Standalone build with flet build
└── requirements.txt
```

## Improving the dictionary

To fix a spelling for yourself, click the word in Persian Output and pick the
right one. To improve it for everyone:

- add a line `finglish<TAB>persian` to `data/community_dict.txt`, or
- add entries to `community_patches.py` or `EXTRA_ENTRIES` in
  `scripts/build_community_dict.py`, then rebuild:

```powershell
python scripts/build_community_dict.py
```

## Building a standalone app

```powershell
.\.venv\Scripts\Activate.ps1
.\build_windows.ps1
```

The output in `build/windows/` runs without a Python installation.

## Troubleshooting

| Problem | What to do |
|---|---|
| Typing does nothing | Check that **Live convert** is on, or press **Convert**. |
| The first word you say is missing | Wait for **Listening on …** before speaking. |
| "… sends no sound" | Take the headset out of its case or reconnect it. |
| "Persian speech recognition is unavailable" | Check your internet connection and [speech key](#speech-key). |
| Nothing appears at start | Run `run.bat` to see errors, and read `data/finglish_launch.log`. |
| An old pin says "Flet description" | Unpin it, start the app, and pin it again. |

## Privacy

- Text conversion runs entirely on your PC.
- When you use the mic, your audio is sent to Google's speech service for
  recognition. Nothing is sent while the mic is off.
- Corrections and settings stay in `data/` on your PC.

## Contributing

Issues and pull requests are welcome. Dictionary fixes are especially useful.
Please describe the Pinglish you typed, what you got and what you expected.

## Credits

- Conversion engine and base word list:
  [elektito/finglish](https://github.com/elektito/finglish) (MIT)
- UI: [Flet](https://flet.dev/)
- Font: [Vazirmatn](https://github.com/rastikerdar/vazirmatn)
  (SIL Open Font License, see `assets/fonts/OFL.txt`)
- Audio: [python-sounddevice](https://github.com/spatialaudio/python-sounddevice)
- Tray and helpers: pystray, Pillow, pyperclip, keyboard, pyautogui

## License

Released under the [MIT License](LICENSE).
