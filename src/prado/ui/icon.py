"""
Icon rendering and asset generator for PradoOS System Tray and Desktop App.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Tuple

from PIL import Image, ImageDraw


def create_tray_icon(
    state: str = "idle", size: int = 64, monochrome: bool = False
) -> Image.Image:
    """
    Renders a crisp, high-contrast system tray icon in memory.

    States:
    - 'idle': UGR Burgundy (#B20029) badge with white graduation mortarboard.
    - 'syncing': Vibrant Amber (#F59E0B) badge with white mortarboard.
    - 'error': Warning Red (#EF4444) badge with white exclamation symbol.

    When `monochrome=True` (recommended for macOS menu bar template images),
    renders an alpha-masked black silhouette on a transparent background so
    AppKit can automatically invert it for light/dark menu bars.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if monochrome:
        fg = (0, 0, 0, 255)
        cut = (0, 0, 0, 0)
        cx, cy = size // 2, size // 2 - max(1, size // 16)
        if state == "error":
            pad = max(2, size // 8)
            d.ellipse([pad, pad, size - pad, size - pad], fill=fg)
            w = max(2, size // 8)
            top = size // 4 + max(1, size // 16)
            h = size // 3 - max(1, size // 16)
            d.rounded_rectangle([cx - w // 2, top, cx + w // 2, top + h], radius=w // 2, fill=cut)
            dot_r = max(2, w // 2 + 1)
            dot_cy = top + h + size // 8
            d.ellipse([cx - dot_r, dot_cy - dot_r, cx + dot_r, dot_cy + dot_r], fill=cut)
            return img

        dw = int(size * 0.42)
        dh = max(3, int(size * 0.20))
        diamond = [(cx, cy - dh), (cx + dw, cy), (cx, cy + dh), (cx - dw, cy)]
        d.polygon(diamond, fill=fg)
        d.polygon(
            [(cx - int(dw * 0.56), cy + max(2, size // 24)), (cx + int(dw * 0.56), cy + max(2, size // 24)), (cx, cy + dh + max(3, size // 12))],
            fill=fg,
        )
        tassel_w = max(2, size // 20)
        d.line([(cx + dw - 2, cy), (cx + dw + 1, cy + dh + max(3, size // 10))], fill=fg, width=tassel_w)

        if state == "syncing":
            br = max(3, size // 7)
            bx, by = size - br - max(2, size // 16), size - br - max(2, size // 16)
            d.ellipse([bx - br - 2, by - br - 2, bx + br + 2, by + br + 2], fill=cut)
            d.ellipse([bx - br, by - br, bx + br, by + br], fill=fg)
        return img

    if state == "syncing":
        bg = (245, 158, 11, 255)  # Amber
        fg = (255, 255, 255, 255)
    elif state == "error":
        bg = (239, 68, 68, 255)  # Red
        fg = (255, 255, 255, 255)
    else:
        bg = (178, 0, 41, 255)  # UGR Official Burgundy
        fg = (255, 255, 255, 255)

    # Rounded rectangle badge
    pad = max(2, size // 16)
    radius = size // 4
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=bg)

    if state == "error":
        # Draw exclamation mark
        cx = size // 2
        w = max(2, size // 8)
        top = size // 4
        h = size // 3
        d.rounded_rectangle([cx - w // 2, top, cx + w // 2, top + h], radius=w // 2, fill=fg)
        dot_r = max(2, w // 2 + 1)
        dot_cy = top + h + size // 8
        d.ellipse([cx - dot_r, dot_cy - dot_r, cx + dot_r, dot_cy + dot_r], fill=fg)
    else:
        # Draw academic mortarboard (graduation cap)
        cx, cy = size // 2, size // 2 - max(1, size // 16)
        dw, dh = size // 3, size // 6
        diamond = [
            (cx, cy - dh),
            (cx + dw, cy),
            (cx, cy + dh),
            (cx - dw, cy),
        ]
        d.polygon(diamond, fill=fg)

        # Cap base / skullcap
        d.polygon(
            [
                (cx - dw // 2, cy + 2),
                (cx + dw // 2, cy + 2),
                (cx, cy + dh + max(2, size // 16)),
            ],
            fill=fg,
        )

        # Cap tassel
        tassel_w = max(1, size // 24)
        d.line(
            [(cx + dw - 2, cy), (cx + dw + 2, cy + dh + max(2, size // 16))],
            fill=fg,
            width=tassel_w,
        )

    return img


def generate_desktop_assets(output_dir: Path | str) -> dict[str, Path]:
    """
    Generates desktop icon assets:
    - icon.png (512x512)
    - icon.ico (multi-resolution for Windows: 16, 32, 48, 64, 128, 256)
    - icon.icns (Apple Icon format for macOS if iconutil is available)
    """
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    results: dict[str, Path] = {}

    # 1. High-resolution PNG (512x512)
    png_path = out / "icon.png"
    img_512 = create_tray_icon(state="idle", size=512)
    img_512.save(png_path, format="PNG")
    results["png"] = png_path

    # 2. Multi-resolution Windows ICO
    ico_path = out / "icon.ico"
    img_512.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    results["ico"] = ico_path

    # 3. macOS ICNS (if iconutil available)
    if sys.platform == "darwin" and shutil.which("iconutil"):
        iconset_dir = out / "icon.iconset"
        iconset_dir.mkdir(parents=True, exist_ok=True)
        sizes: list[Tuple[int, str]] = [
            (16, "icon_16x16.png"),
            (32, "icon_16x16@2x.png"),
            (32, "icon_32x32.png"),
            (64, "icon_32x32@2x.png"),
            (128, "icon_128x128.png"),
            (256, "icon_128x128@2x.png"),
            (256, "icon_256x256.png"),
            (512, "icon_256x256@2x.png"),
            (512, "icon_512x512.png"),
            (1024, "icon_512x512@2x.png"),
        ]
        for px, name in sizes:
            sz_img = create_tray_icon(state="idle", size=px)
            sz_img.save(iconset_dir / name, format="PNG")

        icns_path = out / "icon.icns"
        proc = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0 and icns_path.exists():
            results["icns"] = icns_path
        shutil.rmtree(iconset_dir, ignore_errors=True)

    return results
