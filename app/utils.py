"""
app/utils.py
────────────
이미지 처리 유틸 — 검색 결과 타일 이미지를 화면에 표시하기 위한
base64 data URI 임베딩을 담당합니다.

"""

from __future__ import annotations

import base64
from pathlib import Path


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
