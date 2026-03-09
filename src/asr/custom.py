"""通用 OpenAI Whisper 兼容 ASR Provider。

支持任何兼容 OpenAI /v1/audio/transcriptions 接口的服务商，
用户只需设置 ASR_API_KEY + ASR_API_URL + ASR_MODEL 即可。

兼容服务商示例：
- 硅基流动（默认有专用 Provider，也可用本通用版）
- Groq（https://api.groq.com/openai/v1/audio/transcriptions）
- Deepgram（https://api.deepgram.com/v1/audio/transcriptions）
- 本地 Whisper（https://localhost:8080/v1/audio/transcriptions）
"""

import logging
from pathlib import Path

import httpx

from ..config import (
    ASR_API_KEY,
    ASR_API_URL,
    ASR_MODEL,
    ASR_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_API_URL,
    OPENAI_MODEL,
)
from .base import ASRProvider, ASRResult

logger = logging.getLogger("douyinmcp.asr.custom")


class CustomProvider(ASRProvider):
    """通用 OpenAI Whisper 兼容 ASR Provider。

    只要服务商接口格式满足：
    POST /v1/audio/transcriptions
    Headers: Authorization: Bearer xxx
    Body: multipart（file + model）
    Response: {"text": "..."}
    就能直接用。
    """

    @staticmethod
    def _is_openai_mode() -> bool:
        return ASR_PROVIDER.lower().strip() == "openai"

    def _effective_api_key(self) -> str:
        if self._is_openai_mode():
            return OPENAI_API_KEY
        return ASR_API_KEY

    def _effective_api_url(self) -> str:
        if self._is_openai_mode():
            return OPENAI_API_URL
        return ASR_API_URL

    def _effective_model(self) -> str:
        if self._is_openai_mode():
            return OPENAI_MODEL
        return ASR_MODEL

    @property
    def name(self) -> str:
        if self._is_openai_mode():
            return "OpenAI Whisper"
        return f"Custom ({self._effective_api_url() or '未配置'})"

    def is_configured(self) -> bool:
        return bool(self._effective_api_key() and self._effective_api_url())

    def get_config_hint(self) -> str:
        if self._is_openai_mode():
            return (
                "OpenAI ASR 需要配置以下环境变量：\n"
                "  ASR_PROVIDER=openai\n"
                "  OPENAI_API_KEY=sk-xxx\n"
                "  OPENAI_API_URL=https://api.openai.com/v1/audio/transcriptions（可选）\n"
                "  OPENAI_MODEL=whisper-1（可选）"
            )
        return (
            "通用 ASR 需要配置以下环境变量：\n"
            "  ASR_PROVIDER=custom\n"
            "  ASR_API_KEY=你的API密钥\n"
            "  ASR_API_URL=https://服务商/v1/audio/transcriptions\n"
            "  ASR_MODEL=模型名（可选）"
        )

    async def transcribe(self, audio_path: str) -> ASRResult:
        """调用 OpenAI 兼容接口进行语音识别。"""
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        logger.info(f"开始 ASR ({self.name}): {audio_file.name} ({file_size_mb:.1f}MB)")

        async with httpx.AsyncClient(timeout=120) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_file.name, f, "audio/mpeg")}
                data = {}
                model = self._effective_model()
                if model:
                    data["model"] = model
                headers = {"Authorization": f"Bearer {self._effective_api_key()}"}

                response = await client.post(
                    self._effective_api_url(),
                    files=files,
                    data=data,
                    headers=headers,
                )

            if response.status_code != 200:
                error_detail = response.text[:300]
                raise RuntimeError(
                    f"ASR API 返回 {response.status_code}: {error_detail}"
                )

            result = response.json()
            text = result.get("text", "").strip()

            logger.info(f"ASR 完成: {len(text)} 字符")

            return ASRResult(
                text=text,
                duration=0.0,
                provider=self.name,
            )
