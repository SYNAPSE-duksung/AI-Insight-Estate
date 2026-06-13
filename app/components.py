"""
app/components.py
─────────────────
지도·결과 카드 등 화면 컴포넌트 렌더링 헬퍼 모음.

"""

from __future__ import annotations

import folium
import streamlit as st

from config import CARD_CLS, MAP_COLORS, RANK_CLS, RANK_SYM
from utils import tile_image_html


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
        f'<div style="width:250px;height:250px;flex-shrink:0;border-left:1px solid var(--border);">'
        f'{tile_image_html(r["image_path"], r["label"])}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
