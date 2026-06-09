"""
pipeline/clip_engine.py
───────────────────────
CLIP 모델을 1회만 로드하고 텍스트/이미지 인코딩을 제공하는 싱글톤 모듈.

외부에서는 get_engine() 하나만 호출하면 됩니다.

    from pipeline.clip_engine import get_engine

    engine = get_engine()
    text_vec   = engine.encode_text("숲세권 조용한 아파트")   # (1, clip_dim)
    image_vec  = engine.encode_image("data/raw/tiles/tile_18_223561_101512.jpg")  # (1, clip_dim)

두 벡터 모두 L2 정규화된 float32 ndarray 이므로
내적(inner product) == 코사인 유사도 로 바로 사용할 수 있습니다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from peft import PeftModel

from config import (
    CLIP_BASE_MODEL_PATH,
    CLIP_LORA_ADAPTER_PATH,
    CLIP_FALLBACK_MODEL_PATH,
    CLIP_TEXT_MAX_LENGTH,
)

# ──────────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────────

_BASE_MODEL_PATH    = CLIP_BASE_MODEL_PATH      # v1 전체 가중치 (LoRA 베이스)
_LORA_ADAPTER_PATH  = CLIP_LORA_ADAPTER_PATH    # LoRA 어댑터
_FALLBACK_PATH      = CLIP_FALLBACK_MODEL_PATH


# ──────────────────────────────────────────────────────────────
# CLIPEngine 클래스
# ──────────────────────────────────────────────────────────────

class CLIPEngine:
    """
    CLIP 모델 래퍼.
    encode_text / encode_image 모두 (1, clip_dim) L2정규화 float32 ndarray 반환.
    반환 벡터끼리의 내적 = 코사인 유사도 ([-1, 1] 범위).
    """

    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.processor = self._load()
        # 실제 CLIP 임베딩 차원 자동 감지
        self.clip_dim: int = self._detect_dim()
        print(f"[CLIPEngine] 로드 완료 | device={self.device} | dim={self.clip_dim}")

    # ── 내부 메서드 ────────────────────────────────────────────

    def _load(self) -> tuple[CLIPModel, CLIPProcessor]:
        """
        우선순위에 따라 모델을 로드합니다.
 
        LoRA 어댑터가 있는 경우:
            1. 베이스 모델(_BASE_MODEL_PATH) 로드
            2. PeftModel.from_pretrained()로 LoRA 어댑터 적용
            3. merge_and_unload()로 LoRA를 베이스에 병합
               → 일반 CLIPModel로 변환되어 이후 코드 변경 불필요
        """
        base_exists  = os.path.exists(_BASE_MODEL_PATH)
        lora_exists  = os.path.exists(_LORA_ADAPTER_PATH)
 
        if base_exists and lora_exists:
            # ── LoRA 어댑터 병합 ──────────────────────────────
            print(f"[CLIPEngine] 베이스 모델 로드: {_BASE_MODEL_PATH}")
            model = CLIPModel.from_pretrained(
                _BASE_MODEL_PATH, torch_dtype=torch.float32
            ).to(self.device)
 
            print(f"[CLIPEngine] LoRA 어댑터 적용: {_LORA_ADAPTER_PATH}")
            model = PeftModel.from_pretrained(model, _LORA_ADAPTER_PATH)
 
            print("[CLIPEngine] LoRA → 베이스 병합(merge_and_unload) 중...")
            model = model.merge_and_unload()   # 일반 CLIPModel로 변환
            processor = CLIPProcessor.from_pretrained(_BASE_MODEL_PATH)
 
        elif base_exists:
            # ── v1 전체 가중치만 사용 ─────────────────────────
            print(f"[CLIPEngine] v1 가중치 로드 (LoRA 없음): {_BASE_MODEL_PATH}")
            model     = CLIPModel.from_pretrained(_BASE_MODEL_PATH).to(self.device)
            processor = CLIPProcessor.from_pretrained(_BASE_MODEL_PATH)
 
        else:
            # ── fallback: OpenAI 기본 가중치 ──────────────────
            print(f"[CLIPEngine] 파인튜닝 모델 없음 → 기본 모델 사용: {_FALLBACK_PATH}")
            model     = CLIPModel.from_pretrained(_FALLBACK_PATH).to(self.device)
            processor = CLIPProcessor.from_pretrained(_FALLBACK_PATH)
 
        model.eval()
        return model, processor

    def _detect_dim(self) -> int:
        """더미 입력으로 실제 임베딩 차원을 감지합니다."""
        with torch.no_grad():
            dummy  = self.processor(
                images=Image.new("RGB", (224, 224)),
                return_tensors="pt"
            ).to(self.device)
            feats  = self.model.get_image_features(**dummy)
            # BaseModelOutputWithPooling 대응
            if not isinstance(feats, torch.Tensor):
                feats = feats.pooler_output
        return feats.shape[-1]

    @staticmethod
    def _to_numpy_normalized(tensor: torch.Tensor) -> np.ndarray:
        """
        (1, dim) 텐서 → L2 정규화 → float32 ndarray.
        BaseModelOutputWithPooling 반환값도 처리합니다.
        """
        if not isinstance(tensor, torch.Tensor):
            tensor = tensor.pooler_output          # BaseModelOutputWithPooling 대응
        tensor = tensor / tensor.norm(dim=-1, keepdim=True)   # L2 정규화
        return tensor.cpu().numpy().astype("float32")          # (1, dim)

    # ── 공개 메서드 ────────────────────────────────────────────

    def encode_text(self, text: str) -> np.ndarray:
        """
        자연어 쿼리를 CLIP Text Encoder로 인코딩합니다.

        Args:
            text: 입지 설명 자연어 (예: "나무가 많고 조용한 아파트 단지")

        Returns:
            shape (1, clip_dim), L2 정규화된 float32 ndarray.
            search.py 에서 FAISS IndexFlatIP 내적 검색에 바로 사용 가능.
        """
        with torch.no_grad():
            inputs = self.processor(
                text=text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=CLIP_TEXT_MAX_LENGTH,
            ).to(self.device)
            feats = self.model.get_text_features(**inputs)
        return self._to_numpy_normalized(feats)   # (1, clip_dim)

    def encode_image(self, image_source: Union[str, Path, Image.Image]) -> np.ndarray:
        """
        위성 이미지를 CLIP Image Encoder로 인코딩합니다.

        Args:
            image_source: 이미지 파일 경로(str / Path) 또는 PIL.Image 객체.
                          SQLite image_path 컬럼의 혼합 구분자 경로도 pathlib.Path로
                          정규화하여 처리합니다.

        Returns:
            shape (1, clip_dim), L2 정규화된 float32 ndarray.
            encode_text() 결과와 동일한 임베딩 공간에 있으므로
            두 벡터의 내적 = 코사인 유사도.

        Raises:
            FileNotFoundError: 파일 경로가 존재하지 않을 때.
            OSError: 이미지 파일을 열 수 없을 때.
        """
        # PIL.Image 가 아니면 경로로 간주하고 열기
        if not isinstance(image_source, Image.Image):
            # pathlib.Path 로 정규화 (혼합 구분자 '\' '/' 모두 처리)
            path = Path(str(image_source))
            if not path.exists():
                raise FileNotFoundError(f"[CLIPEngine] 이미지 파일 없음: {path}")
            image = Image.open(path).convert("RGB")
        else:
            image = image_source

        with torch.no_grad():
            inputs = self.processor(
                images=image,
                return_tensors="pt"
            ).to(self.device)
            feats = self.model.get_image_features(**inputs)
        return self._to_numpy_normalized(feats)   # (1, clip_dim)

    def encode_image_batch(
        self,
        image_sources: list[Union[str, Path, Image.Image]],
    ) -> np.ndarray:
        """
        여러 이미지를 한 번에 배치 인코딩합니다. (build_vector_db 에서 사용)

        Args:
            image_sources: 파일 경로 또는 PIL.Image 리스트.

        Returns:
            shape (N, clip_dim), L2 정규화된 float32 ndarray.
        """
        images = []
        for src in image_sources:
            if isinstance(src, Image.Image):
                images.append(src)
            else:
                path = Path(str(src))
                images.append(Image.open(path).convert("RGB"))

        with torch.no_grad():
            inputs = self.processor(
                images=images,
                return_tensors="pt"
            ).to(self.device)
            feats = self.model.get_image_features(**inputs)
        return self._to_numpy_normalized(feats)   # (N, clip_dim)


# ──────────────────────────────────────────────────────────────
# 모듈 레벨 싱글톤
# ──────────────────────────────────────────────────────────────

_engine_instance: CLIPEngine | None = None


def get_engine() -> CLIPEngine:
    """
    CLIPEngine 싱글톤을 반환합니다.
    첫 호출 시에만 모델을 로드하고, 이후 호출은 캐시된 인스턴스를 반환합니다.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = CLIPEngine()
    return _engine_instance


