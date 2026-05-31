"""
AI-Insight Estate — 위성 이미지 기반 부동산 입지 탐색 서비스
Streamlit Web UI (수직 플로우 통합 레이아웃)

실행 방법: streamlit run app.py

*0601 기준 추가 수정이 필요한 부분*
- 1단계 검색 후보군 개수를 3개로 했다고 하자,
- 검색 결과로 나온 3개 중 가장 마음에 드는 입지 하나를 사용자가 선택한다
- 예를 들어 이걸 2번이라고 하자
- search_results의 2번을 선택하면 해당 번호가 선택됨을 시각적으로 명시(색을 바뀌게 한다거나, 2단계에 선택된 입지를 설명하는 란을 띄운다거나 등..)
- 성동구 외 유사 입지를 탐색할 기준 지역 선택에 있는 선택지는 성동구를 제외하고 3개 이상의 동으로 한다.
- 사용자가 행당동을 선택한다면, 행당동의 위성 이미지를 이미지 투 이미지 검색을 통해 성동구의 search_results 2번과 가장 유사한 입지(고정된 위성 이미지 혹은 해당 위성 이미지에 해당하는 고정된 지도) 3 곳을 제공한다.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
from PIL import Image
import numpy as np

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

/* ── 섹션 카드 ── */
.flow-card {
    background: var(--bg-white);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 2rem;
    box-shadow: var(--shadow);
    margin-bottom: 2rem;
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

@keyframes pulse {
    0% { transform: scale(1); }
    100% { transform: scale(1.08); }
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 더미 데이터
# ─────────────────────────────────────────────
DUMMY_TEXT_RESULTS = [
    {"rank": 1, "lat": 37.5468, "lon": 127.0551, "label": "성수동 1가 (서울숲 인근)",
     "text": "서울숲과 인접한 최고급 주거 대안지. 울창한 녹지 비율과 저밀도 카페 상권이 유기적으로 결합된 완벽한 숲세권 입지.",
     "similarity": 0.884, "green_ratio": 0.38, "building_ratio": 0.28},
    {"rank": 2, "lat": 37.5512, "lon": 127.0429, "label": "성수동 2가 (중앙로데오)",
     "text": "트렌디한 붉은 벽돌 저층 건물이 밀집된 특화 상권. 수공업 인프라와 세련된 리테일 숍들이 교차하는 활기찬 문화 구역.",
     "similarity": 0.821, "green_ratio": 0.12, "building_ratio": 0.49},
    {"rank": 3, "lat": 37.5621, "lon": 127.0498, "label": "행당동 (무학중고교 일대)",
     "text": "명문 학군과 중층 아파트가 조화롭게 어우러진 주거 전용 대안지. 도보 거리 내 공원과 생활 커뮤니티가 발달함.",
     "similarity": 0.743, "green_ratio": 0.22, "building_ratio": 0.39},
    {"rank": 4, "lat": 37.5589, "lon": 127.0372, "label": "왕십리역 상권 배후지",
     "text": "다양한 지하철 호선이 교차하는 최상급 교통 역세권. 고밀도 오피스텔 및 근린 상업시설이 조밀하게 형성된 지역.",
     "similarity": 0.698, "green_ratio": 0.05, "building_ratio": 0.62},
    {"rank": 5, "lat": 37.5398, "lon": 127.0289, "label": "금호동 4가 (산책로 초입)",
     "text": "한강 조망을 일부 품은 자연 지형 순응형 구릉지 주택가. 녹지가 완만히 형성되어 고요하고 평화로운 분위기 제공.",
     "similarity": 0.658, "green_ratio": 0.24, "building_ratio": 0.32},
    {"rank": 6, "lat": 37.5545, "lon": 127.0318, "label": "응봉동 (중앙철교 북측)",
     "text": "중랑천·한강 수변이 맞닿는 친수 입지. 재개발 예정 저층 주거지와 공원 벨트가 공존하는 과도기형 주거 구역.",
     "similarity": 0.631, "green_ratio": 0.20, "building_ratio": 0.36},
    {"rank": 7, "lat": 37.5480, "lon": 127.0195, "label": "옥수동 (옥정초 인근)",
     "text": "한남대교 북단에 인접한 구릉형 주택가. 한강 조망 가능 고지대 단지와 조용한 이면도로 주거지가 어우러진 자연친화형 환경.",
     "similarity": 0.612, "green_ratio": 0.26, "building_ratio": 0.30},
]

# 2단계 더미 데이터: 권역별로 분리
# 권역 A — 광진구 자양·구의동
DUMMY_RECOMMENDS_A = {
    "성수동 1가 (서울숲 인근)": [
        {"rank": 1, "lat": 37.5420, "lon": 127.0820, "label": "광진구 자양동 (자양한강공원 인근)",
         "text": "한강변 녹지축이 서울숲과 유사하게 펼쳐지는 광진구 수변 주거지. 저층 카페 상권과 공원 접근성이 성수 서울숲 입지와 매우 흡사함.",
         "similarity": 0.891, "green_ratio": 0.34, "building_ratio": 0.27},
        {"rank": 2, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (구의한강공원 배후)",
         "text": "한강 조망과 수변 산책로를 갖춘 중층 주거 단지 밀집지. 서울숲 인근과 동일한 수목 밀도·도로 격자 패턴이 위성상에서 확인됨.",
         "similarity": 0.843, "green_ratio": 0.29, "building_ratio": 0.31},
        {"rank": 3, "lat": 37.5310, "lon": 127.0750, "label": "광진구 자양동 (테크노마트 북측 주거지)",
         "text": "강변북로 접근성을 갖추면서도 내부 골목은 조용한 저밀도 주거 환경. 녹지 비율과 건물 높이 분포가 서울숲 입지와 유사한 벨트.",
         "similarity": 0.798, "green_ratio": 0.25, "building_ratio": 0.33},
    ],
    "성수동 2가 (중앙로데오)": [
        {"rank": 1, "lat": 37.5440, "lon": 127.0820, "label": "광진구 자양동 (자양로 상업가)",
         "text": "자양로 변 저층 상가·다가구 혼재 구역. 위성 이미지상 중밀도 지붕 패턴과 이면도로 골목 조직이 성수 로데오와 유사한 텍스처를 보임.",
         "similarity": 0.812, "green_ratio": 0.10, "building_ratio": 0.50},
        {"rank": 2, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (구의역 상권 배후)",
         "text": "2호선 구의역 인근 중밀도 상업 주거 혼합지. 역세권 도심형 배후 골목 구조가 성수 2가와 유사한 위성 패턴.",
         "similarity": 0.768, "green_ratio": 0.09, "building_ratio": 0.53},
        {"rank": 3, "lat": 37.5380, "lon": 127.0860, "label": "광진구 자양동 (광장동 경계 주거지)",
         "text": "주거·상업 혼재 블록이 자연 발생적으로 형성된 구역. 저층 건물 밀집도와 지붕 색조 분포가 성수 로데오 지구와 높은 시각적 유사성.",
         "similarity": 0.731, "green_ratio": 0.11, "building_ratio": 0.48},
    ],
    "행당동 (무학중고교 일대)": [
        {"rank": 1, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (학군 중층 단지)",
         "text": "초·중학교 밀집 구역과 정비된 중층 아파트 단지. 도로 격자 구조와 단지 내 녹지 비율이 행당동 학세권과 위성상 동일 유형.",
         "similarity": 0.865, "green_ratio": 0.20, "building_ratio": 0.41},
        {"rank": 2, "lat": 37.5420, "lon": 127.0820, "label": "광진구 자양동 (자양중학교 인근)",
         "text": "학교 밀집 주거 구역으로 정비된 골목과 보행로가 발달함. 행당동 학군지와 유사한 중층 주거 블록 위성 패턴.",
         "similarity": 0.821, "green_ratio": 0.19, "building_ratio": 0.43},
        {"rank": 3, "lat": 37.5310, "lon": 127.0750, "label": "광진구 자양동 (어린이공원 배후 단지)",
         "text": "근린공원과 연계된 패밀리형 주거 단지. 공원 접근성과 단지 배치 패턴이 행당동 주거 커뮤니티 구조와 매우 흡사함.",
         "similarity": 0.779, "green_ratio": 0.22, "building_ratio": 0.38},
    ],
    "왕십리역 상권 배후지": [
        {"rank": 1, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (2호선 역세권 상권)",
         "text": "2호선 구의역 중심 고밀도 근린 상업 구역. 역세권 배후 소형 상가·오피스텔 밀집 구조가 왕십리 배후지와 동일 위성 패턴.",
         "similarity": 0.878, "green_ratio": 0.05, "building_ratio": 0.62},
        {"rank": 2, "lat": 37.5420, "lon": 127.0820, "label": "광진구 자양동 (건대입구역 배후 상권)",
         "text": "건대입구역 인근 고밀도 청년 상권 배후지. 유동인구 밀집 구조와 소형 상가 조직이 왕십리 역세권과 위성 텍스처 면에서 일치함.",
         "similarity": 0.832, "green_ratio": 0.07, "building_ratio": 0.60},
        {"rank": 3, "lat": 37.5380, "lon": 127.0860, "label": "광진구 자양동 (뚝섬유원지역 배후)",
         "text": "한강변 역세권 상업 지구. 간선도로 배후 상가 밀집 패턴과 고밀도 오피스텔 분포가 왕십리 상권과 유사한 위성 구조.",
         "similarity": 0.791, "green_ratio": 0.08, "building_ratio": 0.58},
    ],
    "금호동 4가 (산책로 초입)": [
        {"rank": 1, "lat": 37.5420, "lon": 127.0820, "label": "광진구 자양동 (아차산 남측 경사지)",
         "text": "아차산 완만한 경사면을 따라 저밀도 단독·다가구가 자리한 자연 순응형 주거지. 녹지 분포와 도로 밀도가 금호동 입지와 동일 유형.",
         "similarity": 0.856, "green_ratio": 0.27, "building_ratio": 0.28},
        {"rank": 2, "lat": 37.5310, "lon": 127.0750, "label": "광진구 자양동 (아차산로 배후 구릉지)",
         "text": "산 아래 구릉형 저층 주거지. 경사 지형을 따른 보행로 패턴과 수목 비율이 금호동 구릉 주거지와 위성상 매우 유사함.",
         "similarity": 0.814, "green_ratio": 0.24, "building_ratio": 0.31},
        {"rank": 3, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (워커힐 방향 경사 주거지)",
         "text": "한강변 고지대 방향 저밀도 경사형 주거 구역. 녹지와 단독주택이 혼재하는 구릉 패턴이 금호동 산책로 입지와 유사함.",
         "similarity": 0.779, "green_ratio": 0.26, "building_ratio": 0.29},
    ],
    "응봉동 (중앙철교 북측)": [
        {"rank": 1, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (한강변 중층 단지)",
         "text": "한강을 접한 중층 주거 단지. 수변 녹지 비율과 철교·교량 인근 특유의 위성 지형 패턴이 응봉동 입지와 매우 흡사함.",
         "similarity": 0.881, "green_ratio": 0.22, "building_ratio": 0.35},
        {"rank": 2, "lat": 37.5310, "lon": 127.0750, "label": "광진구 자양동 (자양동 한강로 배후)",
         "text": "한강 접근성을 갖춘 중밀도 주거 지대. 수변 산책로와 중층 아파트가 혼재하는 구조가 응봉동과 동일한 위성 배치 유형.",
         "similarity": 0.832, "green_ratio": 0.19, "building_ratio": 0.37},
        {"rank": 3, "lat": 37.5380, "lon": 127.0860, "label": "광진구 자양동 (뚝섬 방향 수변 주거지)",
         "text": "한강 수변과 인접한 중층 주거·상업 혼재 구역. 응봉동 수변 위성 패턴과 유사한 하천 인접형 도시 조직.",
         "similarity": 0.781, "green_ratio": 0.20, "building_ratio": 0.36},
    ],
    "옥수동 (옥정초 인근)": [
        {"rank": 1, "lat": 37.5420, "lon": 127.0820, "label": "광진구 자양동 (아차산 남서 경사지)",
         "text": "산을 등지고 한강을 바라보는 구릉지형 입지. 고지대 단지 특유의 도로 굴곡 패턴과 녹지 분포가 옥수동과 거의 동일하게 나타남.",
         "similarity": 0.869, "green_ratio": 0.27, "building_ratio": 0.27},
        {"rank": 2, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (아차산 방향 구릉 단지)",
         "text": "아차산 방향 경사 지형의 저밀도 주거 단지. 한강 조망 가능 고지대 특성이 옥수동 구릉 입지와 위성상 동일 유형으로 분류됨.",
         "similarity": 0.831, "green_ratio": 0.25, "building_ratio": 0.29},
        {"rank": 3, "lat": 37.5310, "lon": 127.0750, "label": "광진구 자양동 (자양4동 구릉 주택가)",
         "text": "완만한 구릉 지형의 저층 단독·다가구 주거지. 수목 피복률과 이면도로 골목 패턴이 옥수동 한강변 구릉지와 유사함.",
         "similarity": 0.793, "green_ratio": 0.24, "building_ratio": 0.30},
    ],
}

# 권역 B — 동대문구 제기·용두동
DUMMY_RECOMMENDS_B = {
    "성수동 1가 (서울숲 인근)": [
        {"rank": 1, "lat": 37.5742, "lon": 127.0412, "label": "동대문구 용두동 (청계천 수변 녹지)",
         "text": "청계천과 인접한 수변 녹지 벨트. 하천 변 저층 주거와 소공원이 연결되는 구조가 서울숲 인근 수변 입지와 위성상 유사함.",
         "similarity": 0.831, "green_ratio": 0.28, "building_ratio": 0.30},
        {"rank": 2, "lat": 37.5698, "lon": 127.0355, "label": "동대문구 제기동 (홍릉수목원 남측)",
         "text": "홍릉수목원과 인접한 동대문구 북부 녹지 주거지. 울창한 수목 분포와 저밀도 단지 패턴이 서울숲 입지와 시각적으로 유사함.",
         "similarity": 0.798, "green_ratio": 0.32, "building_ratio": 0.26},
        {"rank": 3, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (장안근린공원 인근)",
         "text": "근린공원과 연결된 중층 주거 단지. 공원 접근성과 단지 배치 패턴이 서울숲 인근 주거지와 위성 레이아웃 면에서 유사함.",
         "similarity": 0.761, "green_ratio": 0.25, "building_ratio": 0.31},
    ],
    "성수동 2가 (중앙로데오)": [
        {"rank": 1, "lat": 37.5742, "lon": 127.0412, "label": "동대문구 용두동 (공업사 밀집 골목)",
         "text": "중소형 공장·공업사와 저층 상가가 혼재하는 특유의 도시 조직. 위성 이미지상 붉은 지붕·철제 지붕 텍스처가 로데오 지구와 높은 일치율.",
         "similarity": 0.912, "green_ratio": 0.07, "building_ratio": 0.54},
        {"rank": 2, "lat": 37.5698, "lon": 127.0355, "label": "동대문구 제기동 (경동시장 배후 골목)",
         "text": "전통 시장과 연결된 저층 혼합 상업 구역. 골목 단위 소규모 건물 밀도와 도로 패턴이 성수 로데오와 위성 구조적 유사성이 높음.",
         "similarity": 0.831, "green_ratio": 0.09, "building_ratio": 0.51},
        {"rank": 3, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (공장 리모델링 진행지)",
         "text": "성수동 성격과 유사한 공업 지대 리모델링 진행 구역. 위성 이미지에서 동일한 격자형 공장 블록과 단층 상가 혼재 패턴이 관찰됨.",
         "similarity": 0.772, "green_ratio": 0.08, "building_ratio": 0.56},
    ],
    "행당동 (무학중고교 일대)": [
        {"rank": 1, "lat": 37.5698, "lon": 127.0412, "label": "동대문구 제기동 (학군 밀집 주거지)",
         "text": "초·중학교가 도보권에 밀집한 전형적인 학세권 주거 단지. 규칙적인 중층 아파트 배치와 정비된 도로망이 행당동 주거 구조와 일치함.",
         "similarity": 0.887, "green_ratio": 0.19, "building_ratio": 0.43},
        {"rank": 2, "lat": 37.5775, "lon": 127.0388, "label": "동대문구 용두동 (고층 아파트 단지)",
         "text": "재개발로 조성된 고층 주거 블록. 단지 내 녹지 비율과 건물 간격이 행당동 아파트 벨트와 위성 레이아웃 면에서 매우 유사함.",
         "similarity": 0.829, "green_ratio": 0.21, "building_ratio": 0.41},
        {"rank": 3, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (중층 학군 단지)",
         "text": "학교 밀집 중층 주거 단지. 단지 배치 규칙성과 학교 접근성 패턴이 행당동 학세권과 위성 구조적으로 유사함.",
         "similarity": 0.791, "green_ratio": 0.18, "building_ratio": 0.44},
    ],
    "왕십리역 상권 배후지": [
        {"rank": 1, "lat": 37.5742, "lon": 127.0412, "label": "동대문구 용두동 (다중 역세권 교차지)",
         "text": "1·2호선 환승 동대문역 및 5호선 답십리역 인근의 고밀도 도심 상업 주거 혼합 지대. 왕십리와 동일한 다중 환승 역세권 위성 패턴.",
         "similarity": 0.924, "green_ratio": 0.04, "building_ratio": 0.66},
        {"rank": 2, "lat": 37.5698, "lon": 127.0355, "label": "동대문구 제기동 (청량리역 배후 상권)",
         "text": "청량리역 멀티플렉스 인근 고밀도 상업 배후지. 왕십리와 유사한 복합환승 역세권 상업 구조가 위성상에서 확인됨.",
         "similarity": 0.871, "green_ratio": 0.05, "building_ratio": 0.63},
        {"rank": 3, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (간선도로 상권)",
         "text": "5호선 답십리역 중심 간선도로 배후 상업 구역. 역세권 고밀도 개발과 이면 주거지 공존 구조가 왕십리와 매우 흡사함.",
         "similarity": 0.801, "green_ratio": 0.06, "building_ratio": 0.60},
    ],
    "금호동 4가 (산책로 초입)": [
        {"rank": 1, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (중랑천 배후 구릉지)",
         "text": "중랑천 인근 완만한 구릉지 저층 주거지. 수변·녹지 접근성과 저밀도 주택 배치가 금호동 산책로 입지와 위성 패턴상 유사함.",
         "similarity": 0.823, "green_ratio": 0.22, "building_ratio": 0.32},
        {"rank": 2, "lat": 37.5698, "lon": 127.0355, "label": "동대문구 제기동 (배봉산 남측 주거지)",
         "text": "배봉산 자락 아래 저밀도 구릉형 주거지. 산 인접 수목 분포와 이면도로 패턴이 금호동 구릉 주거 입지와 유사함.",
         "similarity": 0.791, "green_ratio": 0.24, "building_ratio": 0.30},
        {"rank": 3, "lat": 37.5742, "lon": 127.0412, "label": "동대문구 용두동 (경사 주택가)",
         "text": "완만한 경사 지형의 저층 다가구 주거지. 골목 보행로 패턴과 녹지 분포가 금호동 산책로 구간과 위성상 유사한 텍스처.",
         "similarity": 0.762, "green_ratio": 0.20, "building_ratio": 0.34},
    ],
    "응봉동 (중앙철교 북측)": [
        {"rank": 1, "lat": 37.5742, "lon": 127.0412, "label": "동대문구 용두동 (청계천 수변 주거지)",
         "text": "청계천과 인접한 재개발 중층 주거 구역. 하천 수변 위성 패턴과 중층 주거 배치가 응봉동과 구조적 유사성을 보임.",
         "similarity": 0.851, "green_ratio": 0.18, "building_ratio": 0.38},
        {"rank": 2, "lat": 37.5698, "lon": 127.0355, "label": "동대문구 제기동 (청계천 상류 배후지)",
         "text": "청계천 상류 인근 중밀도 주거 구역. 하천 인접 특유의 수변 녹지 패턴이 응봉동 입지와 위성 구조적으로 유사함.",
         "similarity": 0.812, "green_ratio": 0.17, "building_ratio": 0.40},
        {"rank": 3, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (중랑천변 단지)",
         "text": "중랑천변 수변 산책로 인접 중층 단지. 하천 접근성과 수변 위성 패턴이 응봉동 중앙철교 배후 주거지와 유사함.",
         "similarity": 0.779, "green_ratio": 0.19, "building_ratio": 0.37},
    ],
    "옥수동 (옥정초 인근)": [
        {"rank": 1, "lat": 37.5698, "lon": 127.0355, "label": "동대문구 제기동 (배봉산 조망 단지)",
         "text": "배봉산 조망 가능한 구릉형 중층 단지. 고지대 특유의 조망형 주거 배치가 옥수동 구릉 입지와 위성상 동일 유형.",
         "similarity": 0.841, "green_ratio": 0.24, "building_ratio": 0.29},
        {"rank": 2, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (구릉 저층 주택가)",
         "text": "완만한 경사면의 저층 주거지. 수목 피복률과 이면도로 굴곡 패턴이 옥수동 한강변 구릉지와 위성 텍스처 면에서 유사함.",
         "similarity": 0.803, "green_ratio": 0.22, "building_ratio": 0.31},
        {"rank": 3, "lat": 37.5742, "lon": 127.0412, "label": "동대문구 용두동 (고저차 주택가)",
         "text": "고저차 있는 독특한 필지 구획의 저층 주거지. 조망형 단지 배치와 수목 분포가 옥수동 구릉 입지와 구조적으로 유사함.",
         "similarity": 0.771, "green_ratio": 0.21, "building_ratio": 0.33},
    ],
}

# 권역 C — 중구 신당·황학동
DUMMY_RECOMMENDS_C = {
    "성수동 1가 (서울숲 인근)": [
        {"rank": 1, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (서울성곽 숲길 인근)",
         "text": "한양도성 성곽 숲길과 인접한 녹지 주거지. 수목 분포와 저밀도 단지 패턴이 서울숲 인근 주거지와 위성 레이아웃상 유사함.",
         "similarity": 0.821, "green_ratio": 0.30, "building_ratio": 0.27},
        {"rank": 2, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (남산 방향 구릉 녹지)",
         "text": "남산과 이어지는 구릉 녹지축 주거지. 울창한 수목 비율과 저층 주거 배치가 서울숲 입지와 시각적으로 유사한 위성 패턴.",
         "similarity": 0.793, "green_ratio": 0.28, "building_ratio": 0.29},
        {"rank": 3, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (낙산공원 방향 주거지)",
         "text": "낙산공원 접근 가능한 구릉형 저층 주거지. 수목과 공원이 연결된 녹지 구조가 서울숲 인근 입지와 위성 텍스처 면에서 유사함.",
         "similarity": 0.761, "green_ratio": 0.26, "building_ratio": 0.31},
    ],
    "성수동 2가 (중앙로데오)": [
        {"rank": 1, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (황학동 로터리 상권)",
         "text": "황학동 시장과 신당 복합환승센터 인근 저층 혼합 상권. 골목 단위 상가 밀집 패턴과 지붕 텍스처가 성수 로데오와 위성상 유사함.",
         "similarity": 0.845, "green_ratio": 0.06, "building_ratio": 0.55},
        {"rank": 2, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (중고품 시장 골목)",
         "text": "황학동 중고품 시장 특유의 저층 상가 밀집 구역. 불규칙한 지붕 패턴과 소규모 필지 조직이 성수 2가와 위성 텍스처 면에서 유사함.",
         "similarity": 0.808, "green_ratio": 0.05, "building_ratio": 0.57},
        {"rank": 3, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (신당시장 배후 골목)",
         "text": "신당시장과 연결된 전통 상가 배후 골목. 저층 혼합 상업 구조와 건물 밀도 패턴이 성수 로데오 구역과 유사한 위성 이미지.",
         "similarity": 0.772, "green_ratio": 0.07, "building_ratio": 0.52},
    ],
    "행당동 (무학중고교 일대)": [
        {"rank": 1, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (약수역 배후 주거지)",
         "text": "지하철 6호선 인근의 안정적 중층 주거 구역. 학원가와 근린 공원이 혼재하는 패턴이 행당동 생활권과 위성 구조적으로 동일함.",
         "similarity": 0.878, "green_ratio": 0.18, "building_ratio": 0.44},
        {"rank": 2, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (동국대 배후 주거지)",
         "text": "대학 인근 중층 주거와 근린 상업이 혼재한 구역. 학군·교육 시설 밀집 구조가 행당동 주거 패턴과 유사한 위성 레이아웃.",
         "similarity": 0.831, "green_ratio": 0.17, "building_ratio": 0.45},
        {"rank": 3, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (신당동 경계 중층 단지)",
         "text": "신당동과 경계부의 중층 주거 블록. 정비된 단지 배치와 학교 접근성 패턴이 행당동 학세권 구조와 위성상 동일 유형.",
         "similarity": 0.789, "green_ratio": 0.19, "building_ratio": 0.42},
    ],
    "왕십리역 상권 배후지": [
        {"rank": 1, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (황학동 로터리 역세권)",
         "text": "황학동 시장과 신당 복합환승센터가 근접한 도심 밀집 상권. 고밀도 소형 상가·오피스텔 조직이 왕십리 배후지와 유사한 위성 질감.",
         "similarity": 0.891, "green_ratio": 0.05, "building_ratio": 0.63},
        {"rank": 2, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (을지로 방향 상업 배후지)",
         "text": "을지로 연결 도심 상업 배후 구역. 간선도로 인근 고밀도 상업 조직이 왕십리 역세권 배후지와 위성 패턴상 유사함.",
         "similarity": 0.843, "green_ratio": 0.04, "building_ratio": 0.65},
        {"rank": 3, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (퇴계로 배후 주상복합)",
         "text": "퇴계로 인근 고밀도 주상복합 밀집 구역. 도심형 배후 상업 구조와 소형 주거 조직이 왕십리 배후지와 위성상 동일 패턴.",
         "similarity": 0.812, "green_ratio": 0.05, "building_ratio": 0.61},
    ],
    "금호동 4가 (산책로 초입)": [
        {"rank": 1, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (남산 방향 구릉 주택가)",
         "text": "남산과 이어지는 구릉형 저층 주택가. 경사 지형을 따른 보행로 패턴과 수목 분포가 금호동 산책로 구간과 위성상 거의 동일함.",
         "similarity": 0.908, "green_ratio": 0.24, "building_ratio": 0.31},
        {"rank": 2, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (구릉지 저층 주거지)",
         "text": "한양도성 성곽 인근의 저층 순응형 주거 구역. 굽은 골목길과 수목 피복률이 금호동 구릉지와 매우 흡사한 위성 지형 텍스처.",
         "similarity": 0.861, "green_ratio": 0.21, "building_ratio": 0.34},
        {"rank": 3, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (성곽길 고갯길 주거지)",
         "text": "고저차가 있는 독특한 필지 구획선이 관찰되며, 수목이 주택 사이사이를 메우는 한적한 구릉 분위기가 금호동과 동일함.",
         "similarity": 0.814, "green_ratio": 0.20, "building_ratio": 0.35},
    ],
    "응봉동 (중앙철교 북측)": [
        {"rank": 1, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (약수교 인근 수변지)",
         "text": "청계천 하류와 인접한 재개발 진행 구역. 하천 인접 특유의 위성 수변 패턴과 중층 주거 배치가 응봉동과 구조적 유사성을 보임.",
         "similarity": 0.829, "green_ratio": 0.17, "building_ratio": 0.39},
        {"rank": 2, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (한강대로 배후 수변 주거지)",
         "text": "한강 접근 가능한 수변 인접 중층 주거지. 수변 위성 패턴과 중층 주거 조직이 응봉동 수변 입지와 구조적으로 유사함.",
         "similarity": 0.793, "green_ratio": 0.16, "building_ratio": 0.40},
        {"rank": 3, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (청계천 하류 배후지)",
         "text": "청계천 하류 인접 재개발 구역. 하천 수변 특유의 위성 텍스처가 응봉동 수변 주거 패턴과 매우 유사하게 나타남.",
         "similarity": 0.762, "green_ratio": 0.15, "building_ratio": 0.41},
    ],
    "옥수동 (옥정초 인근)": [
        {"rank": 1, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (성곽길 배후 주택가)",
         "text": "한양도성 성곽과 인접한 구릉형 저층 주거지. 한강 조망 가능 고지대와 조용한 이면도로 구조가 옥수동 입지와 위성 패턴상 동일함.",
         "similarity": 0.894, "green_ratio": 0.25, "building_ratio": 0.29},
        {"rank": 2, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (한강변 구릉지)",
         "text": "남산 방향 고저차를 활용한 조망형 저밀도 단지. 한강변 위성 이미지에서 옥수동 구릉 주거지와 동일한 녹지·건물 배치 유형으로 분류됨.",
         "similarity": 0.851, "green_ratio": 0.23, "building_ratio": 0.31},
        {"rank": 3, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (약수동 방향 구릉 단지)",
         "text": "경사 지형을 활용한 조망형 중층 단지. 수목 분포와 구릉 도로 굴곡 패턴이 옥수동 한강변 입지와 위성 텍스처 면에서 유사함.",
         "similarity": 0.812, "green_ratio": 0.22, "building_ratio": 0.30},
    ],
}

# 권역 라벨 매핑
# ─────────────────────────────────────────────
# 2단계 추천 후보지 데이터 구조 (통합 딕셔너리)
# ─────────────────────────────────────────────
DUMMY_RECOMMENDS = {
    "성수동 1가 (서울숲 인근)": [
        {"rank": 1, "lat": 37.5420, "lon": 127.0820, "label": "광진구 자양동 (자양한강공원 인근)",
         "text": "한강변 녹지축이 서울숲과 유사하게 펼쳐지는 광진구 수변 주거지. 저층 카페 상권과 공원 접근성이 성수 서울숲 입지와 매우 흡사함.",
         "similarity": 0.891, "green_ratio": 0.34, "building_ratio": 0.27},
        {"rank": 2, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (구의한강공원 배후)",
         "text": "한강 조망과 수변 산책로를 갖춘 중층 주거 단지 밀집지. 서울숲 인근과 동일한 수목 밀도·도로 격자 패턴이 위성상에서 확인됨.",
         "similarity": 0.843, "green_ratio": 0.29, "building_ratio": 0.31},
        {"rank": 3, "lat": 37.5310, "lon": 127.0750, "label": "광진구 자양동 (테크노마트 북측 주거지)",
         "text": "강변북로 접근성을 갖추면서도 내부 골목은 조용한 저밀도 주거 환경. 녹지 비율과 건물 높이 분포가 서울숲 입지와 유사한 벨트.",
         "similarity": 0.798, "green_ratio": 0.25, "building_ratio": 0.33},
    ],
    "성수동 2가 (중앙로데오)": [
        {"rank": 1, "lat": 37.5742, "lon": 127.0412, "label": "동대문구 용두동 (공업사 밀집 골목)",
         "text": "중소형 공장·공업사와 저층 상가가 혼재하는 특유의 도시 조직. 위성 이미지상 붉은 지붕·철제 지붕 텍스처가 로데오 지구와 높은 일치율을 보임.",
         "similarity": 0.912, "green_ratio": 0.07, "building_ratio": 0.54},
        {"rank": 2, "lat": 37.5698, "lon": 127.0355, "label": "동대문구 제기동 (경동시장 배후 골목)",
         "text": "전통 시장과 연결된 저층 혼합 상업 구역. 골목 단위 소규모 건물 밀도와 도로 패턴이 성수 로데오 구역과 위성 구조적 유사성이 높음.",
         "similarity": 0.831, "green_ratio": 0.09, "building_ratio": 0.51},
        {"rank": 3, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (공장 리모델링 진행지)",
         "text": "성수동 성격과 유사한 공업 지대 리모델링 진행 구역. 위성 이미지에서 동일한 격자형 공장 블록과 단층 상가 혼재 패턴이 관찰됨.",
         "similarity": 0.772, "green_ratio": 0.08, "building_ratio": 0.56},
    ],
    "행당동 (무학중고교 일대)": [
        {"rank": 1, "lat": 37.5698, "lon": 127.0412, "label": "동대문구 제기동 (학군 밀집 주거지)",
         "text": "초·중학교가 도보권에 밀집한 전형적인 학세권 주거 단지. 규칙적인 중층 아파트 배치와 정비된 도로망이 행당동 주거 구조와 일치함.",
         "similarity": 0.887, "green_ratio": 0.19, "building_ratio": 0.43},
        {"rank": 2, "lat": 37.5775, "lon": 127.0388, "label": "동대문구 용두동 (고층 아파트 단지)",
         "text": "재개발로 조성된 고층 주거 블록. 단지 내 녹지 비율과 건물 간격이 행당동 아파트 벨트와 위성 레이아웃 면에서 매우 유사함.",
         "similarity": 0.829, "green_ratio": 0.21, "building_ratio": 0.41},
        {"rank": 3, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (약수역 배후 주거지)",
         "text": "지하철 6호선 인근의 안정적 중층 주거 구역. 학원가와 근린 공원이 혼재하는 패턴이 행당동 생활권과 위성 구조적으로 동일함.",
         "similarity": 0.778, "green_ratio": 0.18, "building_ratio": 0.44},
    ],
    "왕십리역 상권 배후지": [
        {"rank": 1, "lat": 37.5742, "lon": 127.0412, "label": "동대문구 용두동 (다중 역세권 교차지)",
         "text": "1·2호선 환승 동대문역 및 5호선 답십리역 인근의 고밀도 도심 상업 주거 혼합 지대. 왕십리와 동일한 다중 환승 역세권 위성 패턴.",
         "similarity": 0.924, "green_ratio": 0.04, "building_ratio": 0.66},
        {"rank": 2, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (황학동 로터리 일대)",
         "text": "황학동 시장과 신당 복합환승센터가 근접한 도심 밀집 상권. 고밀도 소형 상가·오피스텔 조직이 왕십리 배후지와 유사한 위성 질감을 보임.",
         "similarity": 0.846, "green_ratio": 0.05, "building_ratio": 0.63},
        {"rank": 3, "lat": 37.5820, "lon": 127.0460, "label": "동대문구 답십리동 (간선도로 상권)",
         "text": "5호선 답십리역 중심의 간선도로 배후 상업 구역. 역세권 고밀도 개발과 이면 주거지가 공존하는 도시 구조가 왕십리와 매우 흡사함.",
         "similarity": 0.801, "green_ratio": 0.06, "building_ratio": 0.60},
    ],
    "금호동 4가 (산책로 초입)": [
        {"rank": 1, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (남산 방향 구릉 주택가)",
         "text": "남산과 이어지는 구릉형 저층 주택가. 경사 지형을 따라 자연 발생한 보행로 패턴과 수목 분포가 금호동 산책로 구간과 위성상 거의 동일함.",
         "similarity": 0.908, "green_ratio": 0.24, "building_ratio": 0.31},
        {"rank": 2, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (구릉지 저층 주거지)",
         "text": "한양도성 성곽 인근의 저층 순응형 주거 구역. 굽은 골목길과 수목 피복률이 금호동 구릉지와 매우 흡사한 위성 지형 텍스처를 갖춤.",
         "similarity": 0.861, "green_ratio": 0.21, "building_ratio": 0.34},
        {"rank": 3, "lat": 37.5420, "lon": 127.0820, "label": "광진구 자양동 (아차산 남측 경사지)",
         "text": "아차산 완만한 경사면을 따라 저밀도 단독·다가구가 자리한 자연 순응형 주거지. 녹지 분포와 도로 밀도가 금호동 입지와 동일 유형으로 분류됨.",
         "similarity": 0.814, "green_ratio": 0.27, "building_ratio": 0.28},
    ],
    "응봉동 (중앙철교 북측)": [
        {"rank": 1, "lat": 37.5495, "lon": 127.0910, "label": "광진구 구의동 (한강변 중층 단지)",
         "text": "한강을 접한 중층 주거 단지. 수변 녹지 비율과 철교·교량 인근 특유의 위성 지형 패턴이 응봉동 입지와 매우 흡사함.",
         "similarity": 0.881, "green_ratio": 0.22, "building_ratio": 0.35},
        {"rank": 2, "lat": 37.5310, "lon": 127.0750, "label": "광진구 자양동 (자양동 한강로 배후)",
         "text": "한강 접근성을 갖춘 중밀도 주거 지대. 수변 산책로와 중층 아파트가 혼재하는 구조가 응봉동과 동일한 위성 배치 유형.",
         "similarity": 0.832, "green_ratio": 0.19, "building_ratio": 0.37},
        {"rank": 3, "lat": 37.5610, "lon": 127.0270, "label": "중구 신당동 (약수교 인근 수변지)",
         "text": "청계천 하류와 인접한 재개발 진행 구역. 하천 인접 특유의 위성 수변 패턴과 중층 주거 배치가 응봉동과 구조적 유사성을 보임.",
         "similarity": 0.779, "green_ratio": 0.17, "building_ratio": 0.39},
    ],
    "옥수동 (옥정초 인근)": [
        {"rank": 1, "lat": 37.5560, "lon": 127.0180, "label": "중구 신당동 (성곽길 배후 주택가)",
         "text": "한양도성 성곽과 인접한 구릉형 저층 주거지. 한강 조망 가능 고지대와 조용한 이면도로 구조가 옥수동 입지와 위성 패턴상 동일함.",
         "similarity": 0.894, "green_ratio": 0.25, "building_ratio": 0.29},
        {"rank": 2, "lat": 37.5420, "lon": 127.0820, "label": "광진구 자양동 (아차산 남서 경사지)",
         "text": "산을 등지고 한강을 바라보는 구릉지형 입지. 고지대 단지 특유의 도로 굴곡 패턴과 녹지 분포가 옥수동과 거의 동일하게 나타남.",
         "similarity": 0.845, "green_ratio": 0.27, "building_ratio": 0.27},
        {"rank": 3, "lat": 37.5495, "lon": 127.0150, "label": "중구 황학동 (중구 한강변 구릉지)",
         "text": "남산 방향 고저차를 활용한 조망형 저밀도 단지. 한강변 위성 이미지에서 옥수동 구릉 주거지와 동일한 녹지·건물 배치 유형으로 분류됨.",
         "similarity": 0.798, "green_ratio": 0.23, "building_ratio": 0.31},
    ],
}

EXAMPLE_QUERIES = [
    "숲세권 조용한 저밀도 주거지",
    "역 바로 앞 편리한 도심형",
    "카페 많고 활기찬 분위기",
    "초등학교 가깝고 아이 키우기 좋은",
    "대단지 아파트 밀집 지역",
]

RANK_SYM   = ["①","②","③","④","⑤","⑥","⑦"]
RANK_CLS   = ["c1","c2","c3","","","",""]
CARD_CLS   = ["t1","t2","t3","","","",""]
MAP_COLORS = ["#2A6B4F","#1E4B8F","#C8761A","#999","#bbb","#999","#bbb"]

# ─────────────────────────────────────────────
# 세션 상태 초기화 및 검색어 주입 제어
# ─────────────────────────────────────────────
if "search_results" not in st.session_state:
    st.session_state["search_results"] = None
if "final_results" not in st.session_state:
    st.session_state["final_results"] = None
if "search_mode" not in st.session_state:
    st.session_state["search_mode"] = ""
if "selected_base" not in st.session_state:
    st.session_state["selected_base"] = ""
if "query_input_value" not in st.session_state:
    st.session_state["query_input_value"] = ""
if "last_searched_query" not in st.session_state:
    st.session_state["last_searched_query"] = ""

# ─────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────
def sbar(label, value, color="#2A6B4F"):
    pct = min(int(value * 100), 100)
    return (f'<div class="sbar">'
            f'<div class="sbar-row"><span>{label}</span><span>{value:.2f}</span></div>'
            f'<div class="sbar-bg"><div class="sbar-fill" '
            f'style="width:{pct}%;background:{color};"></div></div></div>')

def make_map(results):
    lats = [r["lat"] for r in results]
    lons = [r["lon"] for r in results]
    m = folium.Map(
        location=[sum(lats)/len(lats), sum(lons)/len(lons)],
        zoom_start=14,
        tiles="CartoDB positron",
    )
    for i, r in enumerate(results):
        c = MAP_COLORS[min(i, len(MAP_COLORS)-1)]
        folium.CircleMarker(
            location=[r["lat"], r["lon"]],
            radius=13 if i == 0 else 9,
            color=c, fill=True, fill_color=c,
            fill_opacity=0.85 if i == 0 else 0.65,
            popup=folium.Popup(
                f"<b style='color:{c}'>#{r['rank']} {r['label']}</b><br>"
                f"<small>{r['text']}</small><br>"
                f"<small>유사도 {r['similarity']:.3f}</small>",
                max_width=200,
            ),
            tooltip=f"#{r['rank']} {r['label']}",
        ).add_to(m)
        folium.Marker(
            location=[r["lat"], r["lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:11px;font-weight:700;color:#fff;'
                     f'background:{c};border-radius:50%;width:20px;height:20px;'
                     f'display:flex;align-items:center;justify-content:center;'
                     f'margin:-10px 0 0 -10px;box-shadow:0 2px 6px rgba(0,0,0,0.2);">'
                     f'{r["rank"]}</div>',
                icon_size=(20, 20), icon_anchor=(10, 10),
            ),
        ).add_to(m)
    return m


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
# st.markdown('<div class="flow-card">', unsafe_allow_html=True)

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
        with st.spinner("성동구 위성 이미지 토폴로지 분석 및 인프라 시맨틱 벡터 스캔 중..."):
            st.session_state["search_results"] = DUMMY_TEXT_RESULTS[:top_k]
            st.session_state["final_results"] = st.session_state["search_results"]
            st.session_state["search_mode"] = "text"
            st.session_state["last_searched_query"] = text_query
            # 검색 결과를 실행했을 때, 2단계 기본 선택 초기화
            if st.session_state["search_results"]:
                st.session_state["selected_base"] = st.session_state["search_results"][0]["label"]
    else:
        st.warning("입지 탐색을 위해 텍스트 조건을 입력해 주세요.")

st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
# 중단: 입지 분석 및 탐색 대기/결과 카드 (가장 넓은 면적)
# ══════════════════════════════════════════
# st.markdown('<div class="flow-card">', unsafe_allow_html=True)

st.markdown("""
<div class="sec-head">
  <div class="sec-title-wrap">
    <span class="sec-title">🛰️ 위성 이미지 분석 및 탐색 공간 매핑</span>
  </div>
  <span class="sec-badge badge-green" style="background:#f4f0ea; color:#555;">Live Spatial Viewer</span>
