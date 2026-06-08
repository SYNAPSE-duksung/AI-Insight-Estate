"""
config.py
─────────
프로젝트 백엔드(pipeline/, api/) 전역 설정 모음.

참고: UI 전용 설정은 app/config.py 에 별도로 둡니다.
"""

from __future__ import annotations

from pathlib import Path

# ──────────────────────────────────────────────────────────────
# 경로
# ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent

# FAISS 인덱스 · SQLite 메타데이터가 위치한 검색 대상 DB 디렉터리
SEARCH_TARGET_DB_DIR = PROJECT_ROOT / "data" / "processed" / "search_target"


# ──────────────────────────────────────────────────────────────
# CLIP 모델 (pipeline/clip_engine.py)
# ──────────────────────────────────────────────────────────────

# 파인튜닝 모델 경로 (없으면 기본 OpenAI 가중치로 자동 대체)
CLIP_FINETUNED_MODEL_PATH = "checkpoints/clip_finetuned"
CLIP_FALLBACK_MODEL_PATH  = "openai/clip-vit-base-patch32"

# CLIP 텍스트 인코더 최대 토큰 길이
CLIP_TEXT_MAX_LENGTH = 77


# ──────────────────────────────────────────────────────────────
# 검색 대상 district (pipeline/search.py, api/main.py)
# ──────────────────────────────────────────────────────────────

# STEP 1 전용 district 키 (성동구)
SEONGDONG_DISTRICT_KEY = "seongdong"

# UI selectbox 레이블 → district DB 키 매핑
# (faiss_{key}.index / metadata_{key}.db / tile_ids_{key}.npy 파일명에 사용)
UI_LABEL_TO_DISTRICT: dict[str, str] = {
    "광진구 자양동":             "jayangdong",
    "송파구 가락동·문정동 일대":  "garakdong",
    "중구 신당동·황학동":         "sindangdong",
}


# ──────────────────────────────────────────────────────────────
# api/main.py — 행정구역 필터링 · 오버샘플링
# ──────────────────────────────────────────────────────────────

# reverse_geocode 주소의 행정구역 토큰에 기대 구 이름이 없으면 enrich 단계에서
# 제외하고 다음 순위 후보로 백필합니다 (수집 bbox가 행정구역 경계와 어긋나
# 인접 구 타일이 섞여 들어오는 누수 방지).
SEONGDONG_ADDRESS_PREFIX = "성동구"

# STEP 2 탐색 대상 district 키 → 기대 행정구(구) 이름.
# UI_LABEL_TO_DISTRICT 의 레이블("광진구 자양동" 등) 첫 토큰과 일치합니다.
DISTRICT_ADDRESS_PREFIX: dict[str, str] = {
    "jayangdong":  "광진구",
    "garakdong":   "송파구",
    "sindangdong": "중구",
}

# 행정구역 필터링으로 인한 손실을 감안해 top_k보다 넉넉히 후보를 확보하는 배수.
SEARCH_OVERSAMPLE_FACTOR = 3


# ──────────────────────────────────────────────────────────────
# 외부 API 공통 (pipeline/enrich.py)
# ──────────────────────────────────────────────────────────────

# 카카오 · Upstage Solar 등 모든 외부 API 호출 공통 타임아웃 (초)
EXTERNAL_API_TIMEOUT = 3


# ──────────────────────────────────────────────────────────────
# Solar LLM (pipeline/enrich.py — generate_location_text)
# ──────────────────────────────────────────────────────────────

SOLAR_MODEL_NAME  = "solar-1-mini-chat"
SOLAR_MAX_TOKENS  = 150
SOLAR_TEMPERATURE = 0.7


# ──────────────────────────────────────────────────────────────
# 카카오 카테고리 검색 — POI 통계 (pipeline/enrich.py — fetch_poi_summary)
# ──────────────────────────────────────────────────────────────
POI_CATEGORY_TARGETS: list[tuple[str, int, str]] = [
    ("SW8", 500,  "station_count"),
    ("MT1", 1000, "mart_count"),
    ("CS2", 300,  "convenience_count"),
    ("SC4", 500,  "school_count"),
    ("PS3", 500,  "daycare_count"),
    ("HP8", 500,  "hospital_count"),
    ("PM9", 300,  "pharmacy_count"),
    ("CE7", 300,  "cafe_count"),
    ("FD6", 300,  "restaurant_count"),
]


# ──────────────────────────────────────────────────────────────
# 픽셀 분석 임계값 (pipeline/enrich.py — compute_ratios)
# ──────────────────────────────────────────────────────────────

# [녹지율] ExGR(Excess Green Ratio) = 3G - 2.4R - B 가 이 값보다 크고
#          G가 R, B보다 모두 큰 픽셀을 녹지로 판정
GREEN_EXGR_THRESHOLD = 30

# [건물밀도] 채도(saturation, %) < MAX  AND  GRAY_MIN < 밝기(gray) < GRAY_MAX
#           인 중성 회색 픽셀을 건물(콘크리트·지붕·도로)로 판정
BUILDING_SATURATION_MAX = 35
BUILDING_GRAY_MIN       = 40
BUILDING_GRAY_MAX       = 210


# ──────────────────────────────────────────────────────────────
# 입지 설명문 fallback 등급 기준 (pipeline/enrich.py — _stub_text)
# ──────────────────────────────────────────────────────────────

GREEN_RATIO_HIGH_THRESHOLD    = 0.15  # 이상이면 "녹지가 풍부"
GREEN_RATIO_MID_THRESHOLD     = 0.05  # 이상이면 "적당한 녹지"
BUILDING_RATIO_HIGH_THRESHOLD = 0.4   # 이상이면 "고밀도 주거·상업 혼합"
BUILDING_RATIO_MID_THRESHOLD  = 0.2   # 이상이면 "중밀도 주거"
