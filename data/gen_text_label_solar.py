import asyncio
import aiohttp
import json
import os
import math
from pathlib import Path
from dotenv import load_dotenv

# --- .env 파일 로드 ---
load_dotenv()

# --- 설정 ---
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
LLM_API_KEY = os.getenv("LLM_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "solar-mini") 
LLM_API_URL = "https://api.upstage.ai/v1/chat/completions" 

INPUT_FILE = Path("data/raw/tiles/metadata.jsonl") 
OUTPUT_FILE = Path("data/raw/tiles/metadata_solar_test.jsonl")

SYSTEM_PROMPT = """
당신은 AI 비전 모델(CLIP) 학습용 부동산 이미지 데이터셋을 구축하는 수석 데이터 라벨러입니다.
제공된 주소, 랜드마크, 시설물 개수 데이터를 바탕으로 해당 구역(반경 50m)의 시각적 입지 특성을 정확히 묘사하는 캡션을 작성하세요.

[🚨 절대 금지 사항 - 위반 시 데이터 폐기됨]
1. "제공된 정보에 따르면", "종합하면", "판단됩니다", "추정됩니다" 같은 서두나 분석 과정을 절대 쓰지 말 것.
2. 괄호()를 사용한 부연 설명, 해설, 참고 사항을 절대 덧붙이지 말 것.
3. 오직 최종 캡션 텍스트만 출력할 것.

[작성 규칙]
1. 길이는 반드시 1~2문장으로 압축하여 군더더기 없이 간결하게 작성할 것.
2. 시설 개수를 단순 나열하지 말고 '역세권 상가', '먹자골목', '생활밀착형 주거지 상권' 등 동네의 성격으로 요약할 것.
3. 랜드마크(역, 학교 등)가 있다면 해당 랜드마크의 영향을 받는 상권임을 명시할 것.
4. 반드시 마지막은 "~위성 사진입니다." 또는 "~입지입니다."로 끝맺을 것.

[출력 예시]
입력: 서울특별시 중구 신당동 / 랜드마크: 청구역 / 시설: 음식점 21개, 카페 6개
출력: 청구역을 중심으로 음식점과 카페가 고밀도로 집적된 역세권 특화 상권입니다. 활발한 유동인구와 상업 시설이 두드러지는 도심 번화가의 위성 사진입니다.
"""

def tile_to_latlon(zoom, x, y):
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

async def get_micro_address(session, lat, lon):
    url = f"https://dapi.kakao.com/v2/local/geo/coord2address.json?x={lon}&y={lat}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    addr_info = {"dong": "성동구 일대", "road": ""}
    try:
        async with session.get(url, headers=headers, timeout=5) as r:
            if r.status == 200:
                data = await r.json()
                if data.get('documents'):
                    doc = data['documents'][0]
                    if doc.get('address'):
                        addr_info["dong"] = doc['address'].get('region_3depth_name', '')
                    if doc.get('road_address'):
                        addr_info["road"] = doc['road_address'].get('road_name', '')
    except: pass
    return addr_info

async def get_landmark(session, lat, lon, sem):
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    landmark_categories = ["MT1", "SW8", "SC4", "PO3"]
    
    async def fetch_category(code):
        url = f"https://dapi.kakao.com/v2/local/search/category.json?category_group_code={code}&x={lon}&y={lat}&radius=50"
        async with sem:
            try:
                async with session.get(url, headers=headers, timeout=5) as r:
                    if r.status == 200:
                        data = await r.json()
                        if data.get('documents'):
                            return data['documents'][0]['place_name']
            except: pass
        return None

    tasks = [fetch_category(code) for code in landmark_categories]
    results = await asyncio.gather(*tasks)
    for res in results:
        if res: return res
    return None

async def process_row_with_llm(session, item, sem, progress):
    img_filename = item.get("file_name", "")
    original_text = item.get("text", "")

    if "식별되지 않는" in original_text:
        progress['done'] += 1
        return item

    try:
        parts = img_filename.replace(".jpg", "").split("_")
        zoom, x, y = int(parts[1]), int(parts[2]), int(parts[3])
        lat, lon = tile_to_latlon(zoom, x, y)
    except Exception as e:
        progress['done'] += 1
        return item

    addr_task = get_micro_address(session, lat, lon)
    landmark_task = get_landmark(session, lat, lon, sem)
    addr_info, landmark = await asyncio.gather(addr_task, landmark_task)

    context_str = f"- 법정동: {addr_info['dong']}"
    if addr_info['road']: context_str += f"\n- 도로명: {addr_info['road']}"
    if landmark: context_str += f"\n- 🎯 반경 내 주요 랜드마크: {landmark}"

    user_prompt = f"""
[위치 및 랜드마크 힌트]
{context_str}

[내부 식별 시설]
{original_text}

위 힌트를 바탕으로 이곳이 대형 건물 내부인지, 랜드마크 주변 상권인지, 일반 길거리 상권인지 파악하여 입지를 서술해줘.
"""

    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL_NAME, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}], "temperature": 0.2, "max_tokens": 200}

    async with sem:
        try:
            async with session.post(LLM_API_URL, headers=headers, json=payload, timeout=12) as r:
                if r.status == 200:
                    res = await r.json()
                    item['text'] = res['choices'][0]['message']['content'].strip()
        except:
            pass 

    progress['done'] += 1
    print(f" -> [{progress['done']}/{progress['total']}] {img_filename} 처리 완료")

    return item

async def main():
    if not INPUT_FILE.exists():
        print(f"⚠️ 원본 데이터가 없습니다: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        all_records = [json.loads(line) for line in f.readlines()]

    test_records = all_records

    print(f"총 {len(test_records)}장 타일: {MODEL_NAME} 라벨링 시작...")
    progress = {'done': 0, 'total': len(test_records)}
    
    sem = asyncio.Semaphore(5)
    connector = aiohttp.TCPConnector(limit=5, force_close=True)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [process_row_with_llm(session, rec, sem, progress) for rec in test_records]
        results = await asyncio.gather(*tasks)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for res in results:
            if res: f.write(json.dumps(res, ensure_ascii=False) + "\n")

    print(f"\n🎉완료! 결과가 {OUTPUT_FILE}에 저장되었습니다.")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())