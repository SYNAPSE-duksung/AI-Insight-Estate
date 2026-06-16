"""
- 최종적으로 백(api)과 연결된 streamlit UI
AI-Insight Estate — 위성 이미지 기반 부동산 입지 탐색 서비스
Streamlit Web UI (수직 플로우 통합 레이아웃)

실행 방법:
    1) (별도 터미널, 프로젝트 루트에서) uvicorn api.main:app --port 8000 --reload
    2) streamlit run app/app.py
"""

from pathlib import Path

import streamlit as st
from streamlit_folium import st_folium

from config import (
    CARD_CLS,
    DEFAULT_SESSION_STATE,
    DISTRICT_OPTIONS,
    EXAMPLE_QUERIES,
    RANK_SYM,
    UI_LABEL_TO_DISTRICT,
)
from components import make_map, render_result_card
from inference import get_selected_base_result, search_step1_api, search_step2_api

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
# CSS (수직 흐름 및 프리미엄 카드 레이아웃) — app/style.css 참고
# ─────────────────────────────────────────────
_css_text = (Path(__file__).parent / "style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_css_text}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 세션 상태 초기화 및 검색어 주입 제어
# (UI_LABEL_TO_DISTRICT / DISTRICT_OPTIONS / EXAMPLE_QUERIES / DEFAULT_SESSION_STATE 는 config.py 참고)
# ─────────────────────────────────────────────
for _key, _default in DEFAULT_SESSION_STATE.items():
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
    원하는 자연어 명세 조건을 기반으로 성동구 내 최적의 위성 단지를 역탐색합니다.<br>
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
    <span class="sec-title">🔍 1단계: 원하는 입지 조건 검색</span>
  </div>
  <span class="sec-badge badge-green">Semantic Vector Search</span>
</div>
<p class="sec-desc">
  살고 싶은 동네의 분위기를 자유롭게 입력해 주세요. CLIP 모델이 성동구 위성 이미지와 비교해 가장 가까운 입지를 찾아드립니다.
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
    placeholder="예: 나무가 많고 조용하면서 카페가 가까운 저층 주거 지역",
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
    btn_text = st.button("🔍  성동구 입지 검색", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

if btn_text:
    if text_query.strip():
        try:
            with st.spinner("성동구 위성 이미지를 분석하는 중입니다..."):
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
# 1단계 결과 카드 배치 공간
# ══════════════════════════════════════════

st.markdown("""
<div class="sec-head">
  <div class="sec-title-wrap">
    <span class="sec-title">🛰️ 검색 결과 — 위성 이미지 및 지도</span>
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
      <div class="guide-title">입지 검색을 시작해 주세요</div>
      <p class="guide-subtitle">
        위에서 원하는 입지 조건을 입력하면, AI가 성동구 위성 이미지 전체를 분석해 가장 비슷한 분위기의 지역을 찾아드립니다.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # 위성 분석 기법 소개 카드 3종 (이해를 돕는 시각 일러스트레이션 구조)
    st.markdown('<div class="guide-row">', unsafe_allow_html=True)

    # 카드 1
    st.markdown("""
    <div class="guide-card">
      <div class="guide-card-icon">🌲</div>
      <div class="guide-card-title">녹지 환경 분석</div>
      <p class="guide-card-desc">위성 이미지 픽셀을 분석해 나무·공원·녹지가 얼마나 분포하는지 수치로 계산합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # 카드 2
    st.markdown("""
    <div class="guide-card">
      <div class="guide-card-icon">🏢</div>
      <div class="guide-card-title">건물 밀도 분석</div>
      <p class="guide-card-desc">건물이 얼마나 밀집해 있는지 위성 이미지로 파악해, 고밀도/저밀도 지역을 구분합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # 카드 3
    st.markdown("""
    <div class="guide-card">
      <div class="guide-card-icon">🛣️</div>
      <div class="guide-card-title">교통 및 생활 인프라 분석</div>
      <p class="guide-card-desc">카카오 API를 통해 주변 지하철역·버스정류장·마트·학교 등 생활 인프라 정보를 실시간으로 가져옵니다.</p>
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
  1단계에서 마음에 드는 입지를 선택한 뒤, 아래에서 탐색할 <b>기준 지역</b>을 골라주세요.
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
            "성동구 외 유사 입지를 비교할 지역 선택",
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
            with st.spinner(f"'{sel_base}' 위성 이미지와 유사한 {opt_info['label']} 입지 탐색 중..."):
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
        '🔒 먼저 <b>1단계에서 자연어 입지</b>를 검색하고 결과가 나타나면, 하나를 선택해 주세요.'
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
  CLIP ViT-L/14 + LoRA &nbsp;·&nbsp;
  VWorld WMTS · Kakao Local API
</div>
""", unsafe_allow_html=True)