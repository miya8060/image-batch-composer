# image-batch-composer

CSV または Web UI で指定した素材組み合わせから、商品画像をバッチ合成する小さなツール。
Pillow ベース、生成 AI は使わない。500〜3,000 件規模の合成バッチ用。

## 2 つの使い方

| モード | 想定ユーザー | コマンド |
|---|---|---|
| **Web UI** | エンジニアでない人 (クライアントも可) | `uv run streamlit run app.py` |
| **CLI** | 自分で大量データを回す場合 | `uv run python compose.py` |

## セットアップ (共通)

```fish
uv venv                                 # or: python -m venv .venv
uv pip install -r requirements.txt      # or: .venv/bin/pip install -r requirements.txt
```

---

## Web UI モード

```fish
uv run streamlit run app.py             # or: .venv/bin/streamlit run app.py
```

ブラウザで `http://localhost:8501` を開くと:

1. **素材アップロード**: 背景画像、商品画像、テキスト (改行区切り) をドラッグ&ドロップ
2. **レイアウト調整**: 商品位置・拡縮・テキスト位置・フォントサイズ・色をスライダーで設定
3. **プレビュー**: 1 件目の組み合わせをリアルタイム表示
4. **全件生成**: ボタン 1 つで全組み合わせを生成して ZIP ダウンロード

クライアントに URL を共有する形でも運用可能 (社内ネット or トンネリング)。

---

## CLI モード

```fish
uv run python scripts/make_samples.py    # ダミー素材を生成 (.venv 経由なら .venv/bin/python)
uv run python compose.py --limit 5       # 先頭 5 件だけプレビュー
uv run python compose.py                 # 全件処理 (デフォルト 4 並列)
```

### 入力ファイル配置

| パス | 説明 |
|---|---|
| `input/jobs.csv` | 1 行 = 1 枚の合成指示 |
| `input/backgrounds/` | 背景画像 (PNG/JPG) |
| `input/products/` | 商品画像 (透過 PNG 推奨) |
| `input/fonts/` | フォント。空ならシステム (macOS) を参照 |

### CSV カラム

| カラム | 型 | 説明 |
|---|---|---|
| `id` | str | 出力ファイル名 (拡張子なし) |
| `background` | str | `input/backgrounds/` 配下のファイル名 |
| `product` | str | `input/products/` 配下のファイル名 |
| `product_x` / `product_y` | int | 商品の貼り付け位置 (左上基準) |
| `product_scale` | float | 商品の拡縮率 (1.0 で原寸) |
| `text` | str | 描画文字列 (空文字なら描画スキップ) |
| `text_x` / `text_y` | int | テキストの描画位置 (左上基準) |
| `font` | str | フォントファイル名 (システムフォントは NFC でも NFD でも可) |
| `font_size` | int | フォントサイズ (px) |
| `color` | str | テキスト色 (`#rrggbb`) |

### 出力

`output/{id}.png` として PNG 保存。`output/` は gitignore。

### 並列化

`--workers N` で並列数を指定 (デフォルト 4)。
3,000 件 × 1 秒換算 → 4 並列で 12〜15 分目安。

---

## アーキテクチャ

```
core.py       … 画像合成のコアロジック (CLI と Web UI で共有)
compose.py    … CLI エントリポイント (CSV → output/ ディレクトリ)
app.py        … Web UI エントリポイント (Streamlit, アップロード → ZIP)
scripts/      … サンプル素材生成スクリプト
```

`core.compose()` は `PIL.Image` オブジェクトを受け取って返す純関数なので、CLI からも
Web UI からもファイルパス/BytesIO 経由で同じ実装を共有できる。

## 制限

- 影・グラデーション・回転は未対応 (要件が固まったら追加)。
- 出力フォーマットは PNG 固定 (JPG が必要なら `core.compose` の save 部分を分岐)。
- フォントは TrueType / TrueType Collection (.ttc) のみ動作確認。
- Web UI モードでは生成画像を一旦メモリに保持するため、3,000 枚を超えるとブラウザが重くなる可能性がある (CLI 推奨)。

## 背景

商品画像 × テキストパターンの組み合わせを大量に量産する業務向けに、生成 AI を使わず
Pillow で安定した結果を返すことを目的とした小さなツール。
