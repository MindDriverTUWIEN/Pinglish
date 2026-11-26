r"""
Pinglish - Local Pinglish to Persian (Farsi) converter for Windows.

A lightweight desktop helper inspired by Google Translate's Persian transliteration,
but 100% offline and running locally on your PC.

Features (MVP):
- Live converter (type Latin Pinglish -> see Persian)
- Click a Persian word to fix it: alternatives appear in a middle strip with a dropdown
- One-click copy Persian (or both)
- Convert current clipboard content
- Microphone: speak Persian, the text is written into Persian Output as you talk
- System tray (show / hide / convert clipboard / quit)
- X button hides the window (app keeps running in tray). Strg+D or tray menu restores it.
- Esc stops the microphone. Strg+Shift+Q quits fully.
- Clean modern UI via Flet

Run:
    .venv\Scripts\Activate.ps1
    python main.py

Build a standalone Windows exe later with:
    flet build windows --name Pinglish --icon assets/icon.png
"""
import json
import os
import re
import sys
import threading
import time
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import flet as ft
import keyboard
import pyautogui
import pyperclip
import pystray
from PIL import Image, ImageDraw

# Local clean converter (no prints)
from paths import FLET_CLIENT_DIR, FROZEN, PACKAGED, PACKAGED_APP_ID, RES_DIR, USER_DIR, speech_enabled
from converter import apply_user_correction, convert, convert_word, persian_punctuation, to_finglish
from speech_fa import SpeechError, listen_persian, probe_microphone

# Latin Finglish tokens only (must match converter tokenization)
_WORD_RE = re.compile(r"([A-Za-z']+)([^A-Za-z']*)")

# ----------------------------- Windows native helpers (to force window hide like in Qt apps) -----------------------------
def _hide_window_native(title: str):
    """Use Win32 API to force-hide the window by title. This helps make the X button
    truly 'close' the visual window (remove from screen and taskbar) while the process
    and tray icon stay alive. Inspired by how the Qt version uses native hide()."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            # SW_HIDE = 0
            user32.ShowWindow(hwnd, 0)
            # Additional flags to hide from taskbar if needed
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0080)  # SWP_HIDEWINDOW
    except Exception as ex:
        print("Native hide failed:", ex)


def _hide_window_to_tray(page: ft.Page, source: str = "unknown"):
    """Hide the main window but keep the process, tray icon, and hotkey alive."""
    page.window.skip_task_bar = True
    page.window.minimized = True
    page.window.visible = False
    page.update()
    _hide_window_native(page.title)
    _log_launch(f"Window hidden via {source}. Tray and hotkey remain active.")


def _show_window_from_tray(page: ft.Page, source: str = "unknown"):
    """Restore and focus the main window after it was hidden to tray."""
    page.window.visible = True
    page.window.minimized = False
    page.window.skip_task_bar = False
    page.window.focused = True
    page.update()
    _log_launch(f"Window restored via {source}")
    _schedule_native_window_icon()


# Windows taskbar and title-bar icons come from flet.exe, not from Python.
# page.window.icon often never replaces that logo. Paint our .ico onto the
# real window, and give the Flet process its own AppUserModelID so Windows
# does not keep grouping this app under the shared Flet icon.
# The MSIX (Store) version must keep the identity its package gives it.
APP_USER_MODEL_ID = PACKAGED_APP_ID or "Local.Finglish.Desktop"
_native_icons: Dict[str, int] = {"big": 0, "small": 0}


def _window_icon_path() -> Optional[str]:
    """Absolute .ico path. A space-free copy is used because Flet's icon loader drops paths with spaces."""
    ico = APP_DIR / "assets" / "icon.ico"
    if not ico.is_file():
        png = APP_DIR / "assets" / "icon.png"
        return str(png) if png.is_file() else None
    try:
        local = Path(os.environ.get("LOCALAPPDATA", "")) / "Finglish"
        local.mkdir(parents=True, exist_ok=True)
        dest = local / "icon.ico"
        data = ico.read_bytes()
        if not dest.is_file() or dest.read_bytes() != data:
            dest.write_bytes(data)
        return str(dest)
    except Exception as ex:
        _log_launch(f"Could not copy window icon: {ex}")
        return str(ico)


def _load_native_icons(icon_path: str) -> Tuple[int, int]:
    if _native_icons["big"]:
        return _native_icons["big"], _native_icons["small"]
    user32 = ctypes.windll.user32
    user32.LoadImageW.argtypes = [
        wintypes.HINSTANCE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.LoadImageW.restype = wintypes.HANDLE
    image_icon = 1
    lr_loadfromfile = 0x00000010
    big = user32.LoadImageW(None, icon_path, image_icon, 32, 32, lr_loadfromfile) or 0
    small = user32.LoadImageW(None, icon_path, image_icon, 16, 16, lr_loadfromfile) or 0
    _native_icons["big"] = int(big)
    _native_icons["small"] = int(small or big)
    return _native_icons["big"], _native_icons["small"]


def _finglish_window_handles() -> List[int]:
    user32 = ctypes.windll.user32
    found: List[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if title.startswith("Pinglish"):
            found.append(int(hwnd))
        return True

    user32.EnumWindows(_enum, 0)
    return found


def _apply_native_window_icon() -> bool:
    """Replace the flet.exe icon on the title bar and taskbar."""
    icon_path = _window_icon_path()
    if not icon_path:
        return False
    big, small = _load_native_icons(icon_path)
    if not big:
        _log_launch(f"LoadImage failed for {icon_path}")
        return False

    user32 = ctypes.windll.user32
    user32.SendMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.SendMessageW.restype = wintypes.LPARAM
    set_class_long = user32.SetClassLongPtrW
    set_class_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    set_class_long.restype = ctypes.c_void_p

    wm_seticon = 0x0080
    icon_small, icon_big = 0, 1
    gclp_hicon, gclp_hiconsm = -14, -34
    applied = False
    for hwnd in _finglish_window_handles():
        user32.SendMessageW(hwnd, wm_seticon, icon_big, big)
        user32.SendMessageW(hwnd, wm_seticon, icon_small, small)
        set_class_long(hwnd, gclp_hicon, big)
        set_class_long(hwnd, gclp_hiconsm, small)
        _set_taskbar_pin_identity(hwnd, icon_path)
        applied = True
    if applied:
        _log_launch(f"Native window icon applied from {icon_path}")
    return applied


# Taskbar pinning. A pinned window gets its name, icon and start command from
# these window properties. Without them Windows uses flet.exe's own file
# description, "Flet description", and a pin that starts bare flet.exe.
_PKEY_FMTID = "{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"  # System.AppUserModel.*
_PKEY_RELAUNCH_COMMAND, _PKEY_RELAUNCH_ICON, _PKEY_RELAUNCH_NAME, _PKEY_APP_ID = 2, 3, 4, 5


class _Guid(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]


class _PropertyKey(ctypes.Structure):
    _fields_ = [("fmtid", _Guid), ("pid", ctypes.c_ulong)]


class _PropVariant(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort),
                ("r3", ctypes.c_ushort), ("pwszVal", ctypes.c_wchar_p),
                ("pad", ctypes.c_ulonglong)]


def _guid(text: str) -> _Guid:
    guid = _Guid()
    ctypes.oledll.ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(guid))
    return guid


def _pin_relaunch_command() -> str:
    """What a pinned icon runs: Pinglish.exe when installed, else the hidden launcher."""
    if FROZEN:
        return f'"{sys.executable}"'
    launcher = APP_DIR / "launch-hidden.vbs"
    windir = os.environ.get("SystemRoot", r"C:\Windows")
    if launcher.is_file():
        return f'"{Path(windir) / "System32" / "wscript.exe"}" "{launcher}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pythonw if pythonw.is_file() else sys.executable}" "{APP_DIR / "main.py"}"'


