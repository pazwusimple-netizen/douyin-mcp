"""可选 OCR 能力。

当前默认接入 rapidocr-onnxruntime；未安装时按需报错，
避免影响不需要 OCR 的用户。
"""

from __future__ import annotations

from pathlib import Path

from .config import OCR_PROVIDER
from .errors import OCRNotConfiguredError


def _load_rapidocr():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise OCRNotConfiguredError(OCR_PROVIDER) from exc
    return RapidOCR()


def _extract_lines(result) -> list[str]:
    lines = []
    for item in result or []:
        if not item or len(item) < 2:
            continue
        text = str(item[1]).strip()
        if text:
            lines.append(text)
    return lines


def run_ocr(image_path: str) -> dict:
    """对单张图片执行 OCR。"""
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")

    provider = OCR_PROVIDER or "rapidocr"
    if provider != "rapidocr":
        raise OCRNotConfiguredError(provider)

    engine = _load_rapidocr()
    result, _ = engine(str(image_file))
    lines = _extract_lines(result)

    return {
        "image_path": str(image_file),
        "provider": "rapidocr",
        "lines": lines,
        "text": "\n".join(lines),
    }
