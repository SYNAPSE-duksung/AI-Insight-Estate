"""
build_vector_db.py
──────────────────
파인튜닝된 CLIP 모델을 사용해 두 개의 FAISS 인덱스를 독립적으로 구축합니다.

  ① 성동구 인덱스       →  data/processed/search_target/faiss_seongdong.index   (STEP 1용)
  ② 3개 구역 통합 인덱스 →  data/processed/search_target/faiss_3districts.index  (STEP 2용)

파일명 규칙:
  tile_{zoom}_{x}_{y}.jpg
  예: tile_18_223561_101512.jpg
  → tile_id = "SD_0001" 등 (prefix + 순번)
  → 위경도는 슬리피맵 타일 좌표(zoom, x, y)에서 역산

실행:
  python data/build_vector_db.py

결과:
  faiss_{key}.index — FAISS 벡터 인덱스
  tile_ids_{key}.npy — 인덱스 순번 ↔ tile_id 매핑
  metadata_{key}.db — SQLite 메타데이터
"""

import os
import math
import sqlite3

import numpy as np
import faiss
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from tqdm import tqdm
from peft import PeftModel


# ──────────────────────────────────────────────────────────────
# 1. 지역별 폴더 설정 (경로를 여기서만 관리)
# ──────────────────────────────────────────────────────────────

# 각 지역 설정: (폴더 절대/상대 경로, district 키, tile_id 프리픽스, 자치구명)
REGION_CONFIGS = [
    {
        "folder":       "data/raw/tiles",  # 성동구(파인튜닝 데이터와 동일)
        "district_key": "seongdong",
        "prefix":       "SD",
        "gu":           "seongdonggu",
        "step":         1,          # STEP 1 전용 인덱스로 분류
    },
    {
        "folder":       "data/raw/search_tiles/gwangjin_jayang",
        "district_key": "jayangdong",
        "prefix":       "GJ",
        "gu":           "gwangjingu",
        "step":         2,          # STEP 2 통합 인덱스로 분류
    },
    {
        "folder":       "data/raw/search_tiles/songpa_garak",
        "district_key": "garakdong",
        "prefix":       "SP",
        "gu":           "songpagu",
        "step":         2,
    },
    {
        "folder":       "data/raw/search_tiles/junggu_sindang",
        "district_key": "sindangdong",
        "prefix":       "JG",
        "gu":           "junggu",
        "step":         2,
    },
]

# 출력 경로
OUT_DIR      = "data/processed/search_target_v2"
BASE_MODEL_PATH   = "checkpoints/clip_finetuned_v1"
LORA_ADAPTER_PATH = "checkpoints/clip_finetuned_v2"
BATCH_SIZE   = 32
IMG_EXTS     = {".jpg", ".jpeg", ".png"}


# ──────────────────────────────────────────────────────────────
# 2. 유틸 함수
# ──────────────────────────────────────────────────────────────

def tile_xy_to_latlon(zoom: int, x: int, y: int) -> tuple[float, float]:
    """
    슬리피맵 타일 좌표 (zoom, x, y) → 타일 중심점 (위도, 경도) 변환.
    타일의 좌상단 좌표를 구한 뒤 타일 크기의 절반을 더해 중심점을 구합니다.
    """
    n = 2 ** zoom
    # 타일 좌상단 경도
    lon_left  = x / n * 360.0 - 180.0
    lon_right = (x + 1) / n * 360.0 - 180.0
    lon = (lon_left + lon_right) / 2.0
    # 타일 좌상단·우하단 위도 (메르카토르 역산)
    lat_top    = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lat_bottom = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    lat = (lat_top + lat_bottom) / 2.0
    return round(lat, 6), round(lon, 6)


def parse_tile_filename(filename: str) -> tuple[int, int, int] | None:
    """
    파일명에서 (zoom, x, y)를 파싱합니다.
    규칙: tile_{zoom}_{x}_{y}.ext
    예:   tile_18_223561_101512.jpg  →  (18, 223561, 101512)
    파싱 실패 시 None 반환.
    """
    stem = os.path.splitext(filename)[0]   # "tile_18_223561_101512"
    parts = stem.split("_")               # ["tile", "18", "223561", "101512"]
    if len(parts) != 4 or parts[0] != "tile":
        return None
    try:
        return int(parts[1]), int(parts[2]), int(parts[3])
    except ValueError:
        return None


def collect_image_paths(folder: str) -> list[str]:
    """폴더 내 이미지 파일 경로를 정렬해서 반환합니다."""
    if not os.path.isdir(folder):
        return []
    return sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in IMG_EXTS
    )


