# PyInstaller recipe for Pinglish.exe (one folder, no console).
# Build from the project root:  .\installer\build.ps1
# The Flet window program (flet.exe) is bundled so the installed app never
# downloads anything at start-up; main.py points FLET_VIEW_PATH at it.

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent
APP_VERSION = os.environ.get("PINGLISH_VERSION", "1.04")

import flet_desktop  # noqa: E402  (provides the cached Flet client)

flet_client = Path(flet_desktop.ensure_client_cached()) / "flet"
if not (flet_client / "flet.exe").is_file():
    raise SystemExit(f"flet.exe not found in {flet_client}")

datas = [
    (str(ROOT / "assets" / "icon.ico"), "assets"),
    (str(ROOT / "assets" / "icon.png"), "assets"),
    (str(ROOT / "assets" / "icon_tray.png"), "assets"),
    (str(ROOT / "assets" / "fonts"), "assets/fonts"),
    (str(ROOT / "data" / "community_dict.txt"), "data"),
    (str(ROOT / "data" / "community_dict_meta.json"), "data"),
    (str(flet_client), "flet_client/flet"),
]
datas += collect_data_files("finglish")
datas += collect_data_files("flet")

version_file = ROOT / "build" / "version_info.txt"
version_file.parent.mkdir(exist_ok=True)
parts = (APP_VERSION.split(".") + ["0", "0", "0"])[:4]
nums = ", ".join(str(int(p)) for p in parts)
version_file.write_text(
    f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({nums}), prodvers=({nums})),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'Pinglish'),
    StringStruct('FileDescription', 'Pinglish'),
    StringStruct('FileVersion', '{APP_VERSION}'),
    StringStruct('InternalName', 'Pinglish'),
    StringStruct('OriginalFilename', 'Pinglish.exe'),
    StringStruct('ProductName', 'Pinglish'),
    StringStruct('ProductVersion', '{APP_VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
""",
    encoding="utf-8",
)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=collect_submodules("flet_desktop") + ["pystray._win32"],
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide6", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Pinglish",
    icon=str(ROOT / "assets" / "icon.ico"),
    version=str(version_file),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Pinglish", upx=False)
