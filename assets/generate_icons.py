"""
Generate high-quality Finglish app icons (PNG + multi-size ICO).

Windows desktop shortcuts use icon.ico — rendered per-size from a 1024px master
so each resolution stays crisp (16px through 256px).

Run from project root:
    .venv\\Scripts\\python.exe assets\\generate_icons.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS_DIR = Path(__file__).parent.resolve()
MASTER_SIZE = 1024
TRAY_SIZE = 256
# Windows picks the closest embedded size for desktop / taskbar / Explorer.
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def _find_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "C:/Windows/Fonts/tahomabd.ttf",
                "C:/Windows/Fonts/segoeuib.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
            ]
        )
    candidates.extend(
        [
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )


def _squircle_mask(size: int, corner_ratio: float = 0.19) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    margin = max(1, size // 64)
    radius = max(2, int(size * corner_ratio))
    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=radius,
        fill=255,
    )
    return mask


def _paint_background(size: int) -> Image.Image:
    """Premium squircle gradient — fills the whole icon like modern Windows apps."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()

    top_left = (96, 165, 250)     # blue-400
    center = (37, 99, 235)        # blue-600
    bottom = (30, 58, 138)        # blue-900
    accent = (56, 189, 248)       # sky-400

    for y in range(size):
        ny = y / max(size - 1, 1)
        for x in range(size):
            nx = x / max(size - 1, 1)

            vertical = _lerp_color(top_left, bottom, ny**0.9)
            color = _lerp_color(vertical, center, (1.0 - abs(ny - 0.42) * 1.4) * 0.35)

            # Soft diagonal light from upper-left
            light = max(0.0, 1.0 - (nx * 0.55 + ny * 0.45))
            color = _lerp_color(color, accent, light * 0.22)

            # Gentle depth toward lower-right
            shade = 1.0 - (nx * 0.12 + ny * 0.18)
            color = tuple(max(0, min(255, int(c * shade))) for c in color)

            pixels[x, y] = (*color, 255)

    mask = _squircle_mask(size)
    img.putalpha(mask)
    return img


def _add_depth(img: Image.Image, rich: bool) -> Image.Image:
    size = img.width
    if not rich:
        return img

    # Inner top highlight
    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shine)
    inset = int(size * 0.08)
    draw.rounded_rectangle(
        [inset, inset, size - inset, int(size * 0.46)],
        radius=int(size * 0.14),
        fill=(255, 255, 255, 58),
    )
    shine = shine.filter(ImageFilter.GaussianBlur(radius=max(2, size * 0.028)))
    img = Image.alpha_composite(img, shine)

    # Subtle bottom shade
    shade = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shade)
    draw.rounded_rectangle(
        [inset, int(size * 0.55), size - inset, size - inset],
        radius=int(size * 0.14),
        fill=(15, 23, 42, 48),
    )
    shade = shade.filter(ImageFilter.GaussianBlur(radius=max(2, size * 0.03)))
    img = Image.alpha_composite(img, shade)

    # Soft outer shadow on transparent canvas
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    alpha = img.split()[3]
    shadow.paste((8, 15, 35, 95), (0, max(1, int(size * 0.025))), mask=alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(1, size * 0.022)))
    canvas = Image.alpha_composite(canvas, shadow)
    return Image.alpha_composite(canvas, img)


def _draw_glyph(img: Image.Image) -> Image.Image:
    size = img.width
    rich = size >= 40
    draw = ImageDraw.Draw(img)

    persian = "ف"
    scale = 0.50 if size >= 48 else 0.58
    font_size = max(8, int(size * scale))
    font = _find_font(font_size, bold=True)

    bbox = draw.textbbox((0, 0), persian, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]

    if rich:
        # Emboss: dark offset + soft glow
        emboss = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ed = ImageDraw.Draw(emboss)
        offset = max(1, size // 128)
        ed.text((tx + offset, ty + offset), persian, font=font, fill=(15, 23, 42, 120))
        emboss = emboss.filter(ImageFilter.GaussianBlur(radius=max(1, size * 0.01)))
        img = Image.alpha_composite(img, emboss)

        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.text((tx, ty), persian, font=font, fill=(255, 255, 255, 150))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=max(1, size * 0.012)))
        img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)
    draw.text((tx, ty), persian, font=font, fill=(255, 255, 255, 255))

    if rich and size >= 96:
        # Thin inner rim for polish on large sizes
        inset = int(size * 0.09)
        rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rim)
        rd.rounded_rectangle(
            [inset, inset, size - inset, size - inset],
            radius=int(size * 0.15),
            outline=(255, 255, 255, 38),
            width=max(1, size // 256),
        )
        img = Image.alpha_composite(img, rim)

    return img


def render_icon(size: int) -> Image.Image:
    rich = size >= 40
    icon = _paint_background(size)
    icon = _add_depth(icon, rich=rich)
    icon = _draw_glyph(icon)
    return icon


def _downscale(master: Image.Image, size: int) -> Image.Image:
    if size == master.width:
        return master.copy()
    return master.resize((size, size), Image.Resampling.LANCZOS)


def render_master() -> Image.Image:
    return render_icon(MASTER_SIZE)


def save_png(path: Path, size: int, master: Image.Image | None = None) -> None:
    if master is not None and size != MASTER_SIZE:
        _downscale(master, size).save(path, format="PNG", optimize=True)
    else:
        (master or render_icon(size)).save(path, format="PNG", optimize=True)


def save_ico(path: Path, master: Image.Image) -> None:
    """Embed every Windows-friendly size; 256px PNG-compressed for crisp desktop icons."""
    images = [_downscale(master, s).convert("RGBA") for s in ICO_SIZES]
    # Pillow embeds all frames when the largest image is saved first.
    images[-1].save(
        path,
        format="ICO",
        sizes=[(img.width, img.height) for img in images],
        append_images=images[:-1],
    )


def _verify_ico(path: Path) -> list[tuple[int, int]]:
    """Best-effort check of embedded ICO dimensions."""
    try:
        with Image.open(path) as img:
            sizes: list[tuple[int, int]] = []
            for i in range(getattr(img, "n_frames", 1)):
                img.seek(i)
                sizes.append(img.size)
            return sizes
    except Exception:
        return []


def main() -> None:
    print("Rendering master icon...")
    master = render_master()

    save_png(ASSETS_DIR / "icon.png", MASTER_SIZE, master)
    save_png(ASSETS_DIR / "icon_tray.png", TRAY_SIZE, master)
    save_ico(ASSETS_DIR / "icon.ico", master)

    embedded = _verify_ico(ASSETS_DIR / "icon.ico")
    print(f"Generated icons in {ASSETS_DIR}")
    for name in ("icon.png", "icon_tray.png", "icon.ico"):
        p = ASSETS_DIR / name
        print(f"  {name}: {p.stat().st_size // 1024} KB")
    if embedded:
        print(f"  icon.ico sizes: {embedded}")


if __name__ == "__main__":
    main()