def load_clip_model(device: str):
    fallback = "openai/clip-vit-base-patch32"
    base_exists = os.path.exists(BASE_MODEL_PATH)
    lora_exists = os.path.exists(LORA_ADAPTER_PATH)

    if base_exists and lora_exists:
        print(f"베이스 모델 로드: {BASE_MODEL_PATH}")
        model = CLIPModel.from_pretrained(BASE_MODEL_PATH, torch_dtype=torch.float32).to(device)
        print(f"LoRA 어댑터 적용: {LORA_ADAPTER_PATH}")
        model = PeftModel.from_pretrained(model, LORA_ADAPTER_PATH)
        model = model.merge_and_unload()
        processor = CLIPProcessor.from_pretrained(BASE_MODEL_PATH)
    elif base_exists:
        print(f"v1 가중치 로드 (LoRA 없음): {BASE_MODEL_PATH}")
        model     = CLIPModel.from_pretrained(BASE_MODEL_PATH).to(device)
        processor = CLIPProcessor.from_pretrained(BASE_MODEL_PATH)
    else:
        print(f"파인튜닝 모델 없음 → 기본 모델 사용: {fallback}")
        model     = CLIPModel.from_pretrained(fallback).to(device)
        processor = CLIPProcessor.from_pretrained(fallback)

    model.eval()
    return model, processor


# ──────────────────────────────────────────────────────────────
# 3. 임베딩 추출
# ──────────────────────────────────────────────────────────────

def extract_embeddings(
    image_paths: list[str],
    model: CLIPModel,
    processor: CLIPProcessor,
    device: str,
    clip_dim: int,
) -> np.ndarray:
    """
    이미지 경로 리스트를 배치 단위로 CLIP Image Encoder에 통과시켜
    L2 정규화된 (N, clip_dim) float32 배열을 반환합니다.
    열기에 실패한 이미지는 zero 벡터로 대체합니다.
    """
    all_embeddings = []

    with torch.no_grad():
        for i in tqdm(range(0, len(image_paths), BATCH_SIZE), desc="  임베딩 추출"):
            batch = image_paths[i : i + BATCH_SIZE]
            images, valid = [], []

            for p in batch:
                try:
                    images.append(Image.open(p).convert("RGB"))
                    valid.append(True)
                except Exception as e:
                    print(f"\n열기 실패 ({os.path.basename(p)}): {e}")
                    images.append(Image.new("RGB", (224, 224)))  # 더미
                    valid.append(False)

            inputs = processor(images=images, return_tensors="pt").to(device)
            feats  = model.get_image_features(**inputs)

            # 만약 반환값이 Tensor가 아니라 BaseModelOutputWithPooling 객체라면 내부 텐서를 추출
            if hasattr(feats, "pooler_output"):
                feats = feats.pooler_output
                
            feats  = feats / feats.norm(dim=-1, keepdim=True)   # L2 정규화
            feats_np = feats.cpu().numpy().astype("float32")

            for j, ok in enumerate(valid):
                if not ok:
                    feats_np[j] = np.zeros(clip_dim, dtype="float32")

            all_embeddings.append(feats_np)

    return np.vstack(all_embeddings)  # (N, clip_dim)


# ──────────────────────────────────────────────────────────────
# 4. 저장
# ──────────────────────────────────────────────────────────────

def save_faiss(embeddings: np.ndarray, tile_ids: list[str],
               index_path: str, ids_path: str) -> None:
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # 정규화 벡터 → 내적 == 코사인 유사도
    index.add(embeddings)
    faiss.write_index(index, index_path)
    np.save(ids_path, np.array(tile_ids))
    print(f"FAISS  : {index_path}  ({index.ntotal}개 벡터)")
    print(f"tile_ids: {ids_path}")


