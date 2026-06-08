"""
api/main.py
───────────
FastAPI 서버. CLIP 모델과 FAISS 인덱스를 서버 시작 시 선로드하고
STEP 1 / STEP 2 검색 엔드포인트를 제공합니다.

실행:
    # 프로젝트 루트에서
    uvicorn api.main:app --port 8000 --reload
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pipeline.clip_engine import get_engine
from pipeline.search import (
    UI_LABEL_TO_DISTRICT,
    _load_index,
    search_step1,
    search_step2,
)
from pipeline.enrich import enrich_results
from api.schemas import Step1Request, Step2Request, SearchResponse, LocationResult

# ──────────────────────────────────────────────────────────────
# 선로드할 district 키 목록 (build_vector_db.py 와 일치)
# ──────────────────────────────────────────────────────────────

_ALL_DISTRICTS = ["seongdong"] + list(UI_LABEL_TO_DISTRICT.values())

# ──────────────────────────────────────────────────────────────
# STEP 1 / STEP 2 공통 — 행정구역 필터링 설정
# ──────────────────────────────────────────────────────────────
# reverse_geocode 주소의 행정구역 토큰에 기대 구 이름이 없으면 enrich 단계에서
# 제외하고 다음 순위 후보로 백필합니다 (수집 bbox가 행정구역 경계와 어긋나
# 인접 구 타일이 섞여 들어오는 누수 방지).
_SEONGDONG_ADDRESS_PREFIX = "성동구"

# STEP 2 탐색 대상 district 키 → 기대 행정구(구) 이름.
# UI_LABEL_TO_DISTRICT 의 레이블("광진구 자양동" 등) 첫 토큰과 일치합니다.
_DISTRICT_ADDRESS_PREFIX: dict[str, str] = {
    "jayangdong":  "광진구",
    "garakdong":   "송파구",
    "sindangdong": "중구",
}

# 필터링으로 인한 손실을 감안해 top_k보다 넉넉히 후보를 확보하는 배수.
_OVERSAMPLE_FACTOR = 3

# ──────────────────────────────────────────────────────────────
# Lifespan — 서버 시작 시 모델 + 인덱스 선로드
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    서버 시작 시:
      1. CLIP 모델 (파인튜닝 가중치) 1회 로드
      2. 4개 지역 FAISS 인덱스 모두 선로드 → 모듈 캐시에 저장
    첫 요청 시 지연 없이 즉시 검색 가능.
    """
    print("[lifespan] CLIP 모델 로드 중...")
    get_engine()

    print("[lifespan] FAISS 인덱스 선로드 중...")
    for district in _ALL_DISTRICTS:
        try:
            _load_index(district)
            print(f"{district}")
        except FileNotFoundError as e:
            print(f"{district} 인덱스 없음 (build_vector_db.py 실행 필요): {e}")

    print("[lifespan] 준비 완료")
    yield
    print("[lifespan] 서버 종료")


# ──────────────────────────────────────────────────────────────
# FastAPI 앱
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI-Insight Estate API",
    description="위성 이미지 기반 입지 탐색 서비스 — CLIP + FAISS",
    version="1.0.0",
    lifespan=lifespan,
)

# Streamlit UI (localhost:8501) 에서의 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────
# 헬퍼 — raw 결과 → enriched → LocationResult 변환
# ──────────────────────────────────────────────────────────────

def _to_response(
    raw_results:    list[dict],
    *,
    address_prefix: str | None = None,
    target_count:   int | None = None,
) -> SearchResponse:
    """
    search_step1() / search_step2() raw 결과를
    enrich_results() 로 풍부화한 뒤 SearchResponse 로 변환합니다.

    address_prefix / target_count 는 STEP 1 행정구역 필터링·백필에만 사용되며
    STEP 2 호출 시에는 전달하지 않습니다(다른 구역을 의도적으로 검색하므로).
    """
    enriched = enrich_results(
        raw_results,
        address_prefix=address_prefix,
        target_count=target_count,
    )
    return SearchResponse(
        results=[LocationResult(**r) for r in enriched]
    )


# ──────────────────────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["utils"])
def health():
    """서버 상태 확인."""
    return {"status": "ok"}


@app.post(
    "/step1/search",
    response_model=SearchResponse,
    summary="STEP 1: 자연어 → 성동구 입지 검색",
    tags=["search"],
)
async def step1_search(req: Step1Request):
    try:
        loop        = asyncio.get_event_loop()
        fetch_k     = req.top_k * _OVERSAMPLE_FACTOR
        raw_results = await loop.run_in_executor(
            None, search_step1, req.query, req.top_k, fetch_k
        )
        return await loop.run_in_executor(
            None,
            lambda: _to_response(
                raw_results,
                address_prefix=_SEONGDONG_ADDRESS_PREFIX,
                target_count=req.top_k,
            ),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STEP 1 검색 오류: {e}")


@app.post(
    "/step2/search",
    response_model=SearchResponse,
    summary="STEP 2: 이미지 → 유사 입지 탐색",
    tags=["search"],
)
async def step2_search(req: Step2Request):
    valid = set(UI_LABEL_TO_DISTRICT.values())
    if req.district not in valid:
        raise HTTPException(
            status_code=422,
            detail=f"유효하지 않은 district: '{req.district}'. 허용값: {sorted(valid)}",
        )

    try:
        loop           = asyncio.get_event_loop()
        fetch_k        = req.top_k * _OVERSAMPLE_FACTOR
        address_prefix = _DISTRICT_ADDRESS_PREFIX.get(req.district)
        raw_results    = await loop.run_in_executor(
            None,
            lambda: search_step2(req.image_path, req.district, req.top_k, fetch_k=fetch_k),
        )
        return await loop.run_in_executor(
            None,
            lambda: _to_response(
                raw_results,
                address_prefix=address_prefix,
                target_count=req.top_k,
            ),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STEP 2 검색 오류: {e}")