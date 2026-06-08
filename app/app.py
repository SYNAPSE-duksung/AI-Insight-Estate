"""
- 최종적으로 백(api)과 연결된 streamlit UI
AI-Insight Estate — 위성 이미지 기반 부동산 입지 탐색 서비스
Streamlit Web UI (수직 플로우 통합 레이아웃)

실행 방법:
    1) (별도 터미널, 프로젝트 루트에서) uvicorn api.main:app --port 8000 --reload
    2) streamlit run app/app.py
"""

import streamlit as st
from streamlit_folium import st_folium

from ui_helpers import (
    API_BASE_URL,
    RANK_SYM,
    RANK_CLS,
    CARD_CLS,
    MAP_COLORS,
    make_map,
    render_result_card,
    search_step1_api,
    search_step2_api,
    get_selected_base_result,
)

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI-Insight Estate",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CSS (수직 흐름 및 프리미엄 카드 레이아웃)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght=0,400;0,600;1,400&family=Pretendard:wght@300;400;500;600;700&display=swap');

:root {
    --bg:          #F7F5F0;
    --bg-white:    #FFFFFF;
    --bg-soft:     #F0EDE8;
    --accent:      #2A6B4F;
    --accent-lt:   #E8F5EE;
    --accent2:     #1E4B8F;
    --accent2-lt:  #EBF0FA;
    --warm:        #C8761A;
    --text:        #1A1A1A;
    --text-sub:    #555550;
    --text-muted:  #999990;
    --border:      #E2DED8;
    --border-dark: #C8C4BC;
    --radius:      12px;
    --radius-lg:   18px;
    --shadow:      0 2px 14px rgba(0,0,0,0.06);
    --shadow-lg:   0 8px 30px rgba(0,0,0,0.1);
}

.stApp {
    background-color: var(--bg);
    font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif;
}

.main .block-container {
    padding: 2rem 3rem 5rem 3rem;
    max-width: 1200px;
}

/* ── 헤더 ── */
.header-wrap {
    background: var(--bg-white);
    border-bottom: 1px solid var(--border);
    padding: 2rem;
    margin-bottom: 2rem;
    text-align: center;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow);
}
.header-eyebrow {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.6rem;
}
.header-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.6rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.2;
    margin: 0 0 0.6rem 0;
    letter-spacing: -0.02em;
}
.header-title em { color: var(--accent); font-style: italic; }
.header-desc {
    font-size: 0.95rem;
    color: var(--text-sub);
    font-weight: 300;
    margin: 0;
    line-height: 1.8;
}

/* ── 섹션 헤더 ── */
.sec-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.8rem;
    border-bottom: 1px solid var(--bg-soft);
    padding-bottom: 0.8rem;
}
.sec-title-wrap {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.sec-title {
    font-family: 'Pretendard', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text);
    margin: 0;
}
.sec-badge {
    font-family: 'Pretendard', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    padding: 0.2rem 0.65rem;
    border-radius: 100px;
}
.badge-green { background: var(--accent-lt);  color: var(--accent);  }
.badge-blue  { background: var(--accent2-lt); color: var(--accent2); }

.sec-desc {
    font-size: 0.88rem;
    color: var(--text-sub);
    margin: 0 0 1.2rem 0;
    line-height: 1.6;
}

/* ── 예시 태그 버튼화 ── */
.tags-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}

/* ── Streamlit 위젯 스타일 보완 ── */
.stTextArea > div > div > textarea {
    background: var(--bg) !important;
    border: 1.5px solid var(--border-dark) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-family: 'Pretendard', sans-serif !important;
    font-size: 0.92rem !important;
    line-height: 1.65 !important;
}
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(42,107,79,0.15) !important;
    background: var(--bg-white) !important;
}

div[data-baseweb="select"] > div {
    background-color: var(--bg) !important;
    border: 1.5px solid var(--border-dark) !important;
    border-radius: var(--radius) !important;
}

.stButton > button {
    background: var(--accent) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-family: 'Pretendard', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    padding: 0.75rem 1.6rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #1e523b !important;
    box-shadow: 0 4px 18px rgba(42,107,79,0.25) !important;
    transform: translateY(-1px);
}
.stButton > button:disabled {
    background: var(--bg-soft) !important;
    color: var(--text-muted) !important;
    border: 1px solid var(--border) !important;
    transform: none !important;
    box-shadow: none !important;
}

