# collect_tiles.py
import os
import asyncio, aiohttp, math, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── 설정 ───────────────────────────────────────────
VWORLD_API_KEY = os.getenv("VWORLD_API", "")

SAVE_DIR = Path("data/raw/tiles")
META_DIR = Path("data/processed")

SEONGDONG_BBOX = {
    "min_lat": 37.5300, "max_lat": 37.5700,
    "min_lon": 127.0150, "max_lon": 127.0800,
}
ZOOM = 18

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://map.vworld.kr/",
}
# ────────────────────────────────────────────────────

def latlon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(
        math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))
    ) / math.pi) / 2.0 * n)
    return x, y

def tile_to_latlon(x, y, zoom):
    n = 2 ** zoom
    lon = (x + 0.5) / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n)))
    return round(math.degrees(lat_rad), 6), round(lon, 6)

def get_tile_list(bbox, zoom):
    x_min, y_min = latlon_to_tile(bbox["max_lat"], bbox["min_lon"], zoom)
    x_max, y_max = latlon_to_tile(bbox["min_lat"], bbox["max_lon"], zoom)
    return [(x, y)
            for x in range(x_min, x_max + 1)
            for y in range(y_min, y_max + 1)]

async def fetch_tile(session, x, y, zoom, sem):
    path = SAVE_DIR / f"tile_{zoom}_{x}_{y}.jpg"
    if path.exists():
        return "cached"

    url = (f"https://api.vworld.kr/req/wmts/1.0.0/"
           f"{VWORLD_API_KEY}/Satellite/{zoom}/{y}/{x}.jpeg")

    async with sem:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                content = await r.read()
                # Content-Type 체크 제거 — 크기로만 판별
                if r.status == 200 and len(content) > 1000:
                    path.write_bytes(content)
                    return "ok"
                else:
                    return f"fail:{r.status}:size={len(content)}"
        except Exception as e:
            return f"error:{type(e).__name__}"

async def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)

    tiles = get_tile_list(SEONGDONG_BBOX, ZOOM)
    print(f"수집 대상: {len(tiles)}장")

    # 타일 좌표 → 위경도 매핑 저장
    tile_meta = [
        {
            "x": x, "y": y,
            "lat": tile_to_latlon(x, y, ZOOM)[0],
            "lon": tile_to_latlon(x, y, ZOOM)[1],
            "tile_path": str(SAVE_DIR / f"tile_{ZOOM}_{x}_{y}.jpg"),
        }
        for x, y in tiles
    ]
    with open(META_DIR / "tile_coords.jsonl", "w", encoding="utf-8") as f:
        for item in tile_meta:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"좌표 매핑 저장: {len(tile_meta)}개")

    # 비동기 수집
    sem = asyncio.Semaphore(10)
    connector = aiohttp.TCPConnector(limit=10, force_close=True)

    async with aiohttp.ClientSession(
        headers=HEADERS, connector=connector
    ) as session:
        tasks = [fetch_tile(session, x, y, ZOOM, sem) for x, y in tiles]
        results = await asyncio.gather(*tasks)

    ok     = results.count("ok")
    cached = results.count("cached")
    failed = [r for r in results if r.startswith(("fail", "error"))]

    print(f"\n=== 수집 완료 ===")
    print(f"신규:   {ok}장")
    print(f"캐시:   {cached}장")
    print(f"실패:   {len(failed)}장")
    if failed:
        print("실패 샘플:")
        for r in failed[:5]:
            print(f"  {r}")

if __name__ == "__main__":
    asyncio.run(main())