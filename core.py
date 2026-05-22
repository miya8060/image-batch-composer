"""画像合成のコアロジック。CLI (compose.py) と Web UI (app.py) の両方から再利用する。"""
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

# 解凍爆弾対策: 約 5,000 万 px (例: 7000x7000 相当) を超える画像は Pillow が
# DecompressionBombError を投げる。Web 公開時の DoS ベクター封じ。
Image.MAX_IMAGE_PIXELS = 50_000_000

SYSTEM_FONT_DIRS: list[Path] = [
    Path("/System/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
    Path.home() / "Library" / "Fonts",
]


def resolve_font(name: str, extra_dirs: Iterable[Path] = ()) -> Path:
    """フォントを extra_dirs → システムフォント の順で解決。

    macOS のシステムフォントは NFD で保存されているため、NFC 表記でもマッチするように
    正規化して比較する。
    """
    if not name:
        raise ValueError("font name is empty")

    for d in extra_dirs:
        candidate = Path(d) / name
        if candidate.exists():
            return candidate

    target = unicodedata.normalize("NFC", name)
    for d in SYSTEM_FONT_DIRS:
        if not d.exists():
            continue
        for p in d.iterdir():
            if unicodedata.normalize("NFC", p.name) == target:
                return p
    raise FileNotFoundError(f"font not found: {name}")


def list_system_fonts(extensions: tuple[str, ...] = (".ttf", ".otf", ".ttc")) -> list[str]:
    """システムフォント (NFC 正規化済みファイル名) を一覧で返す。"""
    seen: set[str] = set()
    for d in SYSTEM_FONT_DIRS:
        if not d.exists():
            continue
        for p in d.iterdir():
            if p.suffix.lower() in extensions:
                seen.add(unicodedata.normalize("NFC", p.name))
    return sorted(seen)


def compose(
    *,
    background: Image.Image,
    product: Image.Image,
    product_x: int,
    product_y: int,
    product_scale: float = 1.0,
    text: str = "",
    text_x: int = 0,
    text_y: int = 0,
    font_path: str | Path | None = None,
    font_size: int = 0,
    color: str = "#000000",
) -> Image.Image:
    """1 枚合成して RGB の PIL Image を返す。"""
    canvas = background.convert("RGBA").copy()
    product = product.convert("RGBA")

    if product_scale != 1.0:
        w, h = product.size
        product = product.resize(
            (max(1, int(w * product_scale)), max(1, int(h * product_scale))),
            Image.LANCZOS,
        )
    canvas.alpha_composite(product, (product_x, product_y))

    if text and font_path and font_size > 0:
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype(str(font_path), font_size)
        draw.text((text_x, text_y), text, font=font, fill=color)

    return canvas.convert("RGB")