def _set_taskbar_pin_identity(hwnd: int, icon_path: str) -> bool:
    """Name the window "Pinglish" for pinning, with our icon and launcher."""
    try:
        ctypes.windll.ole32.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED
        iid = _guid("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}")  # IPropertyStore
        store = ctypes.c_void_p()
        shell32 = ctypes.windll.shell32
        shell32.SHGetPropertyStoreForWindow.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_void_p]
        hr = shell32.SHGetPropertyStoreForWindow(hwnd, ctypes.byref(iid), ctypes.byref(store))
        if hr != 0 or not store:
            return False
        vtbl = ctypes.cast(ctypes.cast(store, ctypes.POINTER(ctypes.c_void_p))[0],
                           ctypes.POINTER(ctypes.c_void_p))
        proto = ctypes.WINFUNCTYPE
        release = proto(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
        set_value = proto(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(vtbl[6])
        commit = proto(ctypes.c_long, ctypes.c_void_p)(vtbl[7])
        fmtid = _guid(_PKEY_FMTID)
        if PACKAGED:
            # The package already names the pin and starts the app through
            # Windows; a start command pointing into WindowsApps would fail.
            values = [(_PKEY_APP_ID, APP_USER_MODEL_ID)]
        else:
            values = [
                (_PKEY_RELAUNCH_COMMAND, _pin_relaunch_command()),
                (_PKEY_RELAUNCH_NAME, APP_NAME),
                (_PKEY_RELAUNCH_ICON, f"{icon_path},0"),
                (_PKEY_APP_ID, APP_USER_MODEL_ID),  # last: it switches the others on
            ]
        ok = True
        try:
            for pid, text in values:
                key = _PropertyKey(fmtid, pid)
                var = _PropVariant(vt=31, pwszVal=text)  # VT_LPWSTR
                ok = set_value(store, ctypes.byref(key), ctypes.byref(var)) == 0 and ok
            ok = commit(store) == 0 and ok
        finally:
            release(store)
        return ok
    except Exception as ex:
        _log_launch(f"Taskbar pin name not set: {ex}")
        return False


def _schedule_native_window_icon():
    """The Flet window appears a moment after main() returns. Retry until it exists."""

    def _worker():
        for _ in range(25):
            if _apply_native_window_icon():
                return
            time.sleep(0.2)
        _log_launch("Native window icon was not applied (Pinglish window not found)")

    threading.Thread(target=_worker, daemon=True).start()


# ----------------------------- Constants & Paths -----------------------------
APP_NAME = "Pinglish"
APP_VERSION = "1.04"
APP_DIR = RES_DIR      # read-only resources (assets/, launcher)
DATA_DIR = USER_DIR    # settings, log: data/ from source, %LOCALAPPDATA%\Pinglish installed
if FROZEN and FLET_CLIENT_DIR.is_dir():
    # Installed build: use the bundled Flet window, never download one.
    os.environ.setdefault("FLET_VIEW_PATH", str(FLET_CLIENT_DIR))

SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_HOTKEY = "ctrl+d"

# Vazirmatn is the Persian face used in Google Docs. The file is in assets/fonts.
PERSIAN_FONT = "Vazirmatn"
LATIN_FONT = "Consolas"   # or "Segoe UI"

# UI palette
C_PRIMARY = ft.Colors.INDIGO_600
C_PRIMARY_DARK = ft.Colors.INDIGO_800
C_PRIMARY_LIGHT = ft.Colors.INDIGO_50
C_ACCENT = ft.Colors.TEAL_600
C_SURFACE = ft.Colors.BLUE_GREY_50
C_CARD = ft.Colors.WHITE
C_MUTED = ft.Colors.BLUE_GREY_600
C_BORDER = ft.Colors.BLUE_GREY_200
C_CHIP_ACTIVE = ft.Colors.AMBER_50
C_CHIP_BORDER_ACTIVE = ft.Colors.AMBER_300


def _tokenize_phrase(phrase: str) -> List[Tuple[str, str]]:
    """Split phrase into (word, trailing_punctuation) tokens — same rules as converter."""
    return [(m.group(1), m.group(2)) for m in _WORD_RE.finditer(phrase)]


def _build_word_slots(
    phrase: str,
    cutoff: int = 5,
    previous_slots: Optional[List[Dict]] = None,
) -> List[Dict]:
    """Build per-word slots. Reuses prior selected spellings when the Finglish token matches."""
    prev_by_token: Dict[str, str] = {}
    if previous_slots:
        for slot in previous_slots:
            alts = slot.get("alternatives") or []
            idx = slot.get("selected_idx", 0)
            if alts and 0 <= idx < len(alts):
                prev_by_token[slot["token"].lower()] = alts[idx][0]

    slots = []
    for token, punct in _tokenize_phrase(phrase):
        alternatives = convert_word(token, cutoff=cutoff)
        if not alternatives:
            alternatives = [(token, 0.0)]

        selected_idx = 0
        preferred = prev_by_token.get(token.lower())
        if preferred:
            for i, (persian, _score) in enumerate(alternatives):
                if persian == preferred:
                    selected_idx = i
                    break
            else:
                # Keep the user's preferred spelling even if not in engine list
                alternatives = [(preferred, 1.0)] + [
                    a for a in alternatives if a[0] != preferred
                ]
                selected_idx = 0

        slots.append(
            {
                "token": token,
                "punct": punct,
                "alternatives": alternatives,
                "selected_idx": selected_idx,
            }
        )
    return slots


def _persian_from_slots(slots: List[Dict]) -> str:
    # Slots keep the Latin marks typed in Pinglish Input; Persian text gets ؟ ، ؛
    return "".join(
        slot["alternatives"][slot["selected_idx"]][0] + persian_punctuation(slot["punct"])
        for slot in slots
    )


# Spoken commands while dictating Persian. Recognition often writes نقطه for نخته,
# and sometimes نکته when that word ends the sentence.
_SPOKEN_PERIOD_WORD = re.compile(
    r"(?<![\u0600-\u06FF])(?:نخته|نقطه)(?![\u0600-\u06FF])"
)
_SPOKEN_PERIOD_AT_END = re.compile(r"(?:^|\s)نکته\s*$")
_SPOKEN_QUESTION = re.compile(
    r"(?<![\u0600-\u06FF])علامت[\u200c\s]*س[وؤ]ال(?![\u0600-\u06FF])"
)
_SPOKEN_EXCLAMATION = re.compile(
    r"(?<![\u0600-\u06FF])علامت[\u200c\s]*تعجب(?![\u0600-\u06FF])"
)
_SPOKEN_SPACE = re.compile(r"(?<![\u0600-\u06FF])فاصله(?![\u0600-\u06FF])")
_POINT_OF_VIEW = re.compile(r"نقطه[\u200c\s]*نظر")


def _apply_spoken_commands(text: str) -> str:
    """Turn spoken نخته, علامت سوال, علامت تعجب, and فاصله into . ? ! and a space."""
    if not text or not text.strip():
        return ""
    kept: List[str] = []

    def _hold(match: re.Match) -> str:
        kept.append(match.group(0))
        return f"\u0000{len(kept) - 1}\u0000"

    text = _POINT_OF_VIEW.sub(_hold, text.strip())
    text = _SPOKEN_QUESTION.sub("?", text)
    text = _SPOKEN_EXCLAMATION.sub("!", text)
    text = _SPOKEN_PERIOD_WORD.sub(".", text)
    text = _SPOKEN_PERIOD_AT_END.sub(".", text)
    text = _SPOKEN_SPACE.sub(" ", text)
    text = re.sub(r"\s+([.?!])", r"\1", text)
    text = re.sub(r"([.?!])(?=[^\s])", r"\1 ", text)
    text = re.sub(r"([.?!])\1+", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    for index, phrase in enumerate(kept):
        text = text.replace(f"\u0000{index}\u0000", phrase)
    return text


_TRAILING_PUNCT = re.compile(r"[.?!,;:؟،؛\"«»]+$")
_MARKS_ONLY = re.compile(r"^[.?!,;:…؟،؛\"«»]+$")


def _slots_from_dictation(text: str) -> List[Dict]:
    """Persian speech → word slots, each with its Pinglish as the token.

    The heard Persian word is the one shown. The token is its Pinglish, which is
    written into Pinglish Input. When typing continues there, _build_word_slots
    keeps each dictated word's Persian through previous_slots.

    A spoken mark (علامت سوال → ?) belongs to the word before it. When a pause
    made it a phrase of its own, the first slot is {"lead_punct": "?"}, and
    _show_live_persian attaches it to the last word already written. As a word
    of its own it stayed an English "?"; as punctuation it is shown as ؟.
    """
    parts = [part for part in _apply_spoken_commands(text).split() if part]
    slots = []
    lead = ""
    for part in parts:
        if _MARKS_ONLY.match(part):
            mark = to_finglish(part)  # ؟ → ?, shown again as ؟ in Persian Output
            if slots:
                slots[-1]["punct"] = slots[-1]["punct"].rstrip() + mark
            else:
                lead += mark
            continue
        latin = to_finglish(part)
        tokens = _tokenize_phrase(latin)
        persian = _TRAILING_PUNCT.sub("", part) or part
        if len(tokens) == 1 and latin.startswith(tokens[0][0]):
            token, punct = tokens[0][0], tokens[0][1].strip()
            others = [a for a in convert_word(token, cutoff=5) if a[0] != persian]
        else:  # digits or Latin text: keep as heard
            token, punct, others = latin or part, "", []
        slots.append(
            {
                "token": token,
                "punct": punct,
                "alternatives": [(persian, 1.0)] + others,
                "selected_idx": 0,
                "dictated": True,
            }
        )
    for slot in slots[:-1]:
        slot["punct"] += " "
    if lead:
        slots.insert(0, {"lead_punct": lead})
    return slots

# ----------------------------- Silent launch helpers (for pythonw + VBS desktop shortcut) -----------------------------
def _show_error_box(message: str, title: str = "Pinglish - Fehler"):
    """Show a Windows message box for silent launch errors (pythonw + VBS)."""
    try:
        ctypes.windll.user32.MessageBoxW(0, str(message), title, 0x10)  # MB_OK | MB_ICONERROR
    except Exception:
        pass  # last resort

def _log_launch(msg: str):
    """Append to a log file so we can debug hidden launches."""
    try:
        log_path = DATA_DIR / "finglish_launch.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except Exception:
        pass

_log_launch("Module top-level code executed successfully (imports + constants + helpers ok)")

# ----------------------------- Persistence -----------------------------
@dataclass
class Settings:
    hotkey: str = DEFAULT_HOTKEY
    live_conversion: bool = True
    auto_copy_on_convert: bool = False
    window_width: int = 1280
    window_height: int = 920

    def save(self):
        try:
            SETTINGS_FILE.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def load(cls) -> "Settings":
        settings = cls()
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                settings = cls(**{**cls().__dict__, **data})
            except Exception:
                pass
        # A size saved while the window was hidden (e.g. 160 x 28) is not real.
        if settings.window_width < 1100 or settings.window_height < 860:
            settings.window_width, settings.window_height = cls().window_width, cls().window_height
        # Live convert is the app's main job, so every launch starts with it on.
        # Switching it off lasts until the app restarts.
        settings.live_conversion = True
        return settings


# ----------------------------- Tray Icon (pystray) -----------------------------
_tray_icon = None
_tray_thread = None


def create_tray_image() -> Image.Image:
    """Load the polished tray icon asset (falls back to a minimal glyph if missing)."""
    tray_path = APP_DIR / "assets" / "icon_tray.png"
    if tray_path.exists():
        return Image.open(tray_path).convert("RGBA")

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=(37, 99, 235, 255))
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 30)
    except Exception:
        font = ImageFont.load_default()
    text = "ف"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (size - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    return img


def run_tray(page: ft.Page, shutdown_app):
    """Run pystray icon in a background thread. Controls the Flet window."""
    global _tray_icon

    def on_show(icon, item):
        try:
            _show_window_from_tray(page, "tray menu")
        except Exception as ex:
            print("Tray show focus error:", ex)

    def on_hide(icon, item):
        print("DEBUG: Hiding window via tray menu")
        _hide_window_to_tray(page, "tray 'Hide'")

    def on_convert_clip(icon, item):
        # Run on main thread via page.run_thread or just do it and update
        def do_convert():
            try:
                text = pyperclip.paste() or ""
                if text.strip():
                    persian = convert(text)
                    pyperclip.copy(persian)
                    # Brief toast-like feedback by temporarily changing title
                    old_title = page.title
                    page.title = f"{APP_NAME} - Clipboard converted!"
                    page.update()
                    time.sleep(1.2)
                    page.title = old_title
                    page.update()
            except Exception as ex:
                print("Tray convert error:", ex)

        threading.Thread(target=do_convert, daemon=True).start()

    def on_quit(icon, item):
        # User explicitly chose to fully exit from the tray menu.
        page.run_thread(shutdown_app)

    icon_image = create_tray_image()
    menu = pystray.Menu(
        pystray.MenuItem("Pinglish öffnen / fokussieren  (Strg + D)", on_show, default=True),
        pystray.MenuItem("Fenster ausblenden (im Tray lassen)", on_hide),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Convert Clipboard (Pinglish → Persian)", on_convert_clip),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit  (Strg+Shift+Q)", on_quit),
    )

    _tray_icon = pystray.Icon(APP_NAME, icon_image, f"{APP_NAME} – Strg+D (läuft im Hintergrund)", menu)
    _tray_icon.run()


# ----------------------------- Main Flet App -----------------------------
def main(page: ft.Page):
    _log_launch("main() entered - configuring window")
    print("DEBUG: main() started, setting up Flet window...")

    # Load settings first (must exist before any settings.* use)
    settings = Settings.load()

    # Force the hotkey to Strg+D (ctrl+d) even if old settings.json has a previous combo
    if settings.hotkey != "ctrl+d":
        settings.hotkey = "ctrl+d"

    # Large enough to fully show Input + Suggested Alternatives + Persian Output
    settings.window_width = 1280
    settings.window_height = 920
    settings.save()

    page.title = f"{APP_NAME} — Offline Pinglish to Persian"
    page.window.title_bar_hidden = False
    page.window.width = settings.window_width
    page.window.height = settings.window_height
    page.window.min_width = 1100
    page.window.min_height = 860
    page.window.skip_task_bar = False
    page.window.minimized = False
    page.window.visible = True
    page.window.prevent_close = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = C_SURFACE
    # Path is relative to assets_dir. One variable file covers regular and bold.
    page.fonts = {PERSIAN_FONT: "/fonts/Vazirmatn-Variable.ttf"}
    _log_launch("Persian font: Vazirmatn")

    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=C_PRIMARY,
            primary_container=C_PRIMARY_LIGHT,
            secondary=C_ACCENT,
            surface=C_CARD,
            on_primary=ft.Colors.WHITE,
            on_surface=ft.Colors.BLUE_GREY_900,
            outline=C_BORDER,
        ),
        text_theme=ft.TextTheme(
            body_medium=ft.TextStyle(font_family="Segoe UI", size=14, color=ft.Colors.BLUE_GREY_800),
            title_medium=ft.TextStyle(font_family="Segoe UI", size=17, weight=ft.FontWeight.W_600, color=C_PRIMARY_DARK),
            label_small=ft.TextStyle(font_family="Segoe UI", size=11, color=C_MUTED),
        ),
    )
    _log_launch("Basic window properties set")
    print("DEBUG: Window properties set.")

    # Do not assign page.window.icon. On this Flet build that call asks
    # flet.exe to load the icon and the window then keeps the Flet logo,
    # or the client exits. The real icon is painted onto the window below.

    # ---------------- State ----------------
    current_persian = ""
    last_input_text = ""
    word_slots: List[Dict] = []
    selected_slot_index: Optional[int] = None  # which Persian word is being corrected
    mic_stop = threading.Event()
    mic_listening = False
    draft_len = 0
    draft_input = ""  # Pinglish of the unfinished spoken phrase, at the end of the input
    _esc_stop_hotkey = None
    mic_ui = threading.Lock()

    # ---------------- UI Components ----------------
    # Layout (always, top → bottom):
    #   1) Pinglish Input
    #   2) Suggested Alternatives  (empty until a Persian word is clicked)
    #   3) Persian Output          (converted sentence only — click a word to correct it)
    input_field = ft.TextField(
        hint_text="Type Pinglish here…  e.g. salam chetori khoshahvalid?",
        multiline=True,
        min_lines=5,
        max_lines=8,
        text_style=ft.TextStyle(font_family=LATIN_FONT, size=15, color=ft.Colors.BLUE_GREY_800),
        on_change=lambda e: on_input_change(e.control.value),
        autofocus=True,
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding(left=4, right=4, top=4, bottom=4),
        cursor_color=C_PRIMARY,
        selection_color=ft.Colors.with_opacity(0.18, C_PRIMARY),
    )
    page.input_field = input_field

    # --- MIDDLE: Suggested Alternatives (NO alternatives live here until a click) ---
    sa_hint = ft.Text(
        "Click any word in Persian Output below. Only that word will appear here with a dropdown.",
        size=14,
        color=C_MUTED,
        italic=True,
    )
    sa_finglish = ft.Text("", size=14, font_family=LATIN_FONT, color=C_PRIMARY_DARK, weight=ft.FontWeight.W_700)
    sa_arrow = ft.Text("→", size=16, color=C_MUTED, visible=False)
    sa_current = ft.Text("", size=22, font_family=PERSIAN_FONT, color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_700, rtl=True)

    sa_dropdown = ft.Dropdown(
        label="Choose correct spelling",
        hint_text="Open and pick the correct Persian word",
        options=[],
        width=380,
        text_size=18,
        text_style=ft.TextStyle(font_family=PERSIAN_FONT, size=18),
        border_color=C_PRIMARY,
        focused_border_color=C_PRIMARY,
        border_radius=10,
        filled=True,
        fill_color=ft.Colors.WHITE,
        visible=False,
        on_select=lambda e: on_alt_dropdown_select(e),
    )

    sa_clear_btn = ft.TextButton(
        "Clear selection",
        icon=ft.Icons.CLOSE,
        visible=False,
        on_click=lambda e: clear_word_selection(),
        style=ft.ButtonStyle(color=C_MUTED),
    )

    sa_active_row = ft.Row(
        [
            ft.Container(
                content=sa_finglish,
                padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                bgcolor=C_PRIMARY_LIGHT,
                border_radius=8,
                visible=False,
                data="sa_finglish_box",
            ),
            sa_arrow,
            sa_current,
            sa_dropdown,
            sa_clear_btn,
        ],
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
        run_spacing=10,
        visible=False,
    )
    # Keep a direct ref to the finglish chip container for visibility
    sa_finglish_box = sa_active_row.controls[0]

    # --- BOTTOM: Persian Output — converted words only (clickable sentence) ---
    persian_empty = ft.Text(
        "Converted Persian appears here…",
        size=18,
        color=C_MUTED,
        italic=True,
        font_family=PERSIAN_FONT,
        text_align=ft.TextAlign.RIGHT,
        rtl=True,
    )

    # Sentence is a row of clickable words that LOOK like normal text (not suggestion chips)
    persian_sentence_row = ft.Row(
        controls=[],
        wrap=True,
        spacing=2,
        run_spacing=10,
        rtl=True,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Height is updated in render_persian_output() as the sentence grows
    PERSIAN_OUTPUT_MIN_H = 72
    PERSIAN_OUTPUT_MAX_H = 520  # beyond this, the area scrolls instead of growing forever

    persian_output_host = ft.Container(
        content=persian_empty,
        padding=ft.Padding(left=20, right=20, top=16, bottom=16),
        bgcolor=ft.Colors.BLUE_GREY_50,
        border_radius=12,
        border=ft.Border.all(1, C_BORDER),
        alignment=ft.Alignment.TOP_RIGHT,
        height=PERSIAN_OUTPUT_MIN_H,
        animate_size=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
    )

    status_text = ft.Text("Ready — type Pinglish or paste from clipboard", size=12, color=C_MUTED)

    # ---------------- Core Logic ----------------
    def sync_output_from_slots():
        nonlocal current_persian
        current_persian = _persian_from_slots(word_slots)

    def _slot_persian(slot: Dict) -> str:
        alts = slot.get("alternatives") or []
        if not alts:
            return slot.get("token", "")
        idx = slot.get("selected_idx", 0)
        if idx < 0 or idx >= len(alts):
            idx = 0
        return alts[idx][0]

    def make_word_click_handler(slot_index: int):
        """Click a word in Persian Output → load ONLY that word into Suggested Alternatives."""
        def handler(_):
            nonlocal selected_slot_index
            selected_slot_index = slot_index
            render_persian_output()
            render_suggested_alternatives()
            slot = word_slots[slot_index]
            word = _slot_persian(slot)
            n = len(slot.get("alternatives") or [])
            status_text.value = (
                f"Selected «{word}» — pick the correct spelling in Suggested Alternatives (dropdown)"
                if n > 1
                else f"Selected «{word}» — only one spelling available"
            )
            page.update()

        return handler

    def _estimate_persian_output_height(n_words: int) -> int:
        """Grow the output box with content; cap + scroll for very long text."""
        if n_words <= 0:
            return PERSIAN_OUTPUT_MIN_H
        # ~10–12 Persian words per line at this font size in a ~1200px-wide pane
        words_per_line = 10
        lines = max(1, (n_words + words_per_line - 1) // words_per_line)
        line_h = 40  # font ~22 + padding + run_spacing
        pad = 36
        return max(PERSIAN_OUTPUT_MIN_H, min(pad + lines * line_h, PERSIAN_OUTPUT_MAX_H))

    def render_persian_output():
        """Persian Output = converted sentence only (clickable words, not suggestion chips)."""
        sync_output_from_slots()
        out_font = 22  # slightly smaller than before (was 28)

        if not word_slots:
            persian_output_host.content = persian_empty
            persian_output_host.height = PERSIAN_OUTPUT_MIN_H
            return

        words = []
        for idx, slot in enumerate(word_slots):
            persian_word = _slot_persian(slot)
            punct = slot.get("punct") or ""
            is_selected = selected_slot_index == idx

            # Looks like normal sentence text; mild highlight only when selected
            words.append(
                ft.Container(
                    content=ft.Text(
                        persian_word,
                        size=out_font,
                        font_family=PERSIAN_FONT,
                        color=C_PRIMARY_DARK if is_selected else ft.Colors.BLUE_GREY_900,
                        weight=ft.FontWeight.W_700 if is_selected else ft.FontWeight.W_500,
                    ),
                    padding=ft.Padding(left=4, right=4, top=2, bottom=2),
                    border_radius=6,
                    bgcolor=C_CHIP_ACTIVE if is_selected else ft.Colors.TRANSPARENT,
                    border=ft.Border.all(
                        2 if is_selected else 0,
                        C_CHIP_BORDER_ACTIVE if is_selected else ft.Colors.TRANSPARENT,
                    ),
                    on_click=make_word_click_handler(idx),
                    ink=True,
                    tooltip=f"Click to correct this word ({slot['token']})",
                )
            )
            # Keep punctuation / spacing after the word for natural reading
            if punct:
                words.append(
                    ft.Text(
                        persian_punctuation(punct) if not punct.isspace() else " ",
                        size=out_font,
                        font_family=PERSIAN_FONT,
                        color=ft.Colors.BLUE_GREY_900,
                    )
                )
            else:
                words.append(ft.Text(" ", size=out_font))

        persian_sentence_row.controls.clear()
        persian_sentence_row.controls.extend(words)

        n_words = len(word_slots)
        target_h = _estimate_persian_output_height(n_words)
        needs_scroll = target_h >= PERSIAN_OUTPUT_MAX_H and n_words > 20

        if needs_scroll:
            persian_output_host.content = ft.Column(
                [persian_sentence_row],
                scroll=ft.ScrollMode.AUTO,
                tight=True,
                expand=True,
            )
        else:
            persian_output_host.content = ft.Container(
                content=persian_sentence_row,
                alignment=ft.Alignment.TOP_RIGHT,
            )
        persian_output_host.height = target_h

    def render_suggested_alternatives():
        """
        Suggested Alternatives middle section:
        - empty hint by default
        - after a word click: ONLY that word + dropdown of alternatives
        - choosing from dropdown updates Persian Output
        """
        idle = (
            selected_slot_index is None
            or not word_slots
            or selected_slot_index >= len(word_slots)
        )
        if idle:
            sa_hint.visible = True
            sa_active_row.visible = False
            sa_finglish_box.visible = False
            sa_arrow.visible = False
            sa_current.visible = False
            sa_dropdown.visible = False
            sa_dropdown.options = []
            sa_dropdown.value = None
            sa_clear_btn.visible = False
            return

        slot = word_slots[selected_slot_index]
        alts = slot.get("alternatives") or []
        selected = slot.get("selected_idx", 0)
        if selected < 0 or selected >= len(alts):
            selected = 0
        current = alts[selected][0] if alts else slot["token"]

        sa_hint.visible = False
        sa_active_row.visible = True
        sa_finglish_box.visible = True
        sa_finglish.value = slot["token"]
        sa_arrow.visible = True
        sa_current.visible = True
        sa_current.value = current
        sa_clear_btn.visible = True

        sa_dropdown.visible = True
        sa_dropdown.options = [
            ft.DropdownOption(key=str(i), text=p)
            for i, (p, _s) in enumerate(alts)
        ]
        sa_dropdown.value = str(selected)
        if len(alts) <= 1:
            sa_dropdown.label = "Only one spelling"
            sa_dropdown.hint_text = "No other alternatives for this word"
        else:
            sa_dropdown.label = "Choose correct spelling"
            sa_dropdown.hint_text = "Pick alternative → updates Persian Output"

    def render_output():
        render_persian_output()
        render_suggested_alternatives()

    def apply_alternative_as_correct(alt_index: int):
        """Dropdown choice becomes the correct word in Persian Output."""
        if selected_slot_index is None or selected_slot_index >= len(word_slots):
            return
        slot = word_slots[selected_slot_index]
        alts = list(slot.get("alternatives") or [])
        if alt_index < 0 or alt_index >= len(alts):
            return

        chosen = alts[alt_index][0]
        # Put chosen first and select it
        slot["alternatives"] = [(chosen, 1.0)] + [a for a in alts if a[0] != chosen]
        slot["selected_idx"] = 0
        apply_user_correction(slot["token"], chosen)

        sync_output_from_slots()
        render_output()
        status_text.value = f"Persian Output updated: «{slot['token']}» → {chosen}"
        if settings.auto_copy_on_convert:
            pyperclip.copy(current_persian)
            status_text.value += "  ·  copied"
        page.update()

    def on_alt_dropdown_select(e):
        raw = getattr(e.control, "value", None)
        if raw is None:
            raw = getattr(e, "data", None)
        if raw is None:
            return
        try:
            apply_alternative_as_correct(int(raw))
        except (TypeError, ValueError):
            return

    def clear_word_selection():
        nonlocal selected_slot_index
        selected_slot_index = None
        render_output()
        status_text.value = "Selection cleared — click a word in Persian Output"
        page.update()

    def perform_conversion(text: str, from_user: bool = True):
        nonlocal current_persian, last_input_text, word_slots, selected_slot_index, draft_len, draft_input
        draft_len = 0
        draft_input = ""
        try:
            if not text or not text.strip():
                current_persian = ""
                word_slots = []
                selected_slot_index = None
                render_output()
                page.update()
                return

            last_input_text = text
            prev_token = None
            if selected_slot_index is not None and selected_slot_index < len(word_slots):
                prev_token = word_slots[selected_slot_index]["token"]

            word_slots = _build_word_slots(text, previous_slots=word_slots)
            sync_output_from_slots()

            if prev_token is not None and selected_slot_index is not None:
                if (
                    selected_slot_index >= len(word_slots)
                    or word_slots[selected_slot_index]["token"].lower() != prev_token.lower()
                ):
                    selected_slot_index = None

            render_output()

            if settings.auto_copy_on_convert:
                pyperclip.copy(current_persian)

            n_words = len(word_slots)
            status_text.value = (
                f"Converted ✓  ({n_words} words) — click a wrong word in Persian Output to fix it"
                if from_user
                else f"Converted ({n_words} words)"
            )
            page.update()
        except Exception as ex:
            _log_launch(f"perform_conversion error: {ex}")
            status_text.value = f"Conversion error: {ex}"
            try:
                current_persian = convert(text or "")
                persian_output_host.content = ft.Text(
                    current_persian or "(empty)",
                    size=22,
                    font_family=PERSIAN_FONT,
                    color=ft.Colors.BLUE_GREY_900,
                    text_align=ft.TextAlign.RIGHT,
                    rtl=True,
                    selectable=True,
                )
                n = len((text or "").split())
                persian_output_host.height = _estimate_persian_output_height(n)
            except Exception as ex2:
                persian_output_host.content = ft.Text(
                    f"(conversion failed: {ex2})",
                    size=16,
                    color=ft.Colors.RED_400,
                )
                persian_output_host.height = PERSIAN_OUTPUT_MIN_H
            page.update()

    def on_input_change(value: str):
        if not settings.live_conversion:
            return
        perform_conversion(value or "", from_user=True)

    def _show_live_persian(text: str, commit: bool, new_slots: Optional[List[Dict]] = None) -> bool:
        """Update Persian Output and Pinglish Input while the microphone stays open.

        Speech continues what is already there, typed or spoken: the Persian goes
        to the end of Persian Output and its Pinglish to the end of Pinglish Input.
        A commit keeps the phrase. A partial replaces only the unfinished tail.
        """
        nonlocal word_slots, selected_slot_index, draft_len, draft_input, last_input_text
        if new_slots is None:
            new_slots = _slots_from_dictation(text) if text and text.strip() else []
        lead = ""
        if new_slots and "lead_punct" in new_slots[0]:
            lead = new_slots[0]["lead_punct"]
            new_slots = new_slots[1:]
        if not new_slots and not lead:
            if commit:
                draft_len = 0
                draft_input = ""
            return False
        if draft_len:
            if selected_slot_index is not None and selected_slot_index >= len(word_slots) - draft_len:
                selected_slot_index = None
            word_slots = word_slots[:-draft_len]
            draft_len = 0
        base = input_field.value or ""
        if draft_input and base.endswith(draft_input):
            base = base[: -len(draft_input)]
        draft_input = ""
        # A mark said after a pause ends the previous word: "gerooneh?" and ؟.
        # Only on commit, so a partial cannot add it twice.
        if lead and commit:
            if word_slots:
                word_slots[-1]["punct"] = word_slots[-1]["punct"].rstrip() + lead
            if base.strip():
                base = base.rstrip() + lead
        if word_slots and new_slots and not word_slots[-1]["punct"][-1:].isspace():
            word_slots[-1]["punct"] += " "
        word_slots.extend(new_slots)
        addition = "".join(slot["token"] + slot["punct"] for slot in new_slots)
        sep = "" if not base or base[-1].isspace() or not addition else " "
        input_field.value = base + sep + addition
        last_input_text = input_field.value
        end = len(input_field.value)
        input_field.selection = ft.TextSelection(base_offset=end, extent_offset=end)
        if not commit:
            draft_len = len(new_slots)
            draft_input = sep + addition
        render_output()
        if commit and settings.auto_copy_on_convert and current_persian:
            pyperclip.copy(current_persian)
        return True

    def _set_mic_listening(listening: bool):
        mic_btn.icon = ft.Icons.STOP if listening else ft.Icons.MIC
        mic_btn.icon_color = ft.Colors.RED_700 if listening else C_PRIMARY
        mic_btn.bgcolor = ft.Colors.RED_50 if listening else C_PRIMARY_LIGHT
        mic_btn.tooltip = (
            "Stop listening. Esc also stops."
            if listening
            else "Speak Persian. The text appears as you talk. Esc stops."
        )

    def _bind_escape_stop(active: bool):
        """Esc stops the mic from any window, only while it is listening."""
        nonlocal _esc_stop_hotkey
        if _esc_stop_hotkey is not None:
            try:
                keyboard.remove_hotkey(_esc_stop_hotkey)
            except Exception:
                pass
            _esc_stop_hotkey = None
        if not active:
            return
        try:
            _esc_stop_hotkey = keyboard.add_hotkey(
                "esc",
                lambda: _on_ui(_stop_mic_from_key),
                suppress=False,
            )
        except Exception as ex:
            _log_launch(f"Escape stop shortcut failed: {ex}")

    def _on_ui(fn, *args):
        """Run fn on Flet's event loop thread.

        page.update() called from a plain thread queues the patch on an asyncio
        queue without waking the loop, so the window only redraws on the next
        mouse or keyboard event. run_task wakes the loop, and posts run in order.
        """

        async def _run():
            fn(*args)

        try:
            page.run_task(_run)
        except Exception as ex:  # loop already closed while quitting
            _log_launch(f"UI post failed: {ex}")

    def _stop_mic_from_key():
        if mic_listening:
            on_mic_click(None)

    def _finish_mic(error: Optional[str], wrote: bool, note: str = ""):
        nonlocal mic_listening, draft_len, draft_input
        with mic_ui:
            mic_listening = False
            draft_len = 0
            draft_input = ""
            _bind_escape_stop(False)
            _set_mic_listening(False)
            if error:
                status_text.value = error
            elif wrote:
                status_text.value = note or "Persian speech written into Persian Output"
            else:
                status_text.value = note or "No Persian speech recognized. Speak again, a little closer to the microphone."
            page.update()

    def on_mic_click(_):
        nonlocal mic_listening
        with mic_ui:
            _on_mic_click_locked()

    def _on_mic_click_locked():
        nonlocal mic_listening
        if mic_listening:
            mic_stop.set()
            status_text.value = "Stopping…"
            page.update()
            return
        if not speech_enabled():
            status_text.value = (
                "Speech recognition is turned off. To use the mic, run the Pinglish "
                "installer again and tick “Enable speech recognition”."
            )
            page.update()
            return
        mic_listening = True
        mic_stop.clear()
        _set_mic_listening(True)
        _bind_escape_stop(True)
        # "Listening on …" follows once the mic really sends sound (about a
        # second for a Bluetooth headset), so speech is not started too early.
        status_text.value = "Starting the microphone… speak when it says Listening."
        page.update()

        holder ={"error": None, "note": "", "wrote": False}

        # Every result is applied on the Flet loop (see _on_ui), so each partial
        # and phrase is drawn as soon as it arrives, in the order it was heard.
        def apply_live(kind: str, text: str, slots: Optional[List[Dict]] = None):
            if kind == "device":
                if mic_listening and not mic_stop.is_set():
                    status_text.value = f"Listening on {text}. Speak Persian. Esc stops."
                _log_launch(f"Microphone listening: {text}")
                page.update()
                return
            with mic_ui:
                changed = _show_live_persian(text, kind == "commit", slots)
                if changed and text.strip():
                    holder["wrote"] = True
                    if kind == "commit":
                        _log_launch(f"Microphone phrase words={len(text.split())}")
                if changed:
                    page.update()

        def finish():
            _finish_mic(holder["error"], holder["wrote"], holder["note"])

        def post(kind: str, text: str):
            # The Pinglish lookup runs here, off the UI thread.
            try:
                slots = _slots_from_dictation(text) if text and text.strip() else []
            except Exception as ex:
                _log_launch(f"Dictation Pinglish failed: {ex}")
                slots = None  # retried on the UI thread
            _on_ui(apply_live, kind, text, slots)

        def worker():
            try:
                holder["note"] = listen_persian(
                    mic_stop,
                    lambda text: post("partial", text),
                    lambda text: post("commit", text),
                    lambda name: _on_ui(apply_live, "device", name),
                ) or ""
            except SpeechError as ex:
                holder["error"] = str(ex)
                _log_launch(f"Microphone: {ex}")
            except Exception as ex:
                _log_launch(f"Microphone failed: {ex}")
                holder["error"] = "Microphone failed. Try again."
            finally:
                # Posted after every phrase, so the last words are drawn first.
                _on_ui(finish)

        threading.Thread(target=worker, name="finglish-mic-worker", daemon=True).start()

    # ---------------- Action Buttons ----------------
    def on_convert_click(_):
        perform_conversion(input_field.value or "", from_user=True)

    def on_copy_persian(_):
        if current_persian:
            pyperclip.copy(current_persian)
            status_text.value = "Persian text copied to clipboard"
            page.update()

    def on_copy_both(_):
        if last_input_text and current_persian:
            combined = f"{last_input_text}\n{current_persian}"
            pyperclip.copy(combined)
            status_text.value = "Both texts copied"
            page.update()

    def on_convert_clipboard(_):
        try:
            clip = pyperclip.paste()
            if clip and clip.strip():
                input_field.value = clip
                perform_conversion(clip, from_user=True)
                status_text.value = "Converted from clipboard"
            else:
                status_text.value = "Clipboard is empty"
            page.update()
        except Exception as e:
            status_text.value = f"Clipboard error: {e}"
            page.update()

    def on_clear(_):
        nonlocal word_slots, current_persian, selected_slot_index, draft_len, draft_input
        input_field.value = ""
        word_slots = []
        current_persian = ""
        selected_slot_index = None
        draft_len = 0
        draft_input = ""
        render_output()
        status_text.value = "Cleared"
        page.update()

    def on_quit_app(_):
        """Fully quit the app from the main window (stops tray icon too)."""
        shutdown_app()

    def on_paste_to_previous(_):
        """Best-effort: copy Persian to clipboard then try to paste into the previously active window."""
        if not current_persian:
            return
        try:
            pyperclip.copy(current_persian)
            # Give user a moment to have focused another window, or try to restore last one.
            # Simple heuristic: minimize our window briefly, then send Ctrl+V
            page.window.minimized = True
            page.update()
            time.sleep(0.35)           # allow user / OS to switch focus
            pyautogui.hotkey("ctrl", "v")
            status_text.value = "Sent Persian via clipboard + Ctrl+V (check target app)"
            # Restore after a bit
            time.sleep(0.6)
            page.window.minimized = False
            page.window.visible = True
            page.update()
        except Exception as ex:
            status_text.value = f"Paste simulation error: {ex}"
            page.window.minimized = False
            page.update()

    # ---------------- Hotkey ----------------
    hotkey_registered = False

    def register_hotkey():
        nonlocal hotkey_registered
        try:
            if hotkey_registered:
                try:
                    keyboard.remove_hotkey(settings.hotkey)
                except Exception:
                    pass
            keyboard.add_hotkey(
                settings.hotkey,
                lambda: page.run_thread(_focus_app_and_select_input),
                suppress=False,
            )
            hotkey_registered = True
            print(f"Global hotkey registered: {settings.hotkey}")
        except Exception as ex:
            print("Hotkey registration failed (may need admin rights or different combo):", ex)
            raise  # let caller decide how to surface it

    def _focus_app_and_select_input():
        # Called from keyboard thread (Strg+D). Works even when window was hidden via X.
        def action():
            try:
                _show_window_from_tray(page, "hotkey Strg+D")
            except Exception as ex:
                print("Focus action error (hotkey):", ex)
        page.run_thread(action)

    # ---------------- Layout ----------------
    def _section_label(icon, title: str, subtitle: str = ""):
        return ft.Row(
            [
                ft.Container(
                    content=ft.Icon(icon, size=16, color=ft.Colors.WHITE),
                    width=30,
                    height=30,
                    bgcolor=C_PRIMARY,
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text(title, size=12, weight=ft.FontWeight.W_700, color=C_PRIMARY_DARK),
                        ft.Text(subtitle, size=10, color=C_MUTED) if subtitle else ft.Container(),
                    ],
                    spacing=0,
                    tight=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _shortcut_chip(keys: str, action: str):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(keys, size=10, weight=ft.FontWeight.W_700, color=C_PRIMARY),
                    ft.Text(action, size=10, color=C_MUTED),
                ],
                spacing=6,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=10, right=10, top=5, bottom=5),
            bgcolor=C_PRIMARY_LIGHT,
            border_radius=20,
            border=ft.Border.all(1, ft.Colors.INDIGO_200),
            tooltip=f"{keys}: {action}",
        )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text("ف", size=20, font_family=PERSIAN_FONT, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700),
                            width=42,
                            height=42,
                            gradient=ft.LinearGradient(
                                begin=ft.Alignment(-1, -1),
                                end=ft.Alignment(1, 1),
                                colors=[C_PRIMARY, C_ACCENT],
                            ),
                            border_radius=12,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column(
                            [
                                ft.Text(APP_NAME, size=20, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_900),
                                ft.Text("Offline Pinglish → Persian", size=11, color=C_MUTED),
                            ],
                            spacing=0,
                            tight=True,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Container(expand=True),
                ft.Row(
                    [
                        _shortcut_chip("Strg + D", "Show"),
                        _shortcut_chip("Esc", "Stop mic"),
                        _shortcut_chip("Strg + Shift + Q", "Quit"),
                    ],
                    spacing=6,
                    wrap=True,
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(width=8),
                ft.Text(f"V{APP_VERSION}", size=10, color=C_MUTED),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(left=24, right=24, top=16, bottom=16),
        bgcolor=C_CARD,
        border=ft.Border(bottom=ft.BorderSide(1, C_BORDER)),
        shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
    )

    convert_btn = ft.FilledButton("Convert", icon=ft.Icons.AUTORENEW, on_click=on_convert_click, bgcolor=C_PRIMARY)
    copy_btn = ft.OutlinedButton("Copy", icon=ft.Icons.CONTENT_COPY, on_click=on_copy_persian)
    both_btn = ft.OutlinedButton("Both", icon=ft.Icons.COPY_ALL, on_click=on_copy_both)
    clip_btn = ft.OutlinedButton("Clipboard", icon=ft.Icons.CONTENT_PASTE_GO, on_click=on_convert_clipboard)
    paste_btn = ft.OutlinedButton("Paste back", icon=ft.Icons.SEND, on_click=on_paste_to_previous)
    clear_btn = ft.OutlinedButton("Clear", icon=ft.Icons.CLEAR, on_click=on_clear)
    quit_btn = ft.TextButton("Quit", icon=ft.Icons.POWER_SETTINGS_NEW, on_click=on_quit_app, style=ft.ButtonStyle(color=ft.Colors.RED_400))

    live_switch = ft.Switch(
        label="Live convert",
        value=settings.live_conversion,
        active_color=C_PRIMARY,
        on_change=lambda e: setattr(settings, "live_conversion", e.control.value) or settings.save(),
    )

    top_bar = ft.Container(
        content=ft.Row(
            [
                ft.Row([convert_btn, copy_btn, both_btn, clip_btn, paste_btn, clear_btn], spacing=8, wrap=True),
                ft.Container(expand=True),
                ft.Row([live_switch, quit_btn], spacing=8),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(left=20, right=20, top=10, bottom=10),
        bgcolor=ft.Colors.with_opacity(0.6, C_CARD),
        border=ft.Border(bottom=ft.BorderSide(1, C_BORDER)),
    )

    input_card = ft.Container(
        content=ft.Column(
            [
                _section_label(ft.Icons.KEYBOARD, "Pinglish Input", "Type or paste Latin-script Persian"),
                ft.Divider(height=1, color=C_BORDER),
                input_field,
            ],
            spacing=10,
            tight=True,
        ),
        bgcolor=C_CARD,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, C_BORDER),
        shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK), offset=ft.Offset(0, 3)),
    )

    # MIDDLE — Suggested Alternatives (idle until a Persian word is clicked)
    suggestions_card = ft.Container(
        content=ft.Column(
            [
                _section_label(
                    ft.Icons.SPELLCHECK,
                    "Suggested Alternatives",
                    "Appears only after you click a word in Persian Output — use the dropdown to fix it",
                ),
                ft.Divider(height=1, color=C_BORDER),
                sa_hint,
                sa_active_row,
            ],
            spacing=10,
            tight=True,
        ),
        bgcolor=C_CARD,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, C_BORDER),
        height=150,
        shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
    )

    # BOTTOM — Persian Output (grows with the sentence; not a fixed box)
    mic_btn = ft.IconButton(
        icon=ft.Icons.MIC,
        icon_color=C_PRIMARY,
        bgcolor=C_PRIMARY_LIGHT,
        icon_size=22,
        tooltip="Speak Persian. The text appears as you talk. Esc stops.",
        on_click=on_mic_click,
    )
    output_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        _section_label(
                            ft.Icons.TRANSLATE,
                            "Persian Output",
                            "Grows with your text — click any wrong word to load it into Suggested Alternatives above",
                        ),
                        ft.Container(expand=True),
                        mic_btn,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=1, color=C_BORDER),
                persian_output_host,
            ],
            spacing=10,
            tight=True,
        ),
        bgcolor=C_CARD,
        border_radius=16,
        padding=16,
        border=ft.Border.all(1, C_BORDER),
        shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK), offset=ft.Offset(0, 3)),
    )

    main_area = ft.Column(
        [
            input_card,
            suggestions_card,
            output_card,
        ],
        spacing=14,
        expand=True,
        tight=False,
    )

    status_bar = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.CIRCLE, size=8, color=C_ACCENT),
                    padding=ft.Padding(top=2),
                ),
                status_text,
                ft.Container(expand=True),
                ft.Text(
                    "Esc stop mic  ·  Strg+Shift+Q quit  ·  Strg+D show",
                    size=10,
                    color=ft.Colors.BLUE_GREY_400,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(left=20, right=20, top=8, bottom=8),
        bgcolor=C_CARD,
        border=ft.Border(top=ft.BorderSide(1, C_BORDER)),
    )

    page.add(
        header,
        top_bar,
        ft.Container(
            content=main_area,
            padding=ft.Padding(left=20, right=20, top=16, bottom=12),
            expand=True,
        ),
        status_bar,
    )
    print("DEBUG: UI elements added to page.")

    # ---------------- Boot sequence ----------------
    # Final force show in taskbar / visible (helps when launched via hidden VBS + pythonw)
    page.window.skip_task_bar = False
    page.window.minimized = False
    page.window.visible = True
    page.update()
    _log_launch("Window forced visible + skip_taskbar=False")
    print("DEBUG: Final window visibility forced. About to set up tray/hotkey.")

    # Register global hotkey (non-blocking) - best effort
    try:
        _log_launch("Registering global hotkey")
        register_hotkey()
        _log_launch("Hotkey registered successfully")
    except Exception as ex:
        _log_launch(f"Hotkey registration failed: {ex}")
        print("Warning: Could not register global hotkey:", ex)
        status_text.value = "Hotkey Registrierung fehlgeschlagen — App als Administrator starten oder anderes Tastenkürzel versuchen (aktuell: Strg + D)"
        page.update()

    _shutting_down = False

    def shutdown_app():
        """Gracefully stop tray/hotkey and destroy the Flet window so the process exits."""
        nonlocal _shutting_down
        if _shutting_down:
            return
        _shutting_down = True
        mic_stop.set()
        _log_launch("Shutting down application")

        try:
            # Hidden in the tray or minimized, the window reports a tiny size
            # (seen: 160 x 28). Only keep a size the window really had on screen.
            width = int(page.window.width or 0)
            height = int(page.window.height or 0)
            if width >= 1100 and height >= 860:
                settings.window_width = width
                settings.window_height = height
            settings.save()
        except Exception:
            pass

        try:
            keyboard.unhook_all()
        except Exception:
            pass

        if _tray_icon is not None:
            def stop_tray():
                try:
                    _tray_icon.stop()
                except Exception:
                    pass

            threading.Thread(target=stop_tray, daemon=True).start()

        async def destroy_window():
            try:
                await page.window.destroy()
            except Exception as ex:
                _log_launch(f"window.destroy failed: {ex}")
                os._exit(0)

        # Quit must always end the app. If the window does not close in time
        # (hidden, busy, or the client stopped answering), exit anyway; the
        # job object from _close_window_with_app then closes flet.exe too.
        def force_exit():
            _log_launch("Window did not close in time - exiting")
            os._exit(0)

        threading.Timer(4.0, force_exit).start()
        try:
            page.run_task(destroy_window)
        except Exception as ex:
            _log_launch(f"Could not ask the window to close: {ex}")
            os._exit(0)

    def on_keyboard(e: ft.KeyboardEvent):
        key = (e.key or "").lower()
        if e.ctrl and e.shift and not e.alt and key == "q":
            shutdown_app()
            return
        if mic_listening and key == "escape":
            _stop_mic_from_key()

    page.on_keyboard_event = on_keyboard

    try:
        keyboard.add_hotkey(
            "ctrl+shift+q",
            lambda: page.run_thread(shutdown_app),
            suppress=False,
        )
        _log_launch("Shortcuts ready: Esc stops mic, Strg+Shift+Q quits")
    except Exception as ex:
        _log_launch(f"Command hotkeys failed: {ex}")

    # Start tray icon in background thread - best effort
    def start_tray():
        try:
            _log_launch("Starting tray thread")
            run_tray(page, shutdown_app)
        except Exception as e:
            _log_launch(f"Tray failed: {e}")
            _show_error_box(f"Tray icon could not start: {e}")

    tray_thread = threading.Thread(target=start_tray, daemon=True)
    tray_thread.start()
    _log_launch("Tray thread started - app should now be visible")

    # Hide to tray on X (keep running). Flet 0.85 reports close via WindowEvent.type, not Event.data.
    def on_window_event(e):
        if e.type == ft.WindowEventType.CLOSE:
            print("DEBUG: window close event - hiding to tray")
            _hide_window_to_tray(page, "X close button")

    page.window.on_event = on_window_event

    # Opening Pinglish again while it runs brings this window back, like Strg+D.
    _listen_for_second_launch(
        lambda: page.run_thread(lambda: _show_window_from_tray(page, "second launch"))
    )

    _log_launch("on_close handler installed (X hides window to tray, keeps background)")

    status_text.value = (
        "Speak with the mic — Persian appears as you talk. "
        "Esc stops the mic. Strg+Shift+Q quits. Strg+D shows the window."
    )
    page.update()
    _schedule_native_window_icon()

    def _probe_mic():
        try:
            _log_launch(probe_microphone())
        except Exception as ex:
            _log_launch(f"Microphone probe failed: {ex}")

    if speech_enabled():
        threading.Thread(target=_probe_mic, daemon=True).start()
    print("DEBUG: main() setup complete. ft.run should now show the window. (If you don't see the GUI, an error likely happened after this or in a background thread.)")


