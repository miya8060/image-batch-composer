"""CSV-driven batch image composer (CLI).

Usage:
    uv run python compose.py                 # input/jobs.csv 全件を 4 並列で処理
    uv run python compose.py --limit 5       # 先頭 5 件だけプレビュー
    uv run python compose.py --workers 8     # 並列数を変更
    uv run python compose.py --csv path.csv  # 別 CSV を指定

Web UI を使う場合は `uv run streamlit run app.py` を実行する。
"""
from __future__ import annotations

import argparse
import csv
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from tqdm import tqdm

from core import compose, resolve_font

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"


@dataclass(frozen=True)
class Job:
    id: str
    background: str
    product: str
    product_x: int
    product_y: int
    product_scale: float
    text: str
    text_x: int
    text_y: int
    font: str
    font_size: int
    color: str

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Job":
        return cls(
            id=row["id"].strip(),
            background=row["background"].strip(),
            product=row["product"].strip(),
            product_x=int(row["product_x"]),
            product_y=int(row["product_y"]),
            product_scale=float(row["product_scale"]),
            text=row.get("text", "").strip(),
            text_x=int(row["text_x"]) if row.get("text_x") else 0,
            text_y=int(row["text_y"]) if row.get("text_y") else 0,
            font=row.get("font", "").strip(),
            font_size=int(row["font_size"]) if row.get("font_size") else 0,
            color=row.get("color", "#000000").strip(),
        )


def compose_one(job: Job) -> tuple[str, str | None]:
    """1 件合成。成功なら (id, None)、失敗なら (id, error message)。"""
    try:
        bg = Image.open(INPUT_DIR / "backgrounds" / job.background)
        product = Image.open(INPUT_DIR / "products" / job.product)
        font_path = resolve_font(job.font, extra_dirs=[INPUT_DIR / "fonts"]) if job.font else None

        result = compose(
            background=bg,
            product=product,
            product_x=job.product_x,
            product_y=job.product_y,
            product_scale=job.product_scale,
            text=job.text,
            text_x=job.text_x,
            text_y=job.text_y,
            font_path=font_path,
            font_size=job.font_size,
            color=job.color,
        )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        result.save(OUTPUT_DIR / f"{job.id}.png", "PNG")
        return job.id, None
    except Exception as exc:
        return job.id, f"{type(exc).__name__}: {exc}"


def load_jobs(csv_path: Path) -> list[Job]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return [Job.from_row(row) for row in csv.DictReader(f)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--csv", default=INPUT_DIR / "jobs.csv", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None, help="先頭 N 件のみ処理 (プレビュー用)")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"[ERROR] CSV not found: {args.csv}", file=sys.stderr)
        return 2

    jobs = load_jobs(args.csv)
    if args.limit:
        jobs = jobs[: args.limit]
    if not jobs:
        print("[WARN] no jobs to process", file=sys.stderr)
        return 0

    errors: list[tuple[str, str]] = []
    if args.workers <= 1:
        for job in tqdm(jobs, desc="compose"):
            job_id, err = compose_one(job)
            if err:
                errors.append((job_id, err))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(compose_one, job) for job in jobs]
            for fut in tqdm(as_completed(futures), total=len(futures), desc="compose"):
                job_id, err = fut.result()
                if err:
                    errors.append((job_id, err))

    if errors:
        print(f"\n[ERROR] {len(errors)}/{len(jobs)} jobs failed:", file=sys.stderr)
        for job_id, err in errors[:20]:
            print(f"  {job_id}: {err}", file=sys.stderr)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more", file=sys.stderr)
        return 1

    print(f"\n[OK] {len(jobs)} jobs composed -> {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
