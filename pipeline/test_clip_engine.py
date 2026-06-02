"""
test_clip_engine.py
───────────────────
clip_engine.py 단독 테스트 스크립트.

흐름:
  1. 텍스트 쿼리 → CLIP Text Encoder → 벡터화
  2. FAISS (자양동) 검색 → 유사도 상위 3개 이미지 출력
  3. Top-3 중 랜덤 1개 선정
  4. 선정된 이미지 → CLIP Image Encoder → 벡터화
     → 자양동 FAISS에서 가장 유사한 이미지 1개 검색 (선정 이미지 제외)
  5. 선정 이미지 / 유사 이미지 / 두 이미지 간 유사도 출력

실행:
  python pipeline/test_clip_engine.py
  python pipeline/test_clip_engine.py --query "역세권 고밀도 아파트 단지" --top_k 5
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from pathlib import Path

import faiss
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.font_manager as fm
import numpy as np

# clip_engine 은 같은 디렉터리(또는 pipeline 패키지) 에 있다고 가정
# 프로젝트 루트에서 실행할 경우 아래 import 사용
from clip_engine import get_engine   # pipeline 패키지면 → from pipeline.clip_engine import get_engine

# ── 한글 폰트 설정 (Windows: 맑은 고딕, macOS: AppleGothic, Linux: NanumGothic) ──
import platform
_OS = platform.system()
if _OS == "Windows":
    plt.rcParams["font.family"] = "Malgun Gothic"
elif _OS == "Darwin":
    plt.rcParams["font.family"] = "AppleGothic"
else:
    # Linux: NanumGothic 설치 필요 (apt install fonts-nanum)
    plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False   # 마이너스 기호 깨짐 방지

# ──────────────────────────────────────────────────────────────
# 경로 설정
# ──────────────────────────────────────────────────────────────

# 스크립트가 pipeline/ 안에 있으므로 .parent.parent 로 프로젝트 루트를 잡습니다.
# 프로젝트 루트에서 실행해도 동일하게 동작합니다.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

FAISS_INDEX  = PROJECT_ROOT / "data/processed/search_target/faiss_jayangdong.index"
TILE_IDS_NPY = PROJECT_ROOT / "data/processed/search_target/tile_ids_jayangdong.npy"
METADATA_DB  = PROJECT_ROOT / "data/processed/search_target/metadata_jayangdong.db"


# ──────────────────────────────────────────────────────────────
# 유틸 함수
# ──────────────────────────────────────────────────────────────

def load_index() -> tuple[faiss.Index, list[str]]:
    """FAISS 인덱스와 tile_id 매핑 리스트를 로드합니다."""
    index    = faiss.read_index(str(FAISS_INDEX))
    tile_ids = np.load(str(TILE_IDS_NPY), allow_pickle=True).tolist()
    print(f"[FAISS] 인덱스 로드 완료 — 총 {index.ntotal}개 벡터")
    return index, tile_ids


def get_metadata(tile_id: str) -> dict:
    """SQLite 에서 tile_id 에 해당하는 메타데이터를 반환합니다."""
    conn = sqlite3.connect(str(METADATA_DB))
    conn.row_factory = sqlite3.Row
    row  = conn.execute(
        "SELECT * FROM tile_info WHERE tile_id = ?", (tile_id,)
    ).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"tile_id '{tile_id}' 가 DB에 없습니다.")
    return dict(row)


def normalize_image_path(raw_path: str) -> Path:
    """
    SQLite image_path 컬럼의 혼합 구분자 경로를 절대경로로 정규화합니다.
    예: data/raw/tiles\\tile_18_...jpg → PROJECT_ROOT / data/raw/tiles/tile_18_...jpg
    """
    normalized = Path(str(raw_path).replace("\\", "/"))
    if normalized.is_absolute():
        return normalized
    return PROJECT_ROOT / normalized


def faiss_search(
    index: faiss.Index,
    tile_ids: list[str],
    query_vec: np.ndarray,      # (1, dim) L2 정규화된 float32
    top_k: int,
    exclude_tile_id: str | None = None,
) -> list[dict]:
    """
    FAISS IndexFlatIP 검색 후 결과 딕셔너리 리스트 반환.
    내적 = 코사인 유사도 (L2 정규화 벡터 기준).

    exclude_tile_id 가 지정되면 해당 tile_id 를 결과에서 제외합니다.
    """
    # exclude 가 있을 경우 +1 개 더 검색해서 제외 후 top_k 맞춤
    search_k = top_k + (1 if exclude_tile_id else 0)
    distances, indices = index.search(query_vec, search_k)

    results = []
    rank    = 1
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:          # FAISS 패딩 인덱스 (-1) 방어
            continue
        tid = tile_ids[idx]
        if exclude_tile_id and tid == exclude_tile_id:
            continue         # 제외 대상 스킵
        meta = get_metadata(tid)
        results.append({
            "rank":       rank,
            "tile_id":    tid,
            "similarity": float(dist),          # 코사인 유사도 [-1, 1]
            "lat":        meta["latitude"],
            "lon":        meta["longitude"],
            "image_path": normalize_image_path(meta["image_path"]),
        })
        rank += 1
        if len(results) >= top_k:
            break

    return results


def show_images(
    images_info: list[dict],
    title: str,
    fig_w: int = 5,
) -> None:
    """
    결과 이미지를 matplotlib 으로 출력합니다.
    images_info: [{"image_path": Path, "title": str}, ...]
    """
    n   = len(images_info)
    fig, axes = plt.subplots(1, n, figsize=(fig_w * n, fig_w + 1))
    if n == 1:
        axes = [axes]
    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.98)
    fig.subplots_adjust(top=0.88)

    for ax, info in zip(axes, images_info):
        path = info["image_path"]
        if path.exists():
            ax.imshow(mpimg.imread(str(path)))
        else:
            ax.text(0.5, 0.5, "이미지 없음", ha="center", va="center",
                    transform=ax.transAxes, fontsize=11, color="red")
            ax.set_facecolor("#eee")
        ax.set_title(info["title"], fontsize=9, wrap=True)
        ax.axis("off")

    plt.tight_layout()
    plt.show()


# ──────────────────────────────────────────────────────────────
# 메인 테스트 흐름
# ──────────────────────────────────────────────────────────────

def main(query: str, top_k: int) -> None:
    print("\n" + "=" * 60)
    print(f"  쿼리: '{query}'")
    print("=" * 60)

    # ── 준비 ─────────────────────────────────────────────────
    engine          = get_engine()
    index, tile_ids = load_index()

    # ── STEP 1: 텍스트 → 이미지 검색 ────────────────────────
    print(f"\n[STEP 1] 텍스트 쿼리 → 자양동 FAISS 검색 (Top-{top_k})")
    text_vec = engine.encode_text(query)          # (1, clip_dim)
    top_results = faiss_search(index, tile_ids, text_vec, top_k=top_k)

    print(f"\n  {'순위':<5} {'tile_id':<12} {'유사도':>8}  {'위도':>10}  {'경도':>11}")
    print("  " + "-" * 55)
    for r in top_results:
        print(f"  {r['rank']:<5} {r['tile_id']:<12} {r['similarity']:>8.4f}"
              f"  {r['lat']:>10.6f}  {r['lon']:>11.6f}")

    # Top-3 이미지 시각화
    show_images(
        [{"image_path": r["image_path"],
          "title": f"#{r['rank']}  {r['tile_id']}\n유사도: {r['similarity']:.4f}"}
         for r in top_results],
        title=f"[STEP 1] 텍스트 검색 Top-{top_k}  |  쿼리: '{query}'",
    )

    # ── STEP 2: 랜덤 1개 선정 ────────────────────────────────
    print(f"\n[STEP 2] Top-{top_k} 중 랜덤 1개 선정")
    selected = random.choice(top_results)
    print(f"  선정된 타일: {selected['tile_id']}  (유사도: {selected['similarity']:.4f})")

    # ── STEP 3: 이미지 → 이미지 검색 (선정 이미지 제외) ──────
    print(f"\n[STEP 3] 선정 이미지 → 자양동 FAISS 검색 (Top-1, 선정 이미지 제외)")
    img_vec  = engine.encode_image(selected["image_path"])   # (1, clip_dim)
    sim_results = faiss_search(
        index, tile_ids, img_vec,
        top_k=1,
        exclude_tile_id=selected["tile_id"],
    )

    if not sim_results:
        print("  ❌ 유사 이미지를 찾지 못했습니다.")
        return

    similar = sim_results[0]

    # 선정 이미지 ↔ 유사 이미지 코사인 유사도 직접 계산
    sim_vec       = engine.encode_image(similar["image_path"])
    pair_similarity = float((img_vec @ sim_vec.T).item())

    print(f"\n  {'항목':<12} {'tile_id':<12} {'유사도(쿼리 대비)':>18}")
    print("  " + "-" * 48)
    print(f"  {'선정 이미지':<12} {selected['tile_id']:<12}"
          f" {selected['similarity']:>18.4f}  ← 텍스트 쿼리 기준")
    print(f"  {'유사 이미지':<12} {similar['tile_id']:<12}"
          f" {similar['similarity']:>18.4f}  ← 선정 이미지 기준")
    print(f"\n  두 이미지 간 코사인 유사도: {pair_similarity:.4f}")

    # 두 이미지 시각화
    show_images(
        [
            {"image_path": selected["image_path"],
             "title": f"[선정]\n{selected['tile_id']}\n"
                      f"텍스트 유사도: {selected['similarity']:.4f}"},
            {"image_path": similar["image_path"],
             "title": f"[유사]\n{similar['tile_id']}\n"
                      f"이미지 유사도: {pair_similarity:.4f}"},
        ],
        title="[STEP 3] 선정 이미지 ↔ 가장 유사한 이미지",
        fig_w=6,
    )

    print("\n✅ 테스트 완료")


# ──────────────────────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="clip_engine 단독 테스트")
    parser.add_argument(
        "--query",
        type=str,
        default="숲세권 저밀도 주거지",
        help="텍스트 검색 쿼리 (기본값: '숲세권 저밀도 주거지')",
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=3,
        help="STEP 1 검색 결과 수 (기본값: 3)",
    )
    args = parser.parse_args()
    main(query=args.query, top_k=args.top_k)