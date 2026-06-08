"""
app/ui_helpers.py
─────────────────
app.py 의 화면 렌더링과 api/ 백엔드 연동에 쓰이는 헬퍼 모음.

app.py는 페이지 레이아웃·플로우 구성에 집중하고,
재사용 가능한 로직(지도/카드 렌더링, 이미지 임베딩, API 호출)은
이 모듈에서 가져와 사용합니다.

    from ui_helpers import (
        API_BASE_URL, RANK_SYM, RANK_CLS, CARD_CLS, MAP_COLORS,
        sbar, make_map, tile_image_html, render_result_card,
        search_step1_api, search_step2_api, get_selected_base_result,
    )
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import folium
import requests
import streamlit as st

# ─────────────────────────────────────────────
# 백엔드(api/) 연동 설정
# ─────────────────────────────────────────────
API_BASE_URL     = os.getenv("API_BASE_URL", "http://localhost:8000")
_REQUEST_TIMEOUT = 120  # CLIP 인코딩 + FAISS 검색 + enrich(Kakao/Solar LLM) 포함 넉넉한 타임아웃

# ─────────────────────────────────────────────
# 결과 카드 / 지도 표시용 상수
# ─────────────────────────────────────────────
RANK_SYM   = ["①","②","③","④","⑤","⑥","⑦"]
RANK_CLS   = ["c1","c2","c3","","","",""]
CARD_CLS   = ["t1","t2","t3","","","",""]
MAP_COLORS = ["#2A6B4F","#1E4B8F","#C8761A","#999","#bbb","#999","#bbb"]


# ─────────────────────────────────────────────
# 헬퍼 함수 — UI 렌더링
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


def tile_image_html(image_path: str, alt: str = "") -> str:
    """
    검색 결과 타일의 실제 위성 이미지를 base64 data URI로 임베드한 <img> 태그를 반환합니다.
    파일을 읽을 수 없으면 플레이스홀더 블록을 대신 반환합니다.
    """
    try:
        path = Path(image_path)
        suffix = path.suffix.lower().lstrip(".") or "jpeg"
        mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
        data_uri = f"data:image/{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        return (f'<img src="{data_uri}" alt="{alt}" '
                f'style="display:block;object-fit:cover;width:100%;height:100%;" />')
    except OSError:
        return (
            '<div style="display:flex;align-items:center;justify-content:center;width:100%;'
            'height:100%;background:linear-gradient(135deg,#ddd8d0 0%,#c8c2ba 100%);'
            'color:#999;font-size:2.4rem;">🛰️</div>'
        )


def render_result_card(r: dict, rc_idx: int, *, selected: bool = False, badge: bool = False) -> None:
    """1단계/2단계 공용 결과 카드(지도 썸네일 + 수치 명세)를 렌더링합니다."""
    selected_cls = " selected" if selected else ""
    selected_badge = (
        '<div style="margin-top:0.6rem;font-size:0.78rem;font-weight:700;color:var(--accent);">✅ 선택됨</div>'
        if badge else ""
    )
    st.markdown(
        f'<div class="rcard {CARD_CLS[rc_idx]}{selected_cls}" style="display:flex;gap:0;padding:0;overflow:hidden;align-items:stretch;">'
        f'<div style="flex:1;min-width:0;padding:1.2rem;">'
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
        f'{selected_badge}'
        f'</div>'
        f'<div style="width:300px;height:300px;flex-shrink:0;border-left:1px solid var(--border);">'
        f'{tile_image_html(r["image_path"], r["label"])}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# 헬퍼 함수 — api/ 백엔드 연동
# ─────────────────────────────────────────────
def _call_search_api(path: str, payload: dict) -> list[dict]:
    """
    api/main.py 의 검색 엔드포인트를 호출하고 LocationResult 목록을 반환합니다.
    연결 실패·타임아웃·서버 오류는 모두 RuntimeError 로 통일해 호출부에서 st.error 로 안내합니다.
    """
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=_REQUEST_TIMEOUT)
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"API 서버({API_BASE_URL})에 연결할 수 없습니다. "
            f"`uvicorn api.main:app --port 8000` 로 백엔드를 먼저 실행해 주세요."
        ) from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError("API 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.") from e

    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"검색 요청이 실패했습니다 ({resp.status_code}) — {detail}")

    return resp.json().get("results", [])


def search_step1_api(query: str, top_k: int) -> list[dict]:
    """STEP 1: 자연어 → 성동구 입지 검색 (POST /step1/search)."""
    return _call_search_api("/step1/search", {"query": query, "top_k": top_k})


def search_step2_api(image_path: str, district_key: str, top_k: int = 3) -> list[dict]:
    """STEP 2: 선택 타일 이미지 → 구역 내 유사 입지 검색 (POST /step2/search)."""
    return _call_search_api(
        "/step2/search",
        {"image_path": image_path, "district": district_key, "top_k": top_k},
    )


def get_selected_base_result() -> dict | None:
    """1단계 결과 중 사용자가 선택한(없으면 1순위) 기준 입지의 전체 결과 dict를 반환합니다."""
    results = st.session_state.get("search_results") or []
    if not results:
        return None
    idx = st.session_state.get("selected_result_idx")
    if idx is not None and idx < len(results):
        return results[idx]
    return results[0]