# ──────────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = get_engine()

    # 텍스트 인코딩 테스트
    text_vec = engine.encode_text("숲세권 조용한 저밀도 주거지")
    print(f"텍스트 벡터 shape : {text_vec.shape}")          # (1, clip_dim)
    print(f"L2 norm           : {np.linalg.norm(text_vec):.6f}")  # ≈ 1.0

    # 이미지 인코딩 테스트 (더미 PIL 이미지)
    dummy_img = Image.new("RGB", (224, 224), color=(100, 150, 80))
    img_vec   = engine.encode_image(dummy_img)
    print(f"이미지 벡터 shape : {img_vec.shape}")           # (1, clip_dim)
    print(f"L2 norm           : {np.linalg.norm(img_vec):.6f}")   # ≈ 1.0

    # 텍스트 ↔ 이미지 코사인 유사도 (내적)
    text_vec_np = text_vec.cpu().numpy() if hasattr(text_vec, "cpu") else text_vec
    img_vec_np  = img_vec.cpu().numpy() if hasattr(img_vec, "cpu") else img_vec

    # NumPy 배열 간의 계산 후 스칼라 변환
    similarity = (text_vec_np @ img_vec_np.T).item()
    print(f"텍스트-이미지 유사도 : {similarity:.4f}")        # [-1, 1]

    # 싱글톤 확인
    engine2 = get_engine()
    print(f"싱글톤 동일 객체 여부: {engine is engine2}")     # True