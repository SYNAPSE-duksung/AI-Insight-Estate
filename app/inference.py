"""
app/inference.py
────────────────
api/ 백엔드(FastAPI → CLIP/FAISS 추론 파이프라인) 연동 헬퍼 모음.

"""

from __future__ import annotations

import requests
import streamlit as st

from config import API_BASE_URL, API_REQUEST_TIMEOUT


def _call_search_api(path: str, payload: dict) -> list[dict]:
    """
    api/main.py 의 검색 엔드포인트를 호출하고 LocationResult 목록을 반환합니다.
    연결 실패·타임아웃·서버 오류는 모두 RuntimeError 로 통일해 호출부에서 st.error 로 안내합니다.
    """
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=API_REQUEST_TIMEOUT)
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