/* 2단계 전용 푸른색 버튼 스타일 */
.recommend-btn-container .stButton > button {
    background: var(--accent2) !important;
}
.recommend-btn-container .stButton > button:hover {
    background: #14376b !important;
    box-shadow: 0 4px 18px rgba(30,75,143,0.25) !important;
}

/* ── 결과 배너 ── */
.result-banner {
    border-radius: var(--radius);
    padding: 0.8rem 1.2rem;
    margin-bottom: 1.2rem;
    font-size: 0.9rem;
    font-weight: 600;
    line-height: 1.5;
}
.rb-green { background: var(--accent-lt); border: 1px solid #b2d8c4; color: var(--accent); }
.rb-blue  { background: var(--accent2-lt); border: 1px solid #b0c4e8; color: var(--accent2); }

/* ── 지도 ── */
.map-wrap {
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    margin-bottom: 1.5rem;
}

/* ── 결과 카드 격자 구성 ── */
.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
}

.rcard {
    background: var(--bg-white);
    border: 1px solid var(--border);
    border-top: 4px solid var(--border-dark);
    border-radius: var(--radius);
    padding: 1.2rem;
    box-shadow: var(--shadow);
    transition: all 0.18s ease;
}
.rcard.t1 { border-top-color: var(--accent); }
.rcard.t2 { border-top-color: var(--accent2); }
.rcard.t3 { border-top-color: var(--warm); }
.rcard:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-3px);
}

.rcard-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.6rem;
}
.rcard-rank {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    font-weight: 700;
}
.rcard-rank.c1 { color: var(--accent); }
.rcard-rank.c2 { color: var(--accent2); }
.rcard-rank.c3 { color: var(--warm); }
.rcard-sim {
    font-family: 'Playfair Display', serif;
    font-size: 1.2rem;
    color: var(--accent);
    font-weight: 700;
}
.rcard-lbl {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--text-sub);
    margin-bottom: 0.2rem;
}
.rcard-text {
    font-size: 0.83rem;
    color: var(--text-sub);
    line-height: 1.6;
    margin-bottom: 0.8rem;
    min-height: 48px;
}
.rcard-coord { font-size: 0.72rem; color: var(--text-muted); margin-top: 0.5rem; }

/* ── 점수 바 ── */
.sbar { margin: 0.3rem 0; }
.sbar-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-bottom: 0.18rem;
}
.sbar-bg {
    height: 4px;
    background: var(--bg-soft);
    border-radius: 100px;
    overflow: hidden;
}
.sbar-fill { height: 100%; border-radius: 100px; }

/* ── 첫 가이드 및 대기 빈 상태 (고도화된 일러스트형 카드) ── */
.guide-container {
    padding: 1rem 0;
}
.guide-main-card {
    background: linear-gradient(135deg, #fbfaf8 0%, #edeae4 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 2.2rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    margin-bottom: 1.5rem;
    box-shadow: inset 0 0 20px rgba(0,0,0,0.01);
}
.guide-icon-animation {
    font-size: 3rem;
    animation: pulse 2.5s infinite alternate;
    margin-bottom: 1rem;
}
.guide-title {
    font-size: 1.25rem;
    color: var(--text);
    font-weight: 700;
    margin-bottom: 0.5rem;
}
.guide-subtitle {
    font-size: 0.88rem;
    color: var(--text-sub);
    max-width: 550px;
    line-height: 1.7;
    margin-bottom: 0;
}

.guide-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.2rem;
}
.guide-card {
    background: var(--bg-white);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.4rem;
    box-shadow: var(--shadow);
    transition: transform 0.2s ease;
}
.guide-card:hover {
    transform: translateY(-2px);
}
.guide-card-icon {
    font-size: 1.8rem;
    color: var(--accent);
    margin-bottom: 0.6rem;
}
.guide-card-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.4rem;
}
.guide-card-desc {
    font-size: 0.8rem;
    color: var(--text-sub);
    line-height: 1.6;
}