</div>
""", unsafe_allow_html=True)

if st.session_state["final_results"] and st.session_state["search_mode"] != "":
    current_results = st.session_state["final_results"]

    # 검색 맥락을 알려주는 배너 출력
    if st.session_state["search_mode"] == "text":
        preview = st.session_state["last_searched_query"][:50] + ("…" if len(st.session_state["last_searched_query"]) > 50 else "")
        st.markdown(
            f'<div class="result-banner rb-green">'
            f'<b>🔍 1단계 입지 조건 검색결과 활성화</b> &nbsp;·&nbsp; "{preview}" 의 공간 벡터와 일치하는 성동구 상위 지역들</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state["search_mode"] == "recommend":
        st.markdown(
            f'<div class="result-banner rb-blue">'
            f'<b>🖼️ 2단계 성동구 외 유사 입지 탐색 결과</b> &nbsp;·&nbsp; 기준지 "<b>{st.session_state["selected_base"]}</b>"과(와) 위성 구조가 유사한 인접구 대안 입지</div>',
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

    # 2. 결과 카드 리스트 (그리드 정렬)
    st.markdown('<div class="results-grid">', unsafe_allow_html=True)
    for i, r in enumerate(current_results):
        rc_idx = min(i, len(CARD_CLS)-1)
        st.markdown(
            f'<div class="rcard {CARD_CLS[rc_idx]}">'
            f'<div class="rcard-head">'
            f'<div><div class="rcard-rank {RANK_CLS[rc_idx]}">{RANK_SYM[rc_idx]}</div>'
            f'<div class="rcard-lbl">{r["label"]}</div></div>'
            f'<div style="text-align:right">'
            f'<div class="rcard-sim">{int(r["similarity"]*100)}%</div>'
            f'<div class="rcard-lbl">유사 지수</div></div></div>'
            f'<div class="rcard-text">{r["text"]}</div>'
            f'{sbar("숲세권 수목밀도", r["green_ratio"], "#2A6B4F")}'
            f'{sbar("주동 건물밀도", r["building_ratio"], "#1E4B8F")}'
            f'<div class="rcard-coord">📍 {r["lat"]:.4f}°N &nbsp; {r["lon"]:.4f}°E</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # 🌟 [개선] 사용자의 입지 탐색과 위성 이미지 이해를 적극적으로 돕는 가이드 일러스트 및 정보 영역
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

st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
# 하단: 2단계 매칭 입지 기반 유사 단지 연속 추천 (1단계 검색 완료 후 노출 또는 활성화)
# ══════════════════════════════════════════
# st.markdown('<div class="flow-card">', unsafe_allow_html=True)

st.markdown("""
<div class="sec-head">
  <div class="sec-title-wrap">
    <span class="sec-title">🖼️ 2단계: 유사 입지 확장 탐색 — 성동구 외 지역</span>
  </div>
  <span class="sec-badge badge-blue">Cross-District Similarity</span>
