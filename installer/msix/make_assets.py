"""Draw the MSIX tile and Store images from assets/icon.png.

Usage: python make_assets.py <output Assets folder>

Windows picks the size it needs through resources.pri (built by
build_msix.ps1), so each image comes in several scales. The "unplated"
target sizes are the plain icon Windows shows on the taskbar and in the
Start list without a colored square behind it.
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "icon.png"


def _icon(size: int) -> Image.Image:
    return Image.open(SOURCE).convert("RGBA").resize((size, size), Image.LANCZOS)


def _on_canvas(width: int, height: int, icon_size: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    icon = _icon(icon_size)
    canvas.paste(icon, ((width - icon_size) // 2, (height - icon_size) // 2), icon)
    return canvas


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for scale in (100, 125, 150, 200, 400):
        f = scale / 100
        # Small app icon: Start list, taskbar, title bar.
        _on_canvas(round(44 * f), round(44 * f), round(44 * f * 0.9)).save(
            out / f"Square44x44Logo.scale-{scale}.png")
        # Medium tile.
        _on_canvas(round(150 * f), round(150 * f), round(150 * f * 0.66)).save(
            out / f"Square150x150Logo.scale-{scale}.png")
        # Wide tile.
        _on_canvas(round(310 * f), round(150 * f), round(150 * f * 0.66)).save(
            out / f"Wide310x150Logo.scale-{scale}.png")
        # Store listing / installer logo.
        _on_canvas(round(50 * f), round(50 * f), round(50 * f)).save(
            out / f"StoreLogo.scale-{scale}.png")
    for size in (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256):
        icon = _icon(size)
        icon.save(out / f"Square44x44Logo.targetsize-{size}.png")
        icon.save(out / f"Square44x44Logo.targetsize-{size}_altform-unplated.png")
        icon.save(out / f"Square44x44Logo.targetsize-{size}_altform-lightunplated.png")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]))
