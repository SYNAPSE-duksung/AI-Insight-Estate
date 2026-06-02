# collect_search_tiles.py
import os
import asyncio
import aiohttp
import math
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── 1. 브이월드 API 및 기본 네트워크 설정 ───────────────────────────
VWORLD_API_KEY = os.getenv("VWORLD_API", "")
if not VWORLD_API_KEY:
    print("⚠️ 경고: .env 파일에 VWORLD_API 키가 설정되지 않았습니다.")

ZOOM = 18

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://map.vworld.kr/",
}

# ─── 2. 수집 대상 자치구 및 동 지오 박스(BBOX) 명세 ───────────────────────────
# 위성 이미지 매칭용 타 지역들의 행정 구역과 랜드마크를 정밀 표적화한 좌표 정보입니다.
REGIONS_BBOX = {
    "광진구_자양동": {
        "min_lat": 37.5250, "max_lat": 37.5400,
        "min_lon": 127.0600, "max_lon": 127.0850
    },
    "송파구_가락_문정동": {
        "min_lat": 37.4800, "max_lat": 37.5000,
        "min_lon": 127.1100, "max_lon": 127.1350
    },
    "중구_신당_황학동": {
        "min_lat": 37.5450, "max_lat": 37.5700,
        "min_lon": 127.0050, "max_lon": 127.0250
    }
}
# ─── 3. 타일 수학 계산식 ───────────────────────────────────────────────
def latlon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(math.radians(lat)) + (1.0 / math.cos(math.radians(lat)))) / math.pi) / 2.0 * n)
    return x, y

def tile_to_latlon(x, y, zoom):
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon

def get_tile_list(bbox, zoom):
    x_min, y_max = latlon_to_tile(bbox["min_lat"], bbox["min_lon"], zoom)
    x_max, y_min = latlon_to_tile(bbox["max_lat"], bbox["max_lon"], zoom)
    x_start, x_end = min(x_min, x_max), max(x_min, x_max)
    y_start, y_end = min(y_min, y_max), max(y_min, y_max)
    
    tiles = []
    for x in range(x_start, x_end + 1):
        for y in range(y_start, y_end + 1):
            tiles.append((x, y))
    return tiles

# ─── 4. 비동기 다운로드 엔진 (재시도 및 백오프 메커니즘 탑재) ──────────────
async def download_tile(session, sem, x, y, zoom, save_path):
    url = f"https://api.vworld.kr/req/wmts/1.0.0/{VWORLD_API_KEY}/Satellite/{zoom}/{y}/{x}.jpeg"
    
    if save_path.exists() and save_path.stat().st_size > 1024:
        return True, "SKIPPED"
        
    max_retries = 3  # 연결이 끊겼을 때 최대 3번 재시도
    async with sem:
        for attempt in range(max_retries):
            try:
                # 타일별 다운로드 간에 아주 미세한 간격을 두어 방화벽 우회
                await asyncio.sleep(0.05) 
                
                async with session.get(url, timeout=10) as r:
                    if r.status == 200:
                        data = await r.read()
                        if len(data) < 2048:
                            return False, f"Empty Content ({len(data)}B)"
                        
                        with open(save_path, "wb") as f:
                            f.write(data)
                        return True, "SUCCESS"
                    elif r.status == 403:
                        return False, "API_KEY_ERROR_OR_BLOCKED"
                    else:
                        # 5xx 서버 에러 등은 재시도 유도
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1 * (attempt + 1))
                            continue
                        return False, f"HTTP_{r.status}"
            except (aiohttp.ClientError, asyncio.TimeoutError):
                # 10054 강제 종료 발생 시 대기 후 재시도
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                return False, "CONNECTION_RESET_OR_TIMEOUT"
            except Exception as e:
                return False, f"UNKNOWN_ERROR: {str(e)}"
    return False, "MAX_RETRIES_EXCEEDED"

# ─── 5. 메인 조정 프로세스 ───────────────────────────────────────────
async def collect_region_tiles(region_name, bbox):
    base_save_dir = Path(f"data/raw/search_tiles/{region_name}")
    base_save_dir.mkdir(parents=True, exist_ok=True)
    
    meta_dir = Path("data/processed")
    meta_dir.mkdir(parents=True, exist_ok=True)
    
    tiles = get_tile_list(bbox, ZOOM)
    print(f"📡 [{region_name}] 범위 연산 완료 (대상 타일 수: {len(tiles)}장)")
    
    tile_meta = []
    for x, y in tiles:
        lat, lon = tile_to_latlon(x, y, ZOOM)
        tile_meta.append({
            "region": region_name,
            "x": x, "y": y,
            "lat": lat, "lon": lon,
            "tile_path": str(base_save_dir / f"tile_{ZOOM}_{x}_{y}.jpg")
        })
        
    meta_file = meta_dir / f"tile_coords_{region_name}.jsonl"
    with open(meta_file, "w", encoding="utf-8") as f:
        for item in tile_meta:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    # 윈도우 환경 및 방화벽 크래시 방지를 위한 커넥터 튜닝
    # 동시 연결 수를 4개로 줄이고(limit=4), force_close=False로 세션을 재사용하여 안정성 극대화
    sem = asyncio.Semaphore(4)
    connector = aiohttp.TCPConnector(limit=4, force_close=False, enable_cleanup_closed=True)
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        tasks = []
        for item in tile_meta:
            tile_x, tile_y = item["x"], item["y"]
            save_path = Path(item["tile_path"])
            tasks.append(download_tile(session, sem, tile_x, tile_y, ZOOM, save_path))
            
        print(f"[{region_name}] 다운로드 파이프라인 가동 중...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, tuple):
                success, msg = res
                if success:
                    if msg == "SKIPPED":
                        skip_count += 1
                    else:
                        success_count += 1
                else:
                    fail_count += 1
            else:
                # 익셉션이 터지더라도 전체 루프가 다운되지 않도록 예외 처리
                fail_count += 1
                
    print(f"[{region_name}] 완료: {success_count}건 / 스킵: {skip_count}건 / 실패: {fail_count}건\n")

async def main():
    print("AI-Insight Estate 타지역 입지 매칭 위성 이미지 수집 시스템 가동 (안정화 버전)\n")
    if not VWORLD_API_KEY:
        print("오류: VWORLD_API 키가 공백입니다. 환경 변수를 확인하세요.")
        return
        
    for region, bbox in REGIONS_BBOX.items():
        await collect_region_tiles(region, bbox)
        # 지역 교체 시 서버가 숨 고를 시간을 줌
        await asyncio.sleep(3)
        
    print("[모든 타겟 권역] 위성 이미지 타일 수집이 안전하게 완료되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())