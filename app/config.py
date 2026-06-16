"""
app/config.py
─────────────
Streamlit UI(app.py) 전역 설정 모음 — 백엔드 연동 값 · UI 표시 상수 ·
화면 구성용 데이터 · 세션 상태 기본값을 한곳에 모아 관리합니다.

"""

from __future__ import annotations

import os

# ─────────────────────────────────────────────
# 백엔드(api/) 연동 설정
# ─────────────────────────────────────────────
API_BASE_URL     = os.getenv("API_BASE_URL", "http://localhost:8000")
API_REQUEST_TIMEOUT = 120  # CLIP 인코딩 + FAISS 검색 + enrich(Kakao/Solar LLM) 포함 넉넉한 타임아웃


# ─────────────────────────────────────────────
# 결과 카드 / 지도 표시용 상수
# ─────────────────────────────────────────────
RANK_SYM   = ["①","②","③","④","⑤","⑥","⑦"]
RANK_CLS   = ["c1","c2","c3","","","",""]
CARD_CLS   = ["t1","t2","t3","","","",""]
MAP_COLORS = ["#2A6B4F","#1E4B8F","#C8761A","#999","#bbb","#999","#bbb"]


# ─────────────────────────────────────────────
# 2단계 — 탐색 기준 지역 선택지
# ─────────────────────────────────────────────
# UI selectbox 레이블 → pipeline.search.UI_LABEL_TO_DISTRICT 의 district 키와 반드시 일치시킬 것
UI_LABEL_TO_DISTRICT = {
    "광진구 자양동":             "jayangdong",
    "송파구 가락동·문정동 일대":  "garakdong",
    "중구 신당동·황학동":         "sindangdong",
}

DISTRICT_OPTIONS = [
    {
        "label": "광진구 자양동",
        "tag": "한강변·수변 녹지 매칭용",
        "desc": "한강변 및 수변 녹지 환경과 유사한 입지 탐색에 적합합니다.",
        "icon": "🌊",
    },
    {
        "label": "송파구 가락동·문정동 일대",
        "tag": "고밀도 계획 주거 및 역세권 배후지 매칭용",
        "desc": "고밀도 계획 주거지 및 역세권 배후 상업 환경 매칭에 특화됩니다.",
        "icon": "🏙️",
    },
    {
        "label": "중구 신당동·황학동",
        "tag": "구릉지 주택가 및 도심 배후용",
        "desc": "구릉지형 저층 주택가와 도심 배후 상업 구역 매칭에 특화됩니다.",
        "icon": "⛰️",
    },
]


# ─────────────────────────────────────────────
# 1단계 — 예시 쿼리 태그
# ─────────────────────────────────────────────
EXAMPLE_QUERIES = [
    "숲세권 조용한 저밀도 주거지",
    "역 바로 앞 편리한 도심형",
    "소규모 상가가 밀집한 골목 상권",
    "초등학교 가깝고 아이 키우기 좋은",
    "대단지 아파트 밀집 지역",
]


# ─────────────────────────────────────────────
# 세션 상태 기본값
# ─────────────────────────────────────────────
DEFAULT_SESSION_STATE = {
    "search_results":           None,   # STEP 1 API 원본 결과 (LocationResult 목록)
    "final_results":            None,   # 화면에 표시 중인 2단계 결과
    "search_mode":              "",     # "" | "text" | "recommend"
    "query_input_value":        "",
    "last_searched_query":      "",
    "selected_result_idx":      None,   # 1단계에서 사용자가 선택한 결과 카드 인덱스
    "selected_district_toggle": None,   # 2단계에서 선택한 탐색 기준 지역 레이블
    "recommend_district_label": "",
}
