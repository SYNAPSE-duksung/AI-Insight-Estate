"""
AI-Insight Estate — 위성 이미지 기반 부동산 입지 탐색 서비스
Streamlit Web UI (수직 플로우 통합 레이아웃)

실행 방법: streamlit run app.py
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
]

DUMMY_RECOMMENDS = {
    "성수동 1가 (서울숲 인근)": [
        {"rank": 1, "lat": 37.5385, "lon": 127.0450, "label": "성수동 1가 (뚝섬유원지 초입)",
         "text": "서울숲 남측 주거벨트와 유사한 한강변 녹지축 연결로. 도심 속 정적이고 쾌적한 풍경을 자랑하는 대안 입지.",
         "similarity": 0.912, "green_ratio": 0.35, "building_ratio": 0.25},
        {"rank": 2, "lat": 37.5610, "lon": 127.0340, "label": "응봉동 (대현산공원 남서측)",
         "text": "서울숲-응봉산으로 이어지는 지형적 녹지 인근 주택가. 우수한 식생 환경과 탁 트인 개방감을 제공하는 입지.",
         "similarity": 0.843, "green_ratio": 0.29, "building_ratio": 0.31},
        {"rank": 3, "lat": 37.5420, "lon": 127.0620, "label": "자양동 (노유산 인접 단지)",
         "text": "성동구 경계부와 접한 녹지 밀접 구역으로, 넓은 도로격자와 저층 주동 배치가 서울숲 인근 주거지와 시각적으로 매우 흡사함.",
         "similarity": 0.791, "green_ratio": 0.26, "building_ratio": 0.34},
    ],
    "성수동 2가 (중앙로데오)": [
        {"rank": 1, "lat": 37.5440, "lon": 127.0650, "label": "성수동 2가 (연무장길 동측 외곽)",
         "text": "로데오 메인스트리트와 유사한 붉은 벽돌 지붕 및 중소형 공장 밀집 구역. 독창적인 리노베이션형 개발 잠재력 공유.",
         "similarity": 0.925, "green_ratio": 0.09, "building_ratio": 0.52},
        {"rank": 2, "lat": 37.5415, "lon": 127.0510, "label": "송정동 (송정제방 하단부)",
         "text": "뚝방길을 따라 단층 골목상권이 유기적으로 살아 숨 쉬는 제2의 성수동 유망지. 시각적인 건물 밀도 지수가 로데오와 높은 일치율을 보임.",
         "similarity": 0.814, "green_ratio": 0.18, "building_ratio": 0.44},
        {"rank": 3, "lat": 37.5645, "lon": 127.0605, "label": "용답동 (자동차 상가 배후지)",
         "text": "철제 구조 및 중밀도 다가구 골목들이 얽힌 독특한 공업적 맥락 지대. 빈티지한 위성 텍스처를 고스란히 재현.",
         "similarity": 0.755, "green_ratio": 0.06, "building_ratio": 0.58},
    ],
    "행당동 (무학중고교 일대)": [
        {"rank": 1, "lat": 37.5550, "lon": 127.0450, "label": "행당동 (삼부아파트 배후)",
         "text": "대규모 주거 블록과 학군이 밀집하여 도로 정비 상태 및 건물의 시각적 규칙성이 극대화된 유사 주거 단지.",
         "similarity": 0.898, "green_ratio": 0.20, "building_ratio": 0.42},
        {"rank": 2, "lat": 37.5585, "lon": 127.0295, "label": "하왕십리동 (극동미라주 인근)",
         "text": "경사지에 조화롭게 구축된 안정적 패밀리형 단지군. 행당동 학군가와 공통적인 유동인구 분산 구조를 띰.",
         "similarity": 0.832, "green_ratio": 0.17, "building_ratio": 0.45},
        {"rank": 3, "lat": 37.5455, "lon": 127.0250, "label": "금호동 1가 (벽산하이피아 근방)",
         "text": "조밀하게 설계된 고층 주동과 중앙 광장의 배치가 행당동 주거 중심지구와 동일 선상의 위성 레이아웃을 형성함.",
         "similarity": 0.776, "green_ratio": 0.23, "building_ratio": 0.41},
    ],
    "왕십리역 상권 배후지": [
        {"rank": 1, "lat": 37.5620, "lon": 127.0345, "label": "도선동 (상가 및 주상복합가)",
         "text": "왕십리역 멀티플렉스 인근의 강력한 도심형 배후 골목. 사통팔달 교통 및 고효율 소형 아파트 밀집도 상위 매칭.",
         "similarity": 0.931, "green_ratio": 0.04, "building_ratio": 0.65},
        {"rank": 2, "lat": 37.5505, "lon": 127.0440, "label": "사근동 (한양대 배후 상업가)",
         "text": "대학가 특유 of 고밀도 청년 1인 주거 및 근린 리테일 혼합 상권. 유동 인구 흐름과 시각적 조밀도가 높은 유사성 표출.",
         "similarity": 0.826, "green_ratio": 0.08, "building_ratio": 0.59},
        {"rank": 3, "lat": 37.5350, "lon": 127.0500, "label": "성수동 1가 (상가 주택지)",
         "text": "뚝섬역 이면 도로의 밀집 상업 지구. 초밀집 빌딩숲 구조와 대중교통 인접 편의성이 매우 탁월하게 일치함.",
         "similarity": 0.781, "green_ratio": 0.06, "building_ratio": 0.61},
    ],
    "금호동 4가 (산책로 초입)": [
        {"rank": 1, "lat": 37.5425, "lon": 127.0220, "label": "금호동 3가 (금남시장 배후 구릉지)",
         "text": "전형적인 구릉형 저밀도 주택 배치가 특징이며, 굽이치는 능선을 따라 자연 발생적으로 연결된 계단형 보행로를 간직한 유사 입지.",
         "similarity": 0.915, "green_ratio": 0.23, "building_ratio": 0.33},
        {"rank": 2, "lat": 37.5490, "lon": 127.0185, "label": "옥수동 (달맞이봉공원 북측)",
         "text": "한강 및 공원 접근성이 좋은 대표적 언덕 마을. 조용한 주거 여건과 독자적인 수목 식생 비율이 완전히 동치하는 환경.",
         "similarity": 0.864, "green_ratio": 0.28, "building_ratio": 0.29},
        {"rank": 3, "lat": 37.5580, "lon": 127.0210, "label": "신당동 (중구 경계 고갯길 주거지)",
         "text": "고저차가 있는 독특한 필지 구획선이 관찰되며, 조밀하지만 수목이 주택 사이사이를 메우는 한적한 전원 분위기를 동일하게 소유.",
         "similarity": 0.789, "green_ratio": 0.20, "building_ratio": 0.35},
    ]
}

EXAMPLE_QUERIES = [
    "숲세권 조용한 저밀도 주거지",
    "역 바로 앞 편리한 도심형",
    "카페 많고 활기찬 분위기",
    "초등학교 가깝고 아이 키우기 좋은",
    "대단지 아파트 밀집 지역",
]

RANK_SYM   = ["①","②","③","④","⑤"]
RANK_CLS   = ["c1","c2","c3","",""]
CARD_CLS   = ["t1","t2","t3","",""]
MAP_COLORS = ["#2A6B4F","#1E4B8F","#C8761A","#999","#bbb"]

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

text_query = st.text_area(
    label="입지 조건 명세 입력",
    label_visibility="collapsed",
    placeholder="예: 서울숲 가깝고 주변 환경이 정온하며 카페들이 아기자기하게 퍼져 있는 저밀도 주거 구역",
    height=90,
    value=st.session_state["query_input_value"],
    key="text_query_area",
)

col_ctrl1, col_ctrl2 = st.columns([2.5, 1])
with col_ctrl1:
    top_k = st.select_slider(
        "탐색할 최상위 매칭 후보군 개수",
        options=[3, 5, 7],
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
        preview = text_query[:50] + ("…" if len(text_query) > 50 else "")
        st.markdown(
            f'<div class="result-banner rb-green">'
            f'<b>🔍 1단계 입지 조건 검색결과 활성화</b> &nbsp;·&nbsp; "{preview}" 의 공간 벡터와 일치하는 성동구 상위 지역들</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state["search_mode"] == "recommend":
        st.markdown(
            f'<div class="result-banner rb-blue">'
            f'<b>🖼️ 2단계 단지 유사맥락 연쇄추천 활성화</b> &nbsp;·&nbsp; 기준지 "<b>{st.session_state["selected_base"]}</b>"과(와) 위성 구조가 80% 이상 유사한 다른 대안지</div>',
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
    <span class="sec-title">🖼️ 2단계: 매칭 입지 기반 유사 단지 연속 추천</span>
  </div>
  <span class="sec-badge badge-blue">Satellite Visual Similarity</span>
</div>
<p class="sec-desc">
  1단계 결과지 중 가장 마음에 드는 핵심 입지를 정해 보세요. 위성 데이터셋 전체를 대조 검색하여 시각적으로 매우 흡사한 질감을 지닌 성동구 내 다른 주거벨트를 찾아내는 꼬리물기형 추천입니다.
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
            "대비 비교 기준으로 선정할 대표 단지",
            options=candidate_labels,
            index=default_idx,
            key="selected_base_box"
        )
        # 세션에 상호 작용 값 실시간 기록
        st.session_state["selected_base"] = selected_base_choice
        st.markdown(f"ℹ️ 선택한 **'{selected_base_choice}'** 단지의 고유 위성 픽셀 분포 및 도로 기하 특징 구조를 탐색 템플릿으로 고정합니다.")
        
    with col_btn:
        st.markdown('<div class="recommend-btn-container" style="padding-top: 1.6rem;">', unsafe_allow_html=True)
        btn_recommend = st.button("🖼️  유사 맥락 단지 연쇄 탐색", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    if btn_recommend:
        with st.spinner(f"'{selected_base_choice}'과(와) 시각 기하학적 유사도가 가장 높은 대체 후보군 추출 중..."):
            recommend_candidates = DUMMY_RECOMMENDS.get(selected_base_choice, DUMMY_RECOMMENDS["성수동 1가 (서울숲 인근)"])
            st.session_state["final_results"] = recommend_candidates
            st.session_state["search_mode"] = "recommend"
            st.rerun()  # 상태 전이에 맞춰 화면 새로고침 유도
            
else:
    # 1단계 검색이 선행되지 않았을 때의 비활성화 UI
    st.markdown(
        '<div style="border: 1.5px dashed var(--border-dark); padding: 2rem; border-radius: var(--radius);'
        ' background: var(--bg); text-align: center; color: var(--text-sub); font-size: 0.9rem;">'
        '🔒 상단의 <b>1단계 자연어 입지 검색</b> 결과가 나타나면 해당 입지 중 하나를 골라 2차 유사도 탐색을 개시할 수 있습니다.'
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