/* ── 선택된 카드 강조 ── */
.rcard.selected {
    border: 2.5px solid var(--accent) !important;
    background: var(--accent-lt) !important;
    box-shadow: 0 0 0 4px rgba(42,107,79,0.12), var(--shadow-lg) !important;
    transform: translateY(-4px) !important;
}
.rcard.selected .rcard-sim { color: var(--accent); }

/* ── 선택된 입지 요약 배너 ── */
.selected-info-box {
    background: linear-gradient(135deg, #e8f5ee 0%, #d4eee0 100%);
    border: 2px solid var(--accent);
    border-radius: var(--radius);
    padding: 1rem 1.4rem;
    margin: 1.2rem 0 0.5rem 0;
    display: flex;
    align-items: flex-start;
    gap: 0.8rem;
}
.selected-info-icon { font-size: 1.5rem; flex-shrink: 0; margin-top: 0.1rem; }
.selected-info-label {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.25rem;
}
.selected-info-name {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.2rem;
}
.selected-info-desc {
    font-size: 0.82rem;
    color: var(--text-sub);
    line-height: 1.55;
}

/* ── 2단계 동 토글 버튼 ── */
.district-toggle-wrap {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}
.district-toggle-card {
    flex: 1;
    min-width: 200px;
    background: var(--bg-white);
    border: 1.5px solid var(--border-dark);
    border-radius: var(--radius);
    padding: 0.9rem 1.1rem;
    cursor: pointer;
    transition: all 0.18s ease;
}
.district-toggle-card.active {
    border-color: var(--accent2);
    background: var(--accent2-lt);
}
.district-toggle-name {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.25rem;
}
.district-toggle-tag {
    font-size: 0.73rem;
    color: var(--text-muted);
    line-height: 1.5;
}

""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UI 화면 구성용 데이터
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

EXAMPLE_QUERIES = [
    "숲세권 조용한 저밀도 주거지",
    "역 바로 앞 편리한 도심형",
    "카페 많고 활기찬 분위기",
    "초등학교 가깝고 아이 키우기 좋은",
    "대단지 아파트 밀집 지역",
]

# ─────────────────────────────────────────────
# 세션 상태 초기화 및 검색어 주입 제어
# ─────────────────────────────────────────────
_DEFAULT_SESSION_STATE = {
    "search_results":           None,   # STEP 1 API 원본 결과 (LocationResult 목록)
    "final_results":            None,   # 화면에 표시 중인 2단계 결과
    "search_mode":              "",     # "" | "text" | "recommend"
    "query_input_value":        "",
    "last_searched_query":      "",
    "selected_result_idx":      None,   # 1단계에서 사용자가 선택한 결과 카드 인덱스
    "selected_district_toggle": None,   # 2단계에서 선택한 탐색 기준 지역 레이블
    "recommend_district_label": "",
}
for _key, _default in _DEFAULT_SESSION_STATE.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ─────────────────────────────────────────────
# 헤더 영역
# ─────────────────────────────────────────────
st.markdown("""
<div class="header-wrap">
  <div class="header-eyebrow">🛰️ &nbsp; Satellite Vision · 성동구 위성 이미지 탐색</div>
  <h1 class="header-title">AI-Insight <em>Estate</em></h1>
  <p class="header-desc">
    원하는 정주 조건의 자연어 명세를 기반으로 성동구 내 최적의 위성 단지를 역탐색합니다.<br>
    선정된 후보지로부터 <b>유사한 공간적 구조와 텍스처를 가진 대안 입지</b>를 순차적으로 확장하여 탐색해 보세요.
  </p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# 상단: 1단계 자연어 입지 검색 카드
# ══════════════════════════════════════════

st.markdown("""
<div class="sec-head">
  <div class="sec-title-wrap">
    <span class="sec-title">🔍 1단계: 자연어 기반 입지 검색 및 수치 명세</span>
  </div>
  <span class="sec-badge badge-green">Semantic Vector Search</span>
</div>
<p class="sec-desc">
  원하는 주거 환경, 녹지 분포, 대중교통 인접성 등 구체적인 형태를 말하듯 입력해 주세요. 위성 데이터셋과의 정밀 매칭 알고리즘이 가동됩니다.
</p>
""", unsafe_allow_html=True)

# 예시 쿼리 태그 클릭 시 state에 반영하여 사용자 텍스트 영역 기본값 세팅 유도
st.markdown('<div class="tags-title">💡 클릭하여 추천 조건 바로 입력하기</div>', unsafe_allow_html=True)
cols_tags = st.columns(len(EXAMPLE_QUERIES))
for idx, query_tag in enumerate(EXAMPLE_QUERIES):
    with cols_tags[idx]:
        if st.button(query_tag, key=f"tag_btn_{idx}", use_container_width=True):
            st.session_state["query_input_value"] = query_tag
            st.rerun()

text_query = st.text_area(
    label="입지 조건 명세 입력",
    label_visibility="collapsed",
    placeholder="예: 서울숲 가깝고 주변 환경이 정온하며 카페들이 아기자기하게 퍼져 있는 저밀도 주거 구역",
    height=90,
    value=st.session_state["query_input_value"],
)

col_ctrl1, col_ctrl2 = st.columns([2.5, 1])
with col_ctrl1:
    top_k = st.select_slider(
        "탐색할 최상위 매칭 후보군 개수",
        options=[3, 4, 5, 6, 7],
        value=5,
        key="top_k_slider"
    )
with col_ctrl2:
    st.markdown('<div style="padding-top: 1rem;">', unsafe_allow_html=True)
    btn_text = st.button("🔍  성동구 위성 패턴 정밀 검색", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

if btn_text:
    if text_query.strip():
        try:
            with st.spinner("성동구 위성 이미지 토폴로지 분석 및 인프라 시맨틱 벡터 스캔 중..."):
                results = search_step1_api(text_query, top_k)
        except RuntimeError as e:
            st.error(f"🚫 {e}")
        else:
            if results:
                st.session_state["search_results"] = results
                st.session_state["final_results"] = results
                st.session_state["search_mode"] = "text"
                st.session_state["last_searched_query"] = text_query
                st.session_state["selected_result_idx"] = None
                st.session_state["selected_district_toggle"] = None
                st.session_state["recommend_district_label"] = ""
            else:
                st.warning("조건에 맞는 입지를 찾지 못했습니다. 다른 표현으로 다시 시도해 보세요.")
    else:
        st.warning("입지 탐색을 위해 텍스트 조건을 입력해 주세요.")


# ══════════════════════════════════════════
# 중단: 입지 분석 및 탐색 대기/결과 카드 (가장 넓은 면적)
# ══════════════════════════════════════════

st.markdown("""
<div class="sec-head">
  <div class="sec-title-wrap">
    <span class="sec-title">🛰️ 위성 이미지 분석 및 탐색 공간 매핑</span>
  </div>
  <span class="sec-badge badge-green" style="background:#f4f0ea; color:#555;">Live Spatial Viewer</span>
</div>
""", unsafe_allow_html=True)

if st.session_state["search_results"] and st.session_state["search_mode"] != "":
    # 1단계 결과는 모드에 관계없이 항상 search_results로 고정 표시
    current_results = st.session_state["search_results"]
    # 검색 맥락을 알려주는 배너 출력
    if st.session_state["search_mode"] == "text":
        preview = st.session_state["last_searched_query"][:50] + ("…" if len(st.session_state["last_searched_query"]) > 50 else "")
        st.markdown(
            f'<div class="result-banner rb-green">'
            f'<b>🔍 1단계 입지 조건 검색결과 활성화</b> &nbsp;·&nbsp; "{preview}" 의 공간 벡터와 일치하는 성동구 상위 지역들</div>',
            unsafe_allow_html=True,
        )

    # 1. 지도 시각화
    st.markdown('<div class="map-wrap">', unsafe_allow_html=True)
    st_folium(
        make_map(current_results),
        width=None,
        height=380,
        returned_objects=[],
        key=f"flow_result_map_{st.session_state['search_mode']}_{len(current_results)}"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. 결과 카드 리스트 (그리드 정렬) — 모든 모드에서 선택 버튼 유지
    st.markdown('<div class="results-grid">', unsafe_allow_html=True)
    for i, r in enumerate(current_results):
        rc_idx = min(i, len(CARD_CLS)-1)
        is_selected = st.session_state["selected_result_idx"] == i
        render_result_card(r, rc_idx, selected=is_selected, badge=is_selected)
        btn_label = "✅ 선택됨" if is_selected else "이 입지 선택"
        if st.button(btn_label, key=f"select_card_{i}", use_container_width=True):
            st.session_state["selected_result_idx"] = i
            st.session_state["selected_district_toggle"] = None
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 선택된 입지 요약 배너
    if st.session_state["selected_result_idx"] is not None:
        sel_idx = st.session_state["selected_result_idx"]
        if sel_idx < len(current_results):
            sel_r = current_results[sel_idx]
            st.markdown(
                f'<div class="selected-info-box">'
                f'<div class="selected-info-icon">📌</div>'
                f'<div>'
                f'<div class="selected-info-label">✅ 선택된 기준 입지 — 2단계 유사 입지 탐색에 활용됩니다</div>'
                f'<div class="selected-info-name">{RANK_SYM[sel_idx]} {sel_r["label"]}</div>'
                f'<div class="selected-info-desc">{sel_r["text"]}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

elif st.session_state["search_mode"] == "":
    # 사용자의 입지 탐색과 위성 이미지 이해를 적극적으로 돕는 가이드 일러스트 및 정보 영역
    st.markdown('<div class="guide-container">', unsafe_allow_html=True)

    # 상단 대기 상태 대표 배너
    st.markdown("""
    <div class="guide-main-card">
      <div class="guide-icon-animation">🛰️</div>
      <div class="guide-title">성동구 시맨틱 위성 입지 추천 모델 대기 중</div>
      <p class="guide-subtitle">
        상단에서 자연어로 묘사한 가이드 텍스트를 기반으로, CLIP-ResNet 공간 벡터 매칭 장치가 성동구 내 모든 위성 아일랜드의 필지 밀도 및 주거 환경을 스캐닝하기 시작합니다.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # 위성 분석 기법 소개 카드 3종 (이해를 돕는 시각 일러스트레이션 구조)
    st.markdown('<div class="guide-row">', unsafe_allow_html=True)

    # 카드 1
    st.markdown("""
    <div class="guide-card">
      <div class="guide-card-icon">🌲</div>
      <div class="guide-card-title">식생 환경 수치화 (Greenery)</div>
      <p class="guide-card-desc">위성 이미지의 근적외선 파장 대안 분포 모델링을 통해 실제 산책로 및 공원 숲의 배치 텍스처 밀도를 자동으로 탐지해냅니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # 카드 2
    st.markdown("""
    <div class="guide-card">
      <div class="guide-card-icon">🏢</div>
      <div class="guide-card-title">주거 지동 밀도 분석 (Density)</div>
      <p class="guide-card-desc">격자 정렬 구조와 저층 노후 주택 구역, 대규모 아파트 단지 주동 간격의 광학적 기하 특성을 해석하여 정밀 매칭합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # 카드 3
    st.markdown("""
    <div class="guide-card">
      <div class="guide-card-icon">🛣️</div>
      <div class="guide-card-title">토폴로지 접근도 매칭 (Network)</div>
      <p class="guide-card-desc">다중 역세권 간선도로와 이면도로의 조밀 흐름을 텍스트의 맥락(예: '조용함', '편리함')과 자동 맵핑하여 가치를 검증합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
# 하단: 2단계 매칭 입지 기반 유사 단지 연속 추천 (1단계 검색 완료 후 노출 또는 활성화)
# ══════════════════════════════════════════

st.markdown("""
<div class="sec-head">
  <div class="sec-title-wrap">
    <span class="sec-title">🖼️ 2단계: 유사 입지 확장 탐색 — 성동구 외 지역</span>
  </div>
  <span class="sec-badge badge-blue">Cross-District Similarity</span>
</div>
<p class="sec-desc">
  1단계 결과 중 가장 마음에 드는 입지 블록을 클릭해 선택한 뒤, 아래 <b>탐색 기준 지역</b>을 선택하세요.
  해당 위성 이미지와 시각적으로 가장 유사한 입지를 탐색합니다.
</p>
""", unsafe_allow_html=True)

if st.session_state["search_results"]:
    sel_result = get_selected_base_result()
    sel_base = sel_result["label"]

    col_sel, col_btn2 = st.columns([2.5, 1])
    with col_sel:
        district_labels = [o["label"] for o in DISTRICT_OPTIONS]
        default_dist_idx = 0
        if st.session_state["selected_district_toggle"] in district_labels:
            default_dist_idx = district_labels.index(st.session_state["selected_district_toggle"])

        selected_district_label = st.selectbox(
            "성동구 외 유사 입지를 탐색할 기준 지역 선택",
            options=district_labels,
            index=default_dist_idx,
            key="district_selectbox"
        )
        st.session_state["selected_district_toggle"] = selected_district_label
        opt_info = next(o for o in DISTRICT_OPTIONS if o["label"] == selected_district_label)
        st.markdown(
            f'ℹ️ **"{sel_base}"** 의 위성 이미지 패턴을 기준으로 '
            f'**{opt_info["label"]}**({opt_info["tag"]})에서 유사 입지를 탐색합니다.'
        )

    with col_btn2:
        st.markdown('<div class="recommend-btn-container" style="padding-top:1.6rem;">', unsafe_allow_html=True)
        btn_recommend = st.button("🖼️  성동구 외 유사 입지 탐색", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if btn_recommend:
        district_key = UI_LABEL_TO_DISTRICT[opt_info["label"]]
        try:
            with st.spinner(f"'{sel_base}' 위성 패턴과 유사한 {opt_info['label']} 입지 탐색 중..."):
                recommend_candidates = search_step2_api(
                    image_path=sel_result["image_path"],
                    district_key=district_key,
                    top_k=3,
                )
        except RuntimeError as e:
            st.error(f"🚫 {e}")
        else:
            if recommend_candidates:
                st.session_state["final_results"] = recommend_candidates
                st.session_state["search_mode"] = "recommend"
                st.session_state["recommend_district_label"] = opt_info["label"]
                st.rerun()
            else:
                st.warning("선택한 지역에서 유사한 입지를 찾지 못했습니다.")

    # ── 2단계 유사 입지 탐색 결과 ──
    if st.session_state.get("search_mode") == "recommend" and st.session_state.get("final_results"):
        rec_res = st.session_state["final_results"]
        rec_base = sel_base
        rec_district = st.session_state.get("recommend_district_label", "")
        st.markdown("---")
        st.markdown(
            f'<div class="result-banner rb-blue">'
            f'<b>🖼️ 2단계 유사 입지 탐색 결과</b> &nbsp;·&nbsp; '
            f'기준지 "<b>{rec_base}</b>"과(와) 위성 구조가 유사한 <b>{rec_district}</b> 입지</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="results-grid">', unsafe_allow_html=True)
        for i, r in enumerate(rec_res):
            rc_idx = min(i, len(CARD_CLS)-1)
            render_result_card(r, rc_idx)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # 1단계 검색이 선행되지 않았을 때의 비활성화 UI
    st.markdown(
        '<div style="border: 1.5px dashed var(--border-dark); padding: 2rem; border-radius: var(--radius);'
        ' background: var(--bg); text-align: center; color: var(--text-sub); font-size: 0.9rem;">'
        '🔒 상단의 <b>1단계 자연어 입지 검색</b> 결과가 나타나면, 결과 지역 중 하나를 선택하여 '
        '<b>광진구 자양동 / 송파구 가락·문정동 / 중구 신당·황학동</b> 내 유사 입지를 탐색할 수 있습니다.'
        '</div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────
# 푸터 영역
# ─────────────────────────────────────────────
st.markdown("""
<div style="
    text-align:center; margin-top:3rem;
    padding:1.5rem 0;
    border-top:1px solid var(--border);
    font-size:0.75rem; color:var(--text-muted);
    line-height:2;
">
  🛰️ AI-Insight Estate &nbsp;·&nbsp;
  성동구 위성 이미지 기반 부동산 입지 분석 &nbsp;·&nbsp;
  CLIP + LoRA Fine-tuning &nbsp;·&nbsp;
  VWorld WMTS · Kakao Local API
</div>
""", unsafe_allow_html=True)