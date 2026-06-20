"""
download_assets.py
───────────────────
Git에는 포함되지 않은 대용량 자산(CLIP 가중치 · FAISS 인덱스/메타데이터 ·
위성 타일 이미지)을 Google Drive에서 내려받아 프로젝트 구조에 맞게 배치합니다.

사용법:
    python download_assets.py            # 누락된 자산만 다운로드
    python download_assets.py --force    # 모든 자산을 강제로 다시 다운로드
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import gdown

PROJECT_ROOT = Path(__file__).resolve().parent

ASSETS: list[dict] = [
    {
        "name": "best_model",
        "drive_id": "1ljguAujYXpt6WrBS7k2QUoDGJKyZKbFn",
        "dest_dir": "checkpoints/best_model",
        "check": "checkpoints/best_model/model.safetensors",
    },
    {
        "name": "search_target_DB",
        "drive_id": "1d8gNc_Q5D394aXAOVu4avDARH8LyH4BW",
        "dest_dir": "data/processed/search_target_DB",
        "check": "data/processed/search_target_DB/faiss_jayangdong.index",
    },
    {
        "name": "raw_tiles_seongdong",
        "drive_id": "1958GDeO3tr5g41h6079AOXi5Bl2TFhyk",
        "dest_dir": "data/raw/tiles",
        "check": "data/raw/tiles/tile_18_223561_101512.jpg",
    },
    {
        "name": "raw_search_tiles",
        "drive_id": "11sC0n_tR2VVXfsdTZ1UET0X4aYID6CTj",
        "dest_dir": "data/raw/search_tiles",
        "check": "data/raw/search_tiles/gwangjin_jayang",
    },
]


def _is_present(asset: dict) -> bool:
    return (PROJECT_ROOT / asset["check"]).exists()


def _download_and_extract(asset: dict) -> None:
    dest_dir    = PROJECT_ROOT / asset["dest_dir"]
    dest_dir.mkdir(parents=True, exist_ok=True)

    zip_path    = PROJECT_ROOT / f"_tmp_{asset['name']}.zip"
    extract_dir = PROJECT_ROOT / f"_tmp_extract_{asset['name']}"

    print(f"[download_assets] '{asset['name']}' 다운로드 중...")
    gdown.download(id=asset["drive_id"], output=str(zip_path), quiet=False)

    print(f"[download_assets] '{asset['name']}' 압축 해제 중... → {dest_dir}")
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    entries = list(extract_dir.iterdir())
    src_dir = entries[0] if (len(entries) == 1 and entries[0].is_dir()) else extract_dir

    for item in src_dir.iterdir():
        target = dest_dir / item.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), str(target))

    shutil.rmtree(extract_dir)
    zip_path.unlink()
    print(f"[download_assets] '{asset['name']}' 완료")


def ensure_assets(force: bool = False) -> None:
    """누락된 자산을 모두 다운로드합니다. force=True면 존재 여부와 무관하게 재다운로드합니다."""
    for asset in ASSETS:
        if not force and _is_present(asset):
            print(f"[download_assets] '{asset['name']}' 이미 존재 → 스킵")
            continue
        _download_and_extract(asset)


if __name__ == "__main__":
    ensure_assets(force="--force" in sys.argv)