</div>
<p class="sec-desc">
  1단계 결과 중 가장 마음에 드는 입지를 선택하세요. 해당 위성 이미지와 시각적으로 가장 유사한 입지를
  <b>성동구 인접 3개 권역</b>(광진구 자양·구의동 / 동대문구 제기·용두동 / 중구 신당·황학동)에서 탐색합니다.
</p>
""", unsafe_allow_html=True)

if st.session_state["search_results"]:
    # 자연어 검색 완료 후 활성화되는 컨트롤 폼
    candidate_labels = [r["label"] for r in st.session_state["search_results"]]
    
    col_sel, col_btn = st.columns([2.5, 1])
    with col_sel:
        # 이전에 선택한 이력이 세션에 보관되어 있다면 유지
        default_idx = 0
        if st.session_state["selected_base"] in candidate_labels:
            default_idx = candidate_labels.index(st.session_state["selected_base"])
            
        selected_base_choice = st.selectbox(
            "성동구 외 유사 입지를 탐색할 기준 지역 선택",
            options=candidate_labels,
            index=default_idx,
            key="selected_base_box"
        )
        # 세션에 상호 작용 값 실시간 기록
        st.session_state["selected_base"] = selected_base_choice
        st.markdown(f"ℹ️ **'{selected_base_choice}'** 의 위성 이미지 패턴을 기준으로 광진구·동대문구·중구에서 유사 입지를 탐색합니다.")
        
    with col_btn:
        st.markdown('<div class="recommend-btn-container" style="padding-top: 1.6rem;">', unsafe_allow_html=True)
        btn_recommend = st.button("🖼️  성동구 외 유사 입지 탐색", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    if btn_recommend:
        with st.spinner(f"'{selected_base_choice}' 위성 패턴과 유사한 광진구·동대문구·중구 입지 추출 중..."):
            recommend_candidates = DUMMY_RECOMMENDS.get(selected_base_choice, DUMMY_RECOMMENDS["성수동 1가 (서울숲 인근)"])
            st.session_state["final_results"] = recommend_candidates
            st.session_state["search_mode"] = "recommend"
            st.rerun()  # 상태 전이에 맞춰 화면 새로고침 유도
            
else:
    # 1단계 검색이 선행되지 않았을 때의 비활성화 UI
    st.markdown(
        '<div style="border: 1.5px dashed var(--border-dark); padding: 2rem; border-radius: var(--radius);'
        ' background: var(--bg); text-align: center; color: var(--text-sub); font-size: 0.9rem;">'
        '🔒 상단의 <b>1단계 자연어 입지 검색</b> 결과가 나타나면, 결과 지역 중 하나를 선택하여 '
        '<b>광진구·동대문구·중구</b> 내 유사 입지를 탐색할 수 있습니다.'
        '</div>',
        unsafe_allow_html=True
    )

st.markdown('</div>', unsafe_allow_html=True)


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