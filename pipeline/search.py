"""
pipeline/search.py
──────────────────
FAISS 인덱스·SQLite를 래핑하는 STEP 1 / STEP 2 검색 함수 모듈.

- 단독 테스트 실행: python -m pipeline.search

외부(FastAPI, 테스트 스크립트 등)에서는 아래 두 함수만 호출합니다.

    from pipeline.search import search_step1, search_step2

    # STEP 1: 자연어 → 성동구 이미지 검색
    results = search_step1("숲세권 저밀도 주거지", top_k=5)

    # STEP 2: 이미지 → 선택 구역 유사 이미지 검색
    results = search_step2(
        image_path="data/raw/tiles/tile_18_223561_101512.jpg",
        district="자양동",
        top_k=3,
    )

반환 형식 (두 함수 공통):
    [
        {
            "rank":       int,
            "tile_id":    str,
            "lat":        float,
            "lon":        float,
            "image_path": str,      # 절대경로 문자열 (enrich.py / UI에서 바로 사용 가능)
            "similarity": float,    # 코사인 유사도 [-1, 1]
        },
        ...
    ]

district 키 → DB 파일명 매핑 (UI selectbox 레이블과 일치시킬 것):
    "자양동"    → faiss_자양동.index   / metadata_자양동.db
    "가락문정동" → faiss_가락문정동.index / metadata_가락문정동.db
    "신당황학동" → faiss_신당황학동.index / metadata_신당황학동.db
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import faiss
import numpy as np

from pipeline.clip_engine import get_engine

# ──────────────────────────────────────────────────────────────
# 경로 설정
# ──────────────────────────────────────────────────────────────

# 이 파일(pipeline/search.py)의 두 단계 위 = 프로젝트 루트
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DB_DIR       = _PROJECT_ROOT / "data" / "processed" / "search_target"

# UI selectbox 레이블 → district DB 키 매핑
UI_LABEL_TO_DISTRICT: dict[str, str] = {
    "광진구 자양동":          "jayangdong",
    "송파구 가락동·문정동 일대": "garakdong",
    "중구 신당동·황학동":      "sindangdong",
}

# STEP 1 전용 district 키 (성동구)
_SEONGDONG_KEY = "seongdong"


# ──────────────────────────────────────────────────────────────
# 모듈 레벨 캐시 (재로드 방지)
# ──────────────────────────────────────────────────────────────

_indices:  dict[str, faiss.Index]  = {}   # district_key → FAISS Index
_tile_ids: dict[str, list[str]]    = {}   # district_key → tile_id 리스트


# ──────────────────────────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────────────────────────

def _load_index(district_key: str) -> tuple[faiss.Index, list[str]]:
    """
    FAISS 인덱스와 tile_id 매핑을 로드하고 모듈 캐시에 저장합니다.
    이미 로드된 경우 캐시를 반환합니다.
    """
    if district_key not in _indices:
        index_path = _DB_DIR / f"faiss_{district_key}.index"
        ids_path   = _DB_DIR / f"tile_ids_{district_key}.npy"

        if not index_path.exists():
            raise FileNotFoundError(
                f"[search] FAISS 인덱스 없음: {index_path}\n"
                f"  build_vector_db.py 를 먼저 실행하세요."
            )
        if not ids_path.exists():
            raise FileNotFoundError(
                f"[search] tile_ids 파일 없음: {ids_path}"
            )

        _indices[district_key]  = faiss.read_index(str(index_path))
        _tile_ids[district_key] = np.load(
            str(ids_path), allow_pickle=True
        ).tolist()
        print(
            f"[search] 인덱스 로드: {district_key} "
            f"({_indices[district_key].ntotal}개 벡터)"
        )

    return _indices[district_key], _tile_ids[district_key]


def _get_metadata(tile_id: str, district_key: str) -> dict:
    """SQLite에서 tile_id에 해당하는 메타데이터를 반환합니다."""
    db_path = _DB_DIR / f"metadata_{district_key}.db"
    conn    = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM tile_info WHERE tile_id = ?", (tile_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise ValueError(
            f"[search] tile_id '{tile_id}' 가 {db_path.name} 에 없습니다."
        )
    return dict(row)


def _normalize_path(raw_path: str) -> str:
    """
    SQLite image_path 컬럼의 혼합 구분자 경로를 절대경로 문자열로 정규화합니다.
    예: data/raw/tiles\\tile_18_...jpg
        → C:/Users/.../Sat-Prop-CLIP/data/raw/tiles/tile_18_...jpg
    """
    normalized = Path(str(raw_path).replace("\\", "/"))
    if normalized.is_absolute():
        return str(normalized)
    return str(_PROJECT_ROOT / normalized)


def _run_faiss_search(
    index:            faiss.Index,
    tile_ids:         list[str],
    district_key:     str,
    query_vec:        np.ndarray,       # (1, dim) L2 정규화 float32
    top_k:            int,
    exclude_tile_id:  str | None = None,
) -> list[dict]:
    """
    FAISS IndexFlatIP 검색 후 결과 딕셔너리 리스트를 반환합니다.

    - 내적(inner product) = 코사인 유사도 (L2 정규화 벡터 기준)
    - exclude_tile_id 지정 시 해당 타일을 결과에서 제외
    """
    # 제외 대상이 있으면 여유분 +1 검색
    search_k          = top_k + (1 if exclude_tile_id else 0)
    distances, idxs   = index.search(query_vec, search_k)

    results = []
    rank    = 1

    for dist, faiss_idx in zip(distances[0], idxs[0]):
        if faiss_idx < 0:                          # FAISS 패딩 인덱스 방어
            continue
        tid = tile_ids[faiss_idx]
        if exclude_tile_id and tid == exclude_tile_id:
            continue                                # 선정 이미지 자기 자신 제외

        meta = _get_metadata(tid, district_key)
        results.append({
            "rank":       rank,
            "tile_id":    tid,
            "lat":        meta["latitude"],
            "lon":        meta["longitude"],
            "image_path": _normalize_path(meta["image_path"]),
            "similarity": round(float(dist), 6),   # 코사인 유사도 [-1, 1]
        })
        rank += 1
        if len(results) >= top_k:
            break

    return results


# ──────────────────────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────────────────────

def search_step1(query: str, top_k: int = 5, fetch_k: int | None = None) -> list[dict]:
    """
    STEP 1: 자연어 쿼리 → 성동구 FAISS 검색.

    Args:
        query:   사용자 입력 자연어 (예: "숲세권 조용한 저밀도 주거지")
        top_k:   반환할 결과 수 (3~7, UI 슬라이더 값)
        fetch_k: FAISS에서 실제로 가져올 후보 수. 지정하지 않으면 top_k와 동일.
                 enrich 단계에서 행정구역(예: "성동구") 필터링 후 백필이 필요한
                 경우(api/main.py STEP 1 엔드포인트) top_k보다 큰 값을 넘겨
                 여유 후보를 확보합니다.

    Returns:
        코사인 유사도 내림차순 정렬된 딕셔너리 리스트 (최대 fetch_k or top_k개).
        각 항목: {rank, tile_id, lat, lon, image_path, similarity}
    """
    engine             = get_engine()
    query_vec          = engine.encode_text(query)              # (1, clip_dim)
    index, tile_ids    = _load_index(_SEONGDONG_KEY)
    k                  = fetch_k if fetch_k is not None else top_k

    return _run_faiss_search(
        index, tile_ids, _SEONGDONG_KEY, query_vec, k
    )


def search_step2(
    image_path:      str,
    district:        str,
    top_k:           int = 3,
    exclude_tile_id: str | None = None,
    fetch_k:         int | None = None,
) -> list[dict]:
    """
    STEP 2: STEP 1에서 선택한 성동구 타일 이미지 → 선택 구역 FAISS 검색.

    Args:
        image_path:      STEP 1 결과에서 선택한 타일의 이미지 경로.
                         SQLite image_path 컬럼값(혼합 구분자)도 허용.
        district:        탐색 대상 구역 키.
                         "자양동" | "가락문정동" | "신당황학동"
                         (UI_LABEL_TO_DISTRICT 로 변환 후 전달 권장)
        top_k:           반환할 결과 수 (기본 3)
        exclude_tile_id: 결과에서 제외할 tile_id.
                         이미지→이미지 검색 시 쿼리 이미지 자신을 제외할 때 사용.
        fetch_k:         FAISS에서 실제로 가져올 후보 수. 지정하지 않으면 top_k와 동일.
                         enrich 단계에서 행정구역(예: "광진구") 필터링 후 백필이
                         필요한 경우(api/main.py STEP 2 엔드포인트) top_k보다 큰
                         값을 넘겨 여유 후보를 확보합니다.

    Returns:
        코사인 유사도 내림차순 정렬된 딕셔너리 리스트 (최대 fetch_k or top_k개).
        각 항목: {rank, tile_id, lat, lon, image_path, similarity}

    Raises:
        ValueError: district 키가 유효하지 않을 때.
        FileNotFoundError: FAISS 인덱스 또는 이미지 파일이 없을 때.
    """
    valid_districts = set(UI_LABEL_TO_DISTRICT.values())
    if district not in valid_districts:
        raise ValueError(
            f"[search] 유효하지 않은 district: '{district}'\n"
            f"  허용값: {sorted(valid_districts)}"
        )

    engine          = get_engine()
    image_vec       = engine.encode_image(image_path)           # (1, clip_dim)
    index, tile_ids = _load_index(district)
    k               = fetch_k if fetch_k is not None else top_k

    return _run_faiss_search(
        index, tile_ids, district, image_vec, k, exclude_tile_id
    )


# ──────────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("[STEP 1] 자연어 → 성동구 검색")
    print("=" * 60)
    step1_results = search_step1("숲세권 저밀도 주거지", top_k=3)
    for r in step1_results:
        print(
            f"  #{r['rank']}  {r['tile_id']}  "
            f"유사도={r['similarity']:.4f}  "
            f"({r['lat']:.6f}, {r['lon']:.6f})"
        )
        print(f"       {r['image_path']}")

    print()
    print("=" * 60)
    print("[STEP 2] 이미지 → 자양동 검색")
    print("=" * 60)
    # STEP 1 첫 번째 결과 이미지를 쿼리로 사용
    if step1_results:
        selected       = step1_results[0]
        step2_results  = search_step2(
            image_path      = selected["image_path"],
            district        = "jayangdong",
            top_k           = 3,
            exclude_tile_id = selected["tile_id"],   # 자기 자신 제외 (구역이 다르므로 불필요하지만 방어)
        )
        for r in step2_results:
            print(
                f"  #{r['rank']}  {r['tile_id']}  "
                f"유사도={r['similarity']:.4f}  "
                f"({r['lat']:.6f}, {r['lon']:.6f})"
            )
            print(f"       {r['image_path']}")
    else:
        print("  STEP 1 결과 없음 — STEP 2 스킵")