# ----------------------------- Single instance -----------------------------
# Only one Pinglish runs per Windows session. A second launch (Start menu,
# desktop icon, autostart) asks the running one to show its window, then exits.
# Two copies would also fight over the Strg+D hotkey and the tray icon.
SINGLE_INSTANCE_MUTEX = "PinglishSingleInstance"
SHOW_WINDOW_EVENT = "PinglishShowWindow"
_instance_handles: Dict[str, int] = {}  # kept open for the life of this process


def _claim_single_instance() -> bool:
    """True when no other Pinglish is running. Otherwise wakes the running one."""
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.OpenEventW.restype = wintypes.HANDLE
        kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.SetEvent.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

        mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
        already_running = ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
        if not mutex:
            return True  # cannot tell; never block the app from starting
        if not already_running:
            _instance_handles["mutex"] = mutex
            # Auto-reset event: each SetEvent from a later launch wakes the listener once.
            event = kernel32.CreateEventW(None, False, False, SHOW_WINDOW_EVENT)
            if event:
                _instance_handles["event"] = event
            return True

        kernel32.CloseHandle(mutex)
        # This process was just started by the user, so it may hand the right
        # to come to the front to the running window (another process).
        try:
            ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
        except Exception:
            pass
        # The first copy creates the event right after its mutex; wait briefly
        # in case both were started at the same moment.
        for _ in range(25):
            event = kernel32.OpenEventW(0x0002, False, SHOW_WINDOW_EVENT)  # EVENT_MODIFY_STATE
            if event:
                kernel32.SetEvent(event)
                kernel32.CloseHandle(event)
                break
            time.sleep(0.2)
        return False
    except Exception as ex:
        _log_launch(f"Single-instance check failed: {ex}")
        return True


