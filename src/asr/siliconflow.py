"""硅基流动 SenseVoice ASR Provider。

接口兼容 OpenAI Whisper 格式（一个 POST 搞定），
支持 mp3/wav 等多种格式，限制 50MB/1小时。

免费注册: https://cloud.siliconflow.cn/i/cyKSgOyU
"""

import logging
from pathlib import Path

import httpx

from ..config import SILICONFLOW_API_KEY, SILICONFLOW_MODEL, SILICONFLOW_API_URL
from .base import ASRProvider, ASRResult

logger = logging.getLogger("douyinmcp.asr.siliconflow")


class SiliconFlowProvider(ASRProvider):
    """硅基流动 SenseVoice 语音识别 Provider。"""

    @property
    def name(self) -> str:
        return "SiliconFlow SenseVoice"

    def is_configured(self) -> bool:
        return bool(SILICONFLOW_API_KEY)

    def get_config_hint(self) -> str:
        return (
            "请在 MCP 配置的 env 中添加：\n"
            "  SILICONFLOW_API_KEY=sk-xxx\n"
            "免费获取 Key: https://cloud.siliconflow.cn/i/cyKSgOyU"
        )

    async def transcribe(self, audio_path: str) -> ASRResult:
        """调用硅基流动 API 进行语音识别。"""
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        logger.info(f"开始 ASR: {audio_file.name} ({file_size_mb:.1f}MB)")

        async with httpx.AsyncClient(timeout=120) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_file.name, f, "audio/mpeg")}
                data = {"model": SILICONFLOW_MODEL}
                headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}

                response = await client.post(
                    SILICONFLOW_API_URL,
                    files=files,
                    data=data,
                    headers=headers,
                )

            if response.status_code != 200:
                error_detail = response.text[:200]
                raise RuntimeError(
                    f"硅基流动 API 返回 {response.status_code}: {error_detail}"
                )

            result = response.json()
            text = result.get("text", "").strip()

            logger.info(f"ASR 完成: {len(text)} 字符")

            return ASRResult(
                text=text,
                duration=0.0,
                provider=self.name,
            )
