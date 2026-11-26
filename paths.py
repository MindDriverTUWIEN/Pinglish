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


def _packaged_app_id() -> str | None:
    """The AppUserModelID when running from an MSIX package (Microsoft Store), else None.

    A packaged app gets its identity from the package: the Start menu tile,
    taskbar pin and start command all belong to it. Code that sets its own
    identity must leave it alone then.
    """
    if os.name != "nt":
        return None
    try:
        import ctypes

        get_id = ctypes.windll.kernel32.GetCurrentApplicationUserModelId
        length = ctypes.c_uint32(0)
        # 15700 = APPMODEL_ERROR_NO_APPLICATION (not packaged), 122 = buffer too small
        if get_id(ctypes.byref(length), None) != 122:
            return None
        buf = ctypes.create_unicode_buffer(length.value)
        if get_id(ctypes.byref(length), buf) != 0:
            return None
        return buf.value or None
    except Exception:
        return None


# Set inside the Microsoft Store (MSIX) version, None for the .exe installer and source.
PACKAGED_APP_ID = _packaged_app_id()
PACKAGED = PACKAGED_APP_ID is not None

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

# Written by the .exe installer (not present in the MSIX package): [speech] enabled=0 when the user turned speech
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
