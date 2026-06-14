"""
api/schemas.py
──────────────
FastAPI 요청·응답 Pydantic 모델 정의.

STEP 1: POST /step1/search  →  Step1Request  →  SearchResponse
STEP 2: POST /step2/search  →  Step2Request  →  SearchResponse
"""

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# 요청 모델
# ──────────────────────────────────────────────────────────────

class Step1Request(BaseModel):
    query: str = Field(
        ...,
        description="자연어 입지 검색 쿼리",
        examples=["숲세권 저밀도 주거지"],
    )
    top_k: int = Field(
        default=5,
        ge=3,
        le=7,
        description="반환할 결과 수 (3~7)",
    )


class Step2Request(BaseModel):
    image_path: str = Field(
        ...,
        description="STEP 1 결과에서 선택한 타일의 이미지 경로 (서버 내부 처리용)",
        examples=["data/raw/tiles/seongdong/tile_18_223561_101512.jpg"],
    )
    district: str = Field(
        ...,
        description="탐색 대상 구역 키",
        examples=["자양동", "가락문정동", "신당황학동"],
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=5,
        description="반환할 결과 수 (기본 3)",
    )


# ──────────────────────────────────────────────────────────────
# 응답 모델
# ──────────────────────────────────────────────────────────────

class LocationResult(BaseModel):
    rank:           int   = Field(description="유사도 순위")
    tile_id:        str   = Field(description="타일 고유 식별자")
    lat:            float = Field(description="타일 중심 위도")
    lon:            float = Field(description="타일 중심 경도")
    image_path:     str   = Field(description="타일 이미지 절대경로 (STEP 2 쿼리 재사용용)")
    similarity:     float = Field(description="CLIP 임베딩 기반 코사인 유사도 [-1, 1]")
    match_score:    int   = Field(description="결과 집합 내 min-max 정규화 기반 유사 지수 [0, 100] (UI 표시용)")
    label:          str   = Field(description="카카오 reverse geocode 한국어 주소 (실패 시 tile_id)")
    text:           str   = Field(description="Solar LLM 생성 입지 설명문 (실패 시 템플릿 fallback)")
    green_ratio:    float = Field(description="픽셀 기반 녹지율 [0, 1]")
    building_ratio: float = Field(description="픽셀 기반 건물밀도 [0, 1]")


class SearchResponse(BaseModel):
    results: list[LocationResult]