def _listen_for_second_launch(on_show) -> None:
    """Call on_show() each time another launch asks this Pinglish to appear."""
    event = _instance_handles.get("event")
    if not event:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

    def wait_loop():
        while True:
            if kernel32.WaitForSingleObject(event, 0xFFFFFFFF) != 0:  # INFINITE; 0 = signaled
                return
            try:
                on_show()
            except Exception as ex:
                _log_launch(f"Show on second launch failed: {ex}")

    threading.Thread(target=wait_loop, daemon=True, name="second-launch").start()


_APP_JOB = None  # keeps the job handle open for the life of this process


def _close_window_with_app() -> bool:
    """Make Windows close the Flet window whenever this Python process ends.

    The window is a separate program (flet.exe) and it ignores its own X
    button (prevent_close), so when Python crashed the window stayed on
    "Working..." and only Task Manager could end it. This process and its
    children go into a job that Windows ends as soon as the job's last handle,
    held only here, closes - on a normal exit or a crash.
    """
    global _APP_JOB
    try:
        from ctypes import wintypes

        class _IoCounters(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class _BasicLimits(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BasicLimits),
                ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return False
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            return False  # 9 = JobObjectExtendedLimitInformation
        if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
            return False
        _APP_JOB = job
        return True
    except Exception as ex:
        _log_launch(f"Window/process link not set: {ex}")
        return False


if __name__ == "__main__":
    # Run as a desktop Flet app (0.8x+ style).
    # ft.run(main, ...) is the current recommended way (main is positional).
    # Use absolute assets_dir for reliability when launched via VBS/pythonw.
    if not _claim_single_instance():
        _log_launch("Pinglish is already running - showed its window instead of starting again")
        sys.exit(0)
    try:
        assets_dir = str((RES_DIR / "assets").resolve())
        # Must be set before flet.exe starts. The client reads this and stops
        # using the shared Flet taskbar identity.
        os.environ["FLET_APP_USER_MODEL_ID"] = APP_USER_MODEL_ID
        # Before flet.exe starts, so the window joins this process's job.
        _log_launch(f"Window closes with the app: {_close_window_with_app()}")
        _log_launch(f"Packaged (MSIX): {PACKAGED_APP_ID or 'no'}")
        _log_launch("Starting ft.run with hidden launcher")
        ft.run(main, assets_dir=assets_dir)
    except Exception as e:
        _log_launch(f"FATAL: {type(e).__name__}: {e}")
        _show_error_box(f"Pinglish konnte nicht gestartet werden:\n\n{type(e).__name__}: {e}\n\n"
                        f"Log-Datei: data/finglish_launch.log\n\n"
                        "Tipp: Versuche run.bat für Fehlermeldungen im Konsolenfenster.")
        raise
