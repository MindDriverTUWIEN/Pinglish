"""Where Pinglish reads its resources and keeps the user's files.

From source, everything stays in the project folder, as before:
resources next to main.py, user files in data/.

Installed (a PyInstaller build in Program Files), the program folder is
read-only, so user files go to %LOCALAPPDATA%\\Pinglish, and resources are read
from the bundle.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))

# Read-only: assets/, data/community_dict.txt, the Flet window program.
RES_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

# Writable: settings, corrections, log, speech keys.
if FROZEN:
    USER_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Pinglish"
else:
    USER_DIR = RES_DIR / "data"
USER_DIR.mkdir(parents=True, exist_ok=True)

# Folder that holds flet.exe inside an installed build.
FLET_CLIENT_DIR = RES_DIR / "flet_client" / "flet"

# Written by the installer: [speech] enabled=0 when the user turned speech
# recognition (which sends mic audio to Google) off during installation.
INSTALL_INI = Path(sys.executable).resolve().parent / "pinglish.ini" if FROZEN else None


def speech_enabled() -> bool:
    """False only when the installer was told to turn speech recognition off."""
    if INSTALL_INI is None or not INSTALL_INI.is_file():
        return True
    import configparser

    ini = configparser.ConfigParser()
    try:
        ini.read(INSTALL_INI, encoding="utf-8")
        return ini.getboolean("speech", "enabled", fallback=True)
    except (configparser.Error, ValueError, OSError):
        return True
