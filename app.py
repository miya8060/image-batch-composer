"""Web UI for image-batch-composer.

起動方法:
    uv run streamlit run app.py
"""
from __future__ import annotations

import itertools
import zipfile
from io import BytesIO

import streamlit as st
from PIL import Image

from core import compose, list_system_fonts, resolve_font

st.set_page_config(page_title="画像合成バッチツール", page_icon="🖼️", layout="wide")

st.title("🖼️ 画像合成バッチツール")
st.caption(
    "背景・商品・テキストの **すべての組み合わせ** を一括生成します。"
    " アップロード → 配置調整 & プレビュー → ZIP ダウンロード、の 3 ステップ。"
)

# Responsive: 全画面サイズで プレビュー画像を「列幅 100%」かつ「ビューポート高さ 70%」以内に
# 抑え、どんなサイズでも崩れない。iPhone (<768px) のみ縦並び + プレビュー先頭にする。
# :has(.preview-marker) で「セクション 2 のプレビュー行」のみスコープし、アップロード 3 列・
# ZIP 1:2 列・controls_col 内のネスト 2 列には副作用なし。
# Streamlit の data-testid (stColumn / stImage / stImageContainer / stHorizontalBlock) は
# 1.32+ で安定だが上位バージョンで変わる可能性あり (要モニタ)。
st.markdown(
    """
    <style>
    /* 全画面共通: 親 stImage / stImageContainer に inline 固定 px が付くので親ごとフィットさせる */
    [data-testid="stHorizontalBlock"]:has(.preview-marker) [data-testid="stImage"],
    [data-testid="stHorizontalBlock"]:has(.preview-marker) [data-testid="stImageContainer"] {
        max-width: 100% !important;
    }
    [data-testid="stHorizontalBlock"]:has(.preview-marker) [data-testid="stImage"] img {
        max-width: 100% !important;
        max-height: 70vh !important;
        height: auto !important;
        object-fit: contain;
    }
    @media (max-width: 767px) {
        [data-testid="stHorizontalBlock"]:has(.preview-marker) {
            flex-direction: column;
        }
        [data-testid="stHorizontalBlock"]:has(.preview-marker) > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
        [data-testid="stColumn"]:has(.preview-marker) {
            order: -1;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def open_uploaded(uploaded_file) -> Image.Image:
    return Image.open(BytesIO(uploaded_file.getvalue()))


# -----------------------------------------------------------------------------
# 1. 素材アップロード
# -----------------------------------------------------------------------------
st.header("1. 素材をアップロード")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🌄 背景画像")
    bg_files = st.file_uploader(
        "複数選択可 (1 枚以上)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="bg",
    )

with col2:
    st.subheader("📦 商品画像")
    product_files = st.file_uploader(
        "複数選択可 (透過 PNG 推奨)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="prod",
    )

with col3:
    st.subheader("🔤 テキスト")
    text_input = st.text_area(
        "1 行 = 1 パターン (空行 = テキストなし)",
        value="新商品入荷\nSALE 30%OFF\n",
        height=200,
        help="例: 「新商品入荷」「SALE 30%OFF」「(空行)」と書くと、テキスト 3 パターン (空行含む) で展開されます。",
    )

texts = text_input.splitlines() if text_input else [""]
if not texts:
    texts = [""]

# -----------------------------------------------------------------------------
# 2. レイアウト調整 & プレビュー
# -----------------------------------------------------------------------------
st.header("2. レイアウト調整 & プレビュー")

# スライダー操作と同じビューポート内でプレビューを見せて即時フィードバックを得るため横並び。
controls_col, preview_col = st.columns([1, 1])

with controls_col:
    sub_a, sub_b = st.columns(2)
    with sub_a:
        st.subheader("📦 商品の配置")
        product_x = st.slider("商品 X 座標 (左からの距離 px)", 0, 2000, 400, step=10)
        product_y = st.slider("商品 Y 座標 (上からの距離 px)", 0, 2000, 500, step=10)
        product_scale = st.slider("商品の拡縮率", 0.1, 3.0, 1.0, step=0.05)

    with sub_b:
        st.subheader("🔤 テキストの配置")
        text_x = st.slider("テキスト X 座標 (左からの距離 px)", 0, 2000, 80, step=10)
        text_y = st.slider("テキスト Y 座標 (上からの距離 px)", 0, 2000, 80, step=10)
        font_size = st.slider("フォントサイズ (px)", 20, 400, 110, step=2)
        color = st.color_picker("テキスト色", "#222222")

        all_fonts = list_system_fonts()
        jp_fonts = [f for f in all_fonts if "ヒラギノ" in f or "Hiragino" in f or "NotoSansCJK" in f]
        other_fonts = [f for f in all_fonts if f not in jp_fonts]
        font_options = jp_fonts + other_fonts
        default_font = "ヒラギノ角ゴシック W6.ttc"
        default_idx = font_options.index(default_font) if default_font in font_options else 0
        font_name = st.selectbox("フォント (システム)", font_options, index=default_idx)

with preview_col:
    # マーカー: 上部 CSS の :has() スコープ用 (このカラムだけにレスポンシブを効かせる)
    st.markdown('<div class="preview-marker"></div>', unsafe_allow_html=True)
    st.subheader("👀 プレビュー (1 件目の組み合わせ)")
    if bg_files and product_files:
        try:
            font_path = resolve_font(font_name) if font_name else None
            preview = compose(
                background=open_uploaded(bg_files[0]),
                product=open_uploaded(product_files[0]),
                product_x=product_x,
                product_y=product_y,
                product_scale=product_scale,
                text=texts[0] if texts else "",
                text_x=text_x,
                text_y=text_y,
                font_path=font_path,
                font_size=font_size,
                color=color,
            )
            # サイズ制御は上部 CSS (max-width: 100%, max-height: 70vh) に委譲。
            st.image(
                preview,
                caption=(
                    f"背景: {bg_files[0].name} / "
                    f"商品: {product_files[0].name} / "
                    f"テキスト: {texts[0]!r}"
                ),
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"プレビュー生成エラー: {type(e).__name__}: {e}")
    else:
        st.info("背景画像と商品画像をアップロードするとプレビューが表示されます。")

# -----------------------------------------------------------------------------
# 3. 全件生成
# -----------------------------------------------------------------------------
st.header("3. 全件生成して ZIP ダウンロード")

total = (
    len(bg_files) * len(product_files) * len(texts)
    if (bg_files and product_files and texts)
    else 0
)

c1, c2 = st.columns([1, 2])
with c1:
    st.metric("生成枚数", f"{total} 枚")
with c2:
    st.write(
        f"内訳: 背景 **{len(bg_files) if bg_files else 0}** × "
        f"商品 **{len(product_files) if product_files else 0}** × "
        f"テキスト **{len(texts)}**"
    )

if total > 3000:
    st.warning(f"生成枚数が 3,000 を超えています ({total} 枚)。ブラウザが重くなる可能性があります。")

if st.button(
    "🚀 全件生成して ZIP でダウンロード",
    disabled=(total == 0),
    type="primary",
    use_container_width=True,
):
    progress = st.progress(0.0, text="準備中...")
    font_path = resolve_font(font_name) if font_name else None
    zip_buffer = BytesIO()
    errors: list[tuple[int, str]] = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_STORED) as zf:
        combos = list(itertools.product(bg_files, product_files, texts))
        for i, (bg, prod, txt) in enumerate(combos, start=1):
            try:
                img = compose(
                    background=open_uploaded(bg),
                    product=open_uploaded(prod),
                    product_x=product_x,
                    product_y=product_y,
                    product_scale=product_scale,
                    text=txt,
                    text_x=text_x,
                    text_y=text_y,
                    font_path=font_path,
                    font_size=font_size,
                    color=color,
                )
                buf = BytesIO()
                img.save(buf, "PNG")
                zf.writestr(f"{i:04d}.png", buf.getvalue())
            except Exception as e:
                errors.append((i, f"{type(e).__name__}: {e}"))
            progress.progress(i / total, text=f"{i}/{total} 生成中...")

    progress.empty()
    if errors:
        st.error(f"{len(errors)}/{total} 件失敗しました。最初の 10 件を表示します:")
        for idx, msg in errors[:10]:
            st.text(f"  {idx:04d}: {msg}")
    if len(errors) < total:
        st.success(f"{total - len(errors)} 枚の生成が完了しました。下のボタンからダウンロードできます。")
        st.download_button(
            "📥 ZIP をダウンロード",
            data=zip_buffer.getvalue(),
            file_name=f"composed_{total}.zip",
            mime="application/zip",
            use_container_width=True,
        )
