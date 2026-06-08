"""
pipeline/enrich.py
──────────────────
search.py 의 raw 검색 결과에 픽셀 분석, Kakao API, Solar LLM 정보를 추가합니다.

파이프라인 위치:
    search_step1() / search_step2()
        ↓  raw_results
    enrich_results()          ← 이 모듈(여기서 호출되는 모듈로 사용)
        ↓  enriched_results
    FastAPI → Streamlit UI

각 결과 딕셔너리에 추가되는 필드:
    label         : str    — 카카오 reverse geocode 한국어 주소 (실패 시 tile_id)
    text          : str    — Solar LLM 생성 입지 설명문 (실패 시 템플릿 fallback)
    green_ratio   : float  — 픽셀 기반 녹지율   [0, 1]
    building_ratio: float  — 픽셀 기반 건물밀도 [0, 1]
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────
# 환경변수
# ──────────────────────────────────────────────────────────────

_KAKAO_API   = os.getenv("KAKAO_API", "")
_UPSTAGE_API = os.getenv("UPSTAGE_API", "")

_REQUEST_TIMEOUT = 3   # 모든 외부 API 호출 공통 타임아웃 (초)


# ──────────────────────────────────────────────────────────────
# 1. 픽셀 분석 — 외부 API 없이 이미지 파일에서 직접 계산
# ──────────────────────────────────────────────────────────────

def compute_ratios(image_path: str) -> tuple[float, float]:
    """
    위성 이미지 픽셀을 분석해 녹지율과 건물밀도를 반환합니다.

    [green_ratio]
        ExGR(Excess Green Ratio) 공식 사용:
            ExGR = 3G - 2.4R - B
        ExGR > 15 인 픽셀을 녹지로 판정.
        실제 나무·잔디·공원 영역이 밝은 초록으로 보이는 위성 이미지 특성에 맞춤.

    [building_ratio]
        중성 회색 표면 기준:
            채도(saturation) < 20  AND  70 < 밝기(gray) < 195
        콘크리트·지붕·도로 등 건물 밀집 지역의 회색 픽셀 비율.
    """
    try:
        img  = Image.open(image_path).convert("RGB")
        arr  = np.array(img, dtype=np.float32)   # (H, W, 3)
        R, G, B = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        total = R.size

        # ── 녹지율 ─────────────────────────────────────────────
        exgr         = 3 * G - 2.4 * R - B
        # green_ratio  = float(np.sum(exgr > 15) / total)
        green_ratio  = float(np.sum((exgr > 30) & (G > R) & (G > B)) / total)

        # ── 건물밀도 ───────────────────────────────────────────
        gray         = (R + G + B) / 3.0
        r_norm       = R / 255.0
        g_norm       = G / 255.0
        b_norm       = B / 255.0
        c_max        = np.maximum(np.maximum(r_norm, g_norm), b_norm)
        c_min        = np.minimum(np.minimum(r_norm, g_norm), b_norm)
        saturation   = np.where(c_max > 0, (c_max - c_min) / c_max, 0.0) * 100
        # building_mask    = (saturation < 20) & (gray > 70) & (gray < 195)
        building_mask    = (saturation < 35) & (gray > 40) & (gray < 210)
        building_ratio   = float(np.sum(building_mask) / total)

        return round(green_ratio, 4), round(building_ratio, 4)

    except Exception as e:
        print(f"[enrich] 픽셀 분석 실패 ({Path(image_path).name}): {e}")
        return 0.0, 0.0


# ──────────────────────────────────────────────────────────────
# 2. 카카오 API — 위경도 → 주소 + 인프라 통계
# ──────────────────────────────────────────────────────────────

def reverse_geocode(lat: float, lon: float) -> str:
    """
    카카오 coord2address API로 위경도를 한국어 주소 문자열로 변환합니다.
    """
    if not _KAKAO_API:
        return ""
    try:
        resp = requests.get(
            "https://dapi.kakao.com/v2/local/geo/coord2address.json",
            headers={"Authorization": f"KakaoAK {_KAKAO_API}"},
            params={"x": lon, "y": lat},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        if not docs:
            return ""
        addr = docs[0].get("road_address") or docs[0].get("address")
        if addr is None:
            return ""
        # 도로명 주소 우선, 없으면 지번 주소
        return addr.get("address_name", "")
    except Exception as e:
        print(f"[enrich] reverse_geocode 실패 ({lat}, {lon}): {e}")
        return ""


def fetch_poi_summary(lat: float, lon: float) -> dict:
    """
    카카오 카테고리 검색 API로 주변 인프라 통계를 반환합니다.

    카테고리 코드 / 반경 / 항목:
        SW8  500m  지하철역        — 역세권
        MT1 1000m  대형마트        — 장보기 편의성
        CS2  300m  편의점          — 생활 편의성
        SC4  500m  학교            — 학세권
        PS3  500m  어린이집·유치원  — 육아 인프라
        HP8  500m  병원            — 의료 접근성
        PM9  300m  약국            — 생활 편의성
        CE7  300m  카페            — 상권 활성도
        FD6  300m  음식점          — 상권 활성도
    """
    _EMPTY = {
        "station_count":    0,
        "mart_count":       0,
        "convenience_count":0,
        "school_count":     0,
        "daycare_count":    0,
        "hospital_count":   0,
        "pharmacy_count":   0,
        "cafe_count":       0,
        "restaurant_count": 0,
    }
    if not _KAKAO_API:
        return _EMPTY
    
    base_url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {_KAKAO_API}"}

    # (카테고리 코드, 반경, 결과 딕셔너리 키)
    _TARGETS = [
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

    def _fetch_count(category_code: str, radius: int) -> int:
        try:
            resp = requests.get(
                base_url,
                headers=headers,
                params={
                    "category_group_code": category_code,
                    "x":      lon,
                    "y":      lat,
                    "radius": radius,
                    "size":   15,   # API 상한
                },
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json().get("meta", {}).get("total_count", 0)
        except Exception as e:
            print(f"[enrich] fetch_poi({category_code}) 실패: {e}")
            return 0

    return {key: _fetch_count(code, radius) for code, radius, key in _TARGETS}


# ──────────────────────────────────────────────────────────────
# 3. Solar LLM — 수집된 정보 → 입지 설명문 생성
# ──────────────────────────────────────────────────────────────

def _stub_text(
    address:         str,
    green_ratio:     float,
    building_ratio:  float,
    poi:             dict,
    similarity:      float,
) -> str:
    """
    Solar LLM 호출 실패 시 반환하는 템플릿 기반 fallback 문장.
    LLM api 호출 실패시에만 동작하는 비상 로직
    """
    parts = []

    if address:
        parts.append(f"{address} 일대입니다.")

    # 녹지
    if green_ratio >= 0.15:
        parts.append("녹지가 풍부해 쾌적한 환경을 갖추고 있습니다.")
    elif green_ratio >= 0.05:
        parts.append("적당한 녹지를 보유하고 있습니다.")
    else:
        parts.append("도심형 저녹지 지역입니다.")

    # 건물밀도
    if building_ratio >= 0.4:
        parts.append("건물 밀도가 높은 고밀도 주거·상업 혼합 지역입니다.")
    elif building_ratio >= 0.2:
        parts.append("중밀도 주거 지역입니다.")
    else:
        parts.append("저밀도 주거 환경입니다.")

    # 교통
    if poi.get("station_count", 0) >= 1:
        parts.append(f"도보권 내 지하철역 {poi['station_count']}개역으로 교통이 편리합니다.")
    elif poi.get("bus_count", 0) >= 2:
        parts.append(f"버스정류장 {poi['bus_count']}곳이 인근에 있어 대중교통 이용이 가능합니다.")

    # 학세권
    total_school = poi.get("school_count", 0) + poi.get("daycare_count", 0)
    if total_school >= 2:
        parts.append(f"학교·어린이집 등 교육시설이 {total_school}곳 인근에 있어 육아 환경이 좋습니다.")

    # 의료
    if poi.get("hospital_count", 0) >= 1 or poi.get("pharmacy_count", 0) >= 1:
        parts.append("병원·약국이 가까이 있어 의료 접근성이 양호합니다.")

    # 편의
    if poi.get("mart_count", 0) >= 1:
        parts.append("대형마트가 인근에 위치해 장보기가 편리합니다.")
    elif poi.get("convenience_count", 0) >= 2:
        parts.append(f"편의점 {poi['convenience_count']}곳이 가까이 있습니다.")

    # 상권
    total_food = poi.get("cafe_count", 0) + poi.get("restaurant_count", 0)
    if total_food >= 5:
        parts.append(f"카페·음식점 등 상권이 활발한 지역입니다.")

    # 공원
    if poi.get("park_count", 0) >= 1:
        parts.append(f"공원이 {poi['park_count']}곳 인근에 있어 산책·여가 환경이 좋습니다.")

    parts.append(f"(입지 유사도: {similarity:.2f})")
    return " ".join(parts)


def generate_location_text(
    address:        str,
    green_ratio:    float,
    building_ratio: float,
    poi:            dict,
    similarity:     float,
) -> str:
    """
    Solar LLM(Upstage solar-1-mini-chat)으로 2~3문장 한국어 입지 설명문을 생성합니다.

    프롬프트에 픽셀 분석 결과(녹지율·건물밀도) + 카카오 API 전체 POI 통계 + 유사도를
    포함해 실제 거주자 체감 관점의 입지 특성을 자연어로 서술합니다.

    실패(API 키 없음 / 타임아웃 / 파싱 오류) 시 _stub_text() fallback 반환.
    """
    if not _UPSTAGE_API:
        return _stub_text(address, green_ratio, building_ratio, poi, similarity)

    prompt = (
        f"다음은 서울의 한 위성 이미지 타일에 대한 분석 결과입니다.\n"
        f"- 주소: {address if address else '미확인'}\n"
        f"- 입지 유사도 점수: {similarity:.3f}\n"
        f"\n[환경]\n"
        f"- 녹지율: {green_ratio * 100:.1f}%\n"
        f"- 건물밀도: {building_ratio * 100:.1f}%\n"
        f"\n[역세권 — 교통 접근성]\n"
        f"- 도보권 지하철역 수 (500m): {poi.get('station_count', 0)}개\n"
        f"\n[학세권 — 교육 인프라]\n"
        f"- 인근 학교 수 (500m): {poi.get('school_count', 0)}개\n"
        f"- 인근 어린이집·유치원 수 (500m): {poi.get('daycare_count', 0)}개\n"
        f"\n[편의 인프라]\n"
        f"- 인근 대형마트 수 (1km): {poi.get('mart_count', 0)}개\n"
        f"- 인근 편의점 수 (300m): {poi.get('convenience_count', 0)}개\n"
        f"\n[의료 인프라]\n"
        f"- 인근 병원 수 (500m): {poi.get('hospital_count', 0)}개\n"
        f"- 인근 약국 수 (300m): {poi.get('pharmacy_count', 0)}개\n"
        f"\n[상권 활성도]\n"
        f"- 인근 카페 수 (300m): {poi.get('cafe_count', 0)}개\n"
        f"- 인근 음식점 수 (300m): {poi.get('restaurant_count', 0)}개\n"
        f"\n위 정보를 바탕으로 이 지역의 입지 특성을 자연스러운 한국어로 설명해주세요. "
        f"주어진 정보를 모두 활용할 필요는 없습니다. 정보를 활용해서 특징을 정리한 서술을 해주세요. "
        f"주소지를 출력에 포함하지 말고 지역에 대한 서술만 포함하세요."
        f"숫자를 그대로 나열하지 말고 실제 거주자의 체감 관점에서 서술해주세요."
        f"문장은 반드시 '~습니다' 체로 통일해주세요. "
        f"'이 지역은', '이곳은' 같은 주어로 시작하지 말고 바로 입지 특성부터 서술해주세요."
        f"반드시 2~3문장 이내, 100자 이내로 간결하게 작성해주세요."
    )

    try:
        resp = requests.post(
            "https://api.upstage.ai/v1/solar/chat/completions",
            headers={
                "Authorization": f"Bearer {_UPSTAGE_API}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       "solar-1-mini-chat",
                "messages":    [{"role": "user", "content": prompt}],
                "max_tokens":  150,
                "temperature": 0.7,
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(f"[enrich] Solar LLM 호출 실패: {e} → fallback 사용")
        return _stub_text(address, green_ratio, building_ratio, poi, similarity)


# ──────────────────────────────────────────────────────────────
# 4. 통합 — enrich_results()
# ──────────────────────────────────────────────────────────────

def enrich_results(
    raw_results:    list[dict],
    *,
    address_prefix: str | None = None,
    target_count:   int | None = None,
) -> list[dict]:
    """
    search_step1() / search_step2() 의 raw 결과 리스트를 받아
    픽셀 분석 · 카카오 API · Solar LLM 정보를 추가한 enriched 결과를 반환합니다.

    처리 순서 (결과 1건당):
        1. reverse_geocode(lat, lon)
               → address (한국어 주소)         (카카오 API, ~0.2s)
               address_prefix 가 주어졌는데 주소의 행정구역 토큰(공백으로 분리한
               단어들) 중에 이 값이 없으면 — 예: "서울 광진구 자양동 97-5"처럼
               기대 구가 빠져 있는 경우 (수집 bbox가 행정구역 경계와 어긋나
               인접 구가 섞여 들어온 경우) — 이 결과는 건너뛰고 raw_results의
               다음 순위 후보로 대체합니다. 카카오 주소는 "서울 성동구 ..." /
               "서울특별시 성동구 ..."처럼 구 이름이 문자열 맨 앞이 아니라
               시/도 다음 토큰으로 오므로 단순 startswith 가 아닌 토큰 매칭을
               사용합니다. — POI/LLM 호출 전에 걸러내어 불필요한 외부 API
               비용을 줄입니다.
        2. compute_ratios(image_path)
               → green_ratio, building_ratio  (픽셀 분석, ~1ms)
        3. fetch_poi_summary(lat, lon)
               → station_count, cafe_count    (카카오 API, ~0.3s)
        4. generate_location_text(...)
               → text (입지 설명문)            (Solar LLM, ~0.3s)

    Args:
        raw_results:    search_step1() 또는 search_step2() 반환값.
            [{rank, tile_id, lat, lon, image_path, similarity}, ...]
        address_prefix: 지정하면 reverse_geocode 주소의 행정구역 토큰 중에
                        이 값이 포함된 결과만 채택합니다. (예: "성동구")
                        주소가 "서울 성동구 ..." 형식이라 문자열 접두사가
                        아닌 공백 분리 토큰 단위로 비교합니다.
                        STEP 1처럼 검색 대상 구역이 고정된 경우, 타일 수집용
                        bbox가 행정구역 경계와 완전히 일치하지 않아 인접 구
                        (예: 광진구) 타일이 섞여 들어오는 것을 걸러낼 때 사용합니다.
                        주소 조회에 실패해 빈 문자열이 반환된 경우는 판단할 수
                        없으므로 필터링하지 않고 통과시킵니다.
        target_count:   반환할 최종 결과 수 상한. address_prefix와 함께 사용하면
                        필터링으로 제외된 자리를 raw_results의 다음 순위 후보로
                        채워 최대 target_count개를 모을 때까지 진행합니다.
                        지정하지 않으면 raw_results 전체를 처리합니다.
                        (반환 결과의 rank는 최종 채택 순서대로 1..N 으로 재부여됩니다)

    Returns:
        enriched_results: app_v6.py 호환 형식.
            [{
                rank,           # int
                tile_id,        # str  (내부 식별자, UI 에서 image_path 키로도 사용)
                lat,            # float
                lon,            # float
                image_path,     # str   (절대경로)
                similarity,     # float (코사인 유사도)
                label,          # str   (한국어 주소 또는 tile_id fallback)
                text,           # str   (Solar LLM 생성 입지 설명문)
                green_ratio,    # float [0,1]
                building_ratio, # float [0,1]
            }, ...]

    각 단계가 실패해도 나머지 단계는 계속 진행됩니다.
    (카카오 API 키 없음 → label=tile_id, poi=0 → Solar LLM fallback 문장)
    """
    enriched = []

    for r in raw_results:
        if target_count is not None and len(enriched) >= target_count:
            break   # 목표 개수를 채웠으면 나머지 후보는 처리하지 않음

        image_path  = r["image_path"]
        lat, lon    = r["lat"], r["lon"]
        similarity  = r["similarity"]

        # ── 1. 카카오 reverse geocode → 주소 (행정구역 필터링 선행) ──
        # 카카오 주소는 "서울 성동구 옥수동 490-6" / "서울특별시 성동구 왕십리로 80"
        # 형식으로, 구 이름이 맨 앞이 아니라 시/도 다음 토큰으로 옵니다.
        # 따라서 문자열 접두사가 아니라 공백으로 분리한 토큰 단위로 비교합니다.
        address = reverse_geocode(lat, lon)
        if address_prefix and address and address_prefix not in address.split():
            print(
                f"[enrich] 행정구역 불일치로 제외: {r['tile_id']} → '{address}' "
                f"(기대 행정구역 '{address_prefix}') — 다음 순위 후보로 대체"
            )
            continue
        label = address if address else r["tile_id"]   # 조회 실패 시 tile_id 표시

        # ── 2. 픽셀 분석 ──────────────────────────────────────
        green_ratio, building_ratio = compute_ratios(image_path)

        # ── 3. 카카오 POI 통계 ────────────────────────────────
        poi = fetch_poi_summary(lat, lon)

        # ── 4. Solar LLM 입지 설명문 생성 ────────────────────
        text = generate_location_text(
            address        = address,
            green_ratio    = green_ratio,
            building_ratio = building_ratio,
            poi            = poi,
            similarity     = similarity,
        )

        enriched.append({
            **r,                            # rank, tile_id, lat, lon, image_path, similarity 보존
            "label":          label,
            "text":           text,
            "green_ratio":    green_ratio,
            "building_ratio": building_ratio,
        })

    # 필터링/백필로 원본 FAISS 순위에 빈자리가 생길 수 있으므로 최종 채택 순서 기준 1..N 재부여
    if address_prefix:
        for i, item in enumerate(enriched, start=1):
            item["rank"] = i

    return enriched


# ──────────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from pipeline.search import search_step1

    print("=" * 60)
    print("[enrich 단독 테스트]")
    print("=" * 60)

    raw      = search_step1("숲세권 저밀도 주거지", top_k=3)
    enriched = enrich_results(raw)

    for r in enriched:
        print(f"\n#{r['rank']}  {r['tile_id']}  유사도={r['similarity']:.4f}")
        print(f"  주소  : {r['label']}")
        print(f"  녹지율: {r['green_ratio']:.2%}  건물밀도: {r['building_ratio']:.2%}")
        print(f"  설명  : {r['text']}")