"""火山引擎语音识别 ASR Provider。

使用豆包大模型录音文件极速版识别 API，一次请求即返回结果。
火山引擎是字节跳动旗下云服务平台，与抖音同宗同源。

注册: https://www.volcengine.com
语音技术控制台: https://console.volcengine.com/speech
"""

import base64
import logging
import uuid
from pathlib import Path

import httpx

from ..config import (
    VOLCENGINE_API_URL,
    VOLCENGINE_APP_ID,
    VOLCENGINE_ACCESS_TOKEN,
    VOLCENGINE_AUDIO_FORMAT,
    VOLCENGINE_CLUSTER,
    VOLCENGINE_MODEL,
    VOLCENGINE_MODEL_VERSION,
    VOLCENGINE_RESOURCE_ID,
)
from .base import ASRProvider, ASRResult

logger = logging.getLogger("douyinmcp.asr.volcengine")


class VolcengineProvider(ASRProvider):
    """火山引擎语音识别 Provider。

    使用录音文件极速版 API（同步返回，无需轮询）。
    """

    @property
    def name(self) -> str:
        return "火山引擎 ASR"

    def is_configured(self) -> bool:
        return bool(VOLCENGINE_APP_ID and VOLCENGINE_ACCESS_TOKEN)

    def get_config_hint(self) -> str:
        return (
            "请在 MCP 配置的 env 中添加：\n"
            "  ASR_PROVIDER=volcengine\n"
            "  VOLCENGINE_APP_ID=你的AppID\n"
            "  VOLCENGINE_ACCESS_TOKEN=你的AccessToken\n"
            "  VOLCENGINE_MODEL=bigmodel\n"
            "  VOLCENGINE_RESOURCE_ID=volc.bigasr.auc_turbo\n"
            "兼容旧版：VOLCENGINE_API_KEY 仍可用（不推荐）\n"
            "获取方式: 火山引擎控制台 → 语音技术 → 语音识别"
        )

    @staticmethod
    def _use_v3_flash_api(api_url: str) -> bool:
        return "/api/v3/auc/bigmodel/recognize/flash" in api_url

    def _build_v3_flash_request(self, audio_base64: str) -> tuple[dict, dict]:
        """构建火山 v3 极速版请求体与请求头。"""
        request_payload = {
            "model_name": VOLCENGINE_MODEL,
            "enable_itn": True,
            "enable_punc": True,
        }
        if VOLCENGINE_MODEL_VERSION:
            request_payload["model_version"] = VOLCENGINE_MODEL_VERSION

        payload = {
            "user": {"uid": VOLCENGINE_APP_ID},
            "audio": {"data": audio_base64},
            "request": request_payload,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Api-App-Key": VOLCENGINE_APP_ID,
            "X-Api-Access-Key": VOLCENGINE_ACCESS_TOKEN,
            "X-Api-Resource-Id": VOLCENGINE_RESOURCE_ID,
            "X-Api-Request-Id": uuid.uuid4().hex,
            "X-Api-Sequence": "-1",
        }
        return payload, headers

    def _build_legacy_v1_request(self, audio_base64: str) -> tuple[dict, dict]:
        """构建火山旧版 v1 请求体与请求头（向后兼容）。"""
        payload = {
            "app": {
                "appid": VOLCENGINE_APP_ID,
                "token": VOLCENGINE_ACCESS_TOKEN,
                "cluster": VOLCENGINE_CLUSTER,
            },
            "user": {"uid": "douyinmcp"},
            "audio": {
                "format": VOLCENGINE_AUDIO_FORMAT,
                "codec": VOLCENGINE_AUDIO_FORMAT,
                "url": "",
                "language": "zh-CN",
                "data": audio_base64,
            },
            "request": {
                "model_name": VOLCENGINE_MODEL,
                "enable_itn": True,
                "enable_punc": True,
                "result_type": "full",
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer; {VOLCENGINE_ACCESS_TOKEN}",
        }
        return payload, headers

    @staticmethod
    def _extract_text(result: dict) -> str:
        """兼容不同返回结构，提取识别文本。"""
        text_parts = []
        payload = result.get("result")

        if isinstance(payload, list):
            for utterance in payload:
                if isinstance(utterance, dict):
                    text_parts.append(utterance.get("text", ""))
        elif isinstance(payload, dict):
            text_parts.append(payload.get("text", ""))
        elif isinstance(payload, str):
            text_parts.append(payload)

        return "".join(text_parts).strip()

    async def transcribe(self, audio_path: str) -> ASRResult:
        """调用火山引擎录音文件极速版 API。"""
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        logger.info(f"开始 ASR (火山引擎): {audio_file.name} ({file_size_mb:.1f}MB)")

        # 读取音频文件并 Base64 编码
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        # 兼容两种火山接口风格
        if self._use_v3_flash_api(VOLCENGINE_API_URL):
            payload, headers = self._build_v3_flash_request(audio_base64)
        else:
            payload, headers = self._build_legacy_v1_request(audio_base64)

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(VOLCENGINE_API_URL, json=payload, headers=headers)

            if response.status_code != 200:
                error_detail = response.text[:300]
                raise RuntimeError(
                    f"火山引擎 API 返回 {response.status_code}: {error_detail}"
                )

            result = response.json()

            # 解析结果（v3: 头部状态码；v1: body.code）
            if self._use_v3_flash_api(VOLCENGINE_API_URL):
                api_status = response.headers.get("X-Api-Status-Code", "")
                if api_status and api_status not in ("0", "20000000"):
                    raise RuntimeError(
                        "火山引擎 ASR 错误: "
                        f"{response.headers.get('X-Api-Message', '未知错误')} "
                        f"(status={api_status})"
                    )
            elif result.get("code") != 0:
                raise RuntimeError(
                    f"火山引擎 ASR 错误: {result.get('message') or result.get('msg') or '未知错误'}"
                )

            text = self._extract_text(result)

            logger.info(f"ASR 完成: {len(text)} 字符")

            return ASRResult(
                text=text,
                duration=0.0,
                provider=self.name,
            )