def save_sqlite(rows: list[dict], db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tile_info (
            tile_id    TEXT PRIMARY KEY,
            district   TEXT NOT NULL,
            gu         TEXT NOT NULL,
            zoom       INTEGER NOT NULL,
            tile_x     INTEGER NOT NULL,
            tile_y     INTEGER NOT NULL,
            latitude   REAL NOT NULL,
            longitude  REAL NOT NULL,
            image_path TEXT NOT NULL
        )
    """)
    cur.executemany("""
        INSERT OR REPLACE INTO tile_info
            (tile_id, district, gu, zoom, tile_x, tile_y,
             latitude, longitude, image_path)
        VALUES
            (:tile_id, :district, :gu, :zoom, :tile_x, :tile_y,
             :latitude, :longitude, :image_path)
    """, rows)
    conn.commit()
    conn.close()
    print(f"SQLite : {db_path}  ({len(rows)}개 타일)")


# ──────────────────────────────────────────────────────────────
# 5. 검증
# ──────────────────────────────────────────────────────────────

def verify(index_path: str, ids_path: str, db_path: str) -> None:
    print(f"\n검증: {os.path.basename(index_path)}")
    try:
        index    = faiss.read_index(index_path)
        tile_ids = np.load(ids_path, allow_pickle=True).tolist()
        assert index.ntotal == len(tile_ids), \
            f"벡터 수 불일치: FAISS={index.ntotal} / tile_ids={len(tile_ids)}"
        print(f"벡터 수 일치: {index.ntotal}")

        conn = sqlite3.connect(db_path)
        row  = conn.execute(
            "SELECT * FROM tile_info WHERE tile_id = ?", (tile_ids[0],)
        ).fetchone()
        conn.close()
        assert row is not None, f"tile_id '{tile_ids[0]}' 가 SQLite에 없음"
        print(f"SQLite 연동 확인: {row}")
    except Exception as e:
        print(f"검증 실패: {e}")


# ──────────────────────────────────────────────────────────────
# 6. 단일 지역 처리 (수집 → 파싱 → 임베딩)
#    반환: (embeddings, tile_ids, rows) — 저장은 메인에서 일괄 처리
# ──────────────────────────────────────────────────────────────

def process_region(cfg: dict, model, processor, device: str, clip_dim: int):
    folder       = cfg["folder"]
    district_key = cfg["district_key"]
    prefix       = cfg["prefix"]
    gu           = cfg["gu"]

    print(f"\n📂 [{gu} / {district_key}]  {folder}")

    image_paths = collect_image_paths(folder)
    if not image_paths:
        print("이미지 없음, 건너뜀")
        return None, [], []

    print(f"{len(image_paths)}장 발견")

    rows, tile_ids, valid_paths = [], [], []
    skipped = 0

    for idx, img_path in enumerate(image_paths):
        parsed = parse_tile_filename(os.path.basename(img_path))
        if parsed is None:
            skipped += 1
            continue

        zoom, tx, ty = parsed
        lat, lon     = tile_xy_to_latlon(zoom, tx, ty)
        tile_id      = f"{prefix}_{idx + 1:04d}"

        rows.append({
            "tile_id":    tile_id,
            "district":   district_key,
            "gu":         gu,
            "zoom":       zoom,
            "tile_x":     tx,
            "tile_y":     ty,
            "latitude":   lat,
            "longitude":  lon,
            "image_path": img_path,
        })
        tile_ids.append(tile_id)
        valid_paths.append(img_path)

    if skipped:
        print(f"파일명 파싱 실패 {skipped}개 건너뜀")

    if not valid_paths:
        print("유효한 이미지 없음")
        return None, [], []

    embeddings = extract_embeddings(valid_paths, model, processor, device, clip_dim)
    return embeddings, tile_ids, rows


# ──────────────────────────────────────────────────────────────
# 7. 메인
# ──────────────────────────────────────────────────────────────

def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"디바이스: {device}")

    # 모델 1회 로드 (4개 지역 공통 사용)
    model, processor = load_clip_model(device)

    # 실제 CLIP 출력 차원 자동 감지
    with torch.no_grad():
        dummy    = processor(images=Image.new("RGB", (224, 224)),
                            return_tensors="pt").to(device)
        features = model.get_image_features(**dummy)

        # 만약 반환값이 Tensor가 아니라 BaseModelOutputWithPooling 객체라면 내부 텐서를 추출
        if hasattr(features, "pooler_output"):
            features = features.pooler_output

        clip_dim = features.shape[-1]
    print(f"CLIP 임베딩 차원: {clip_dim}\n")

    # ── 4개 지역 각각 독립 DB 구축 ────────────────────────────────
    # district_key 가 출력 파일명 suffix로 사용됩니다.
    #   faiss_{district_key}.index
    #   tile_ids_{district_key}.npy
    #   metadata_{district_key}.db
    # ─────────────────────────────────────────────────────────────
    results_summary = []   # 완료 후 출력용 (key, status) status: "built" | "skipped" | "failed"

    for cfg in REGION_CONFIGS:
        key        = cfg["district_key"]
        index_path = os.path.join(OUT_DIR, f"faiss_{key}.index")
        ids_path   = os.path.join(OUT_DIR, f"tile_ids_{key}.npy")
        db_path    = os.path.join(OUT_DIR, f"metadata_{key}.db")

        print("\n" + "=" * 55)
        print(f"[{cfg['gu']} / {key}] FAISS 인덱스 구축")
        print("=" * 55)

        # 이미 3개 파일이 모두 존재하면 임베딩 추출 없이 건너뜀
        if os.path.exists(index_path) and os.path.exists(ids_path) and os.path.exists(db_path):
            print(f"  → DB 파일이 이미 존재합니다. Skip")
            print(f"     {index_path}")
            print(f"     {ids_path}")
            print(f"     {db_path}")
            results_summary.append((key, "skipped"))
            continue

        embs, ids, rows = process_region(cfg, model, processor, device, clip_dim)
        if embs is None:
            results_summary.append((key, "failed"))
            continue

        save_faiss(embs, ids, index_path, ids_path)
        save_sqlite(rows, db_path)
        verify(index_path, ids_path, db_path)

        results_summary.append((key, "built"))

    # ── 완료 요약 ─────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("전체 FAISS 인덱스 구축 완료!")
    print(f"   출력 경로: {OUT_DIR}/")
    print("=" * 55)
    status_icon = {"built": "✅", "skipped": "⏭ ", "failed": "❌"}
    for key, status in results_summary:
        step_tag = "STEP 1" if key == "seongdong" else "STEP 2"
        label    = {"built": "완료", "skipped": "Skip (이미 존재)", "failed": "실패"}[status]
        print(f"  {status_icon[status]}  faiss_{key}.index  ({step_tag})  {label}")


if __name__ == "__main__":
    main()