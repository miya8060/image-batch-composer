"""サンプル素材を生成する (背景 3 枚 + 商品 3 枚)。

クライアントから素材が来る前に動作確認するためのダミー素材。
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BG_DIR = ROOT / "input" / "backgrounds"
PRODUCT_DIR = ROOT / "input" / "products"

CANVAS = (1200, 1200)
PRODUCT_SIZE = (400, 400)

BACKGROUNDS: dict[str, tuple[int, int, int]] = {
    "bg_white.png": (250, 250, 250),
    "bg_pink.png": (255, 220, 230),
    "bg_navy.png": (30, 50, 90),
}


def make_backgrounds() -> None:
    BG_DIR.mkdir(parents=True, exist_ok=True)
    for name, color in BACKGROUNDS.items():
        Image.new("RGB", CANVAS, color).save(BG_DIR / name)


def make_products() -> None:
    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", PRODUCT_SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((20, 20, 380, 380), fill=(220, 80, 80, 255))
    img.save(PRODUCT_DIR / "item_circle.png")

    img = Image.new("RGBA", PRODUCT_SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(img).rectangle((40, 40, 360, 360), fill=(80, 140, 220, 255))
    img.save(PRODUCT_DIR / "item_square.png")

    img = Image.new("RGBA", PRODUCT_SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon(
        [
            (200, 20), (244, 156), (388, 156), (272, 240),
            (316, 380), (200, 296), (84, 380), (128, 240),
            (12, 156), (156, 156),
        ],
        fill=(240, 200, 50, 255),
    )
    img.save(PRODUCT_DIR / "item_star.png")


if __name__ == "__main__":
    make_backgrounds()
    make_products()
    print(f"backgrounds -> {BG_DIR}")
    print(f"products    -> {PRODUCT_DIR}")
