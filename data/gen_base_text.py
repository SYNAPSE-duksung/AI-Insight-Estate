import asyncio
import aiohttp
import json
import math
import os
from pathlib import Path
from dotenv import load_dotenv

# --- .env 파일 로드 ---
load_dotenv()

# --- 설정 ---
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
if not KAKAO_API_KEY:
    raise ValueError(".env 파일에 KAKAO_API_KEY를 설정해주세요.")

# 입력 파일: 위경도를 계산할 수 있는 파일명(tile_z_x_y.jpg)이 포함된 메타데이터 또는 리스트
INPUT_FILE = Path("data/raw/tiles/raw_tiles_list.jsonl") 
# 출력 파일: 시설물 카운트 텍스트가 추가된 메타데이터
OUTPUT_FILE = Path("data/raw/tiles/metadata.jsonl")

# 카카오 API 카테고리 그룹 코드 매핑
CATEGORY_MAP = {
    "FD6": "음식점",
    "CE7": "카페",
    "CS2": "편의점",
    "PM9": "약국",
    "BK9": "금융시설",
    "AG2": "부동산",
    "PO3": "공공기관",
    "AT4": "문화시설",
    "AD5": "숙박시설",
    "SC4": "학교",
    "PS3": "유치원/어린이집",
    "AC5": "학원",
    "PK6": "주차장/공원",
    "HP8": "의료시설"
}

def tile_to_latlon(zoom, x, y):
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

async def count_facilities(session, lat, lon, sem):
    """지정된 좌표 반경 50m 내의 시설물 개수를 집계합니다."""
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    facility_counts = {}
    
    async def fetch_category_count(code, name):
        url = f"https://dapi.kakao.com/v2/local/search/category.json?category_group_code={code}&x={lon}&y={lat}&radius=50"
        async with sem:
            try:
                async with session.get(url, headers=headers, timeout=5) as r:
                    if r.status == 200:
                        data = await r.json()
                        count = data['meta']['total_count']
                        if count > 0:
                            return name, count
            except Exception as e:
                pass
        return name, 0

    tasks = [fetch_category_count(code, name) for code, name in CATEGORY_MAP.items()]
    results = await asyncio.gather(*tasks)
    
    for name, count in results:
        if count > 0:
            facility_counts[name] = count
            
    return facility_counts

def generate_caption(facility_counts):
    """집계된 시설물 데이터를 바탕으로 캡션을 생성합니다."""
    if not facility_counts:
        return "특별한 상업/공공 시설이 식별되지 않는 일반 도로, 녹지 또는 주택/건물 지붕의 위성 사진"
    
    # 시설물 개수 기준으로 내림차순 정렬
    sorted_facilities = sorted(facility_counts.items(), key=lambda item: item[1], reverse=True)
    
    # "음식점 37개, 숙박시설 3개..." 형태의 문자열 생성
    facilities_str = ", ".join([f"{name} {count}개" for name, count in sorted_facilities])
    
    return f"{facilities_str} 시설이 밀집된 소규모 건물 및 인접 구역의 위성 사진"

async def process_tile(session, item, sem, progress):
    img_filename = item.get("file_name", "")
    
    try:
        parts = img_filename.replace(".jpg", "").split("_")
        zoom, x, y = int(parts[1]), int(parts[2]), int(parts[3])
        lat, lon = tile_to_latlon(zoom, x, y)
    except Exception as e:
        progress['done'] += 1
        return item

    # 시설물 집계 및 캡션 생성
    facility_counts = await count_facilities(session, lat, lon, sem)
    caption = generate_caption(facility_counts)
    
    item["text"] = caption
    
    progress['done'] += 1
    if progress['done'] % 50 == 0:
        print(f" -> [{progress['done']}/{progress['total']}] 처리 완료")

    return item

async def main():
    if not INPUT_FILE.exists():
        print(f"⚠️ 원본 파일이 없습니다: {INPUT_FILE}")
        print("💡 임시 데이터를 생성하여 테스트합니다.")
        # 파일이 없을 경우 테스트용 데이터 생성
        test_records = [
            {"file_name": "tile_18_223561_101512.jpg"},
            {"file_name": "tile_18_223561_101513.jpg"},
            {"file_name": "tile_18_223561_101525.jpg"} # 시설이 없을 법한 곳
        ]
    else:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            test_records = [json.loads(line) for line in f.readlines()]

    print(f"총 {len(test_records)}장 타일: 카카오 API 기반 기초 텍스트 데이터 추출 시작...")
    progress = {'done': 0, 'total': len(test_records)}
    
    # 카카오 API 호출 제한을 고려하여 동시 접속 수 제한
    sem = asyncio.Semaphore(10) 
    connector = aiohttp.TCPConnector(limit=10, force_close=True)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [process_tile(session, rec, sem, progress) for rec in test_records]
        results = await asyncio.gather(*tasks)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for res in results:
            if res: 
                f.write(json.dumps(res, ensure_ascii=False) + "\n")

    print(f"\n🎉 완료! 결과가 {OUTPUT_FILE}에 저장되었습니다.")
    print("이 파일을 Solar LLM 2차 가공 코드의 INPUT_FILE로 사용하시면 됩니다.")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())