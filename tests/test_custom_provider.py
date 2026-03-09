"""通用 / OpenAI ASR Provider 单元测试（离线）。"""

import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import patch

from src.asr.custom import CustomProvider


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse):
        self.response = response
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, files: dict, data: dict, headers: dict):
        self.post_calls.append(
            {"url": url, "files": files, "data": data, "headers": headers}
        )
        return self.response


class CustomProviderTest(TestCase):
    def test_custom_mode_uses_generic_asr_env(self):
        provider = CustomProvider()

        with patch.multiple(
            "src.asr.custom",
            ASR_PROVIDER="custom",
            ASR_API_KEY="generic-key",
            ASR_API_URL="https://example.com/v1/audio/transcriptions",
            ASR_MODEL="whisper-large-v3",
            OPENAI_API_KEY="openai-key",
            OPENAI_API_URL="https://api.openai.com/v1/audio/transcriptions",
            OPENAI_MODEL="whisper-1",
        ):
            self.assertEqual(provider.name, "Custom (https://example.com/v1/audio/transcriptions)")
            self.assertTrue(provider.is_configured())
            self.assertIn("ASR_PROVIDER=custom", provider.get_config_hint())

    def test_openai_mode_uses_openai_env(self):
        provider = CustomProvider()

        with patch.multiple(
            "src.asr.custom",
            ASR_PROVIDER="openai",
            ASR_API_KEY="",
            ASR_API_URL="",
            ASR_MODEL="",
            OPENAI_API_KEY="openai-key",
            OPENAI_API_URL="https://api.openai.com/v1/audio/transcriptions",
            OPENAI_MODEL="whisper-1",
        ):
            self.assertEqual(provider.name, "OpenAI Whisper")
            self.assertTrue(provider.is_configured())
            self.assertIn("ASR_PROVIDER=openai", provider.get_config_hint())

    def test_transcribe_in_openai_mode_uses_openai_settings(self):
        with NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake-audio")
            audio_path = Path(f.name)

        fake_response = _FakeResponse(status_code=200, payload={"text": "hello world"})
        fake_client = _FakeAsyncClient(fake_response)

        try:
            with patch("src.asr.custom.httpx.AsyncClient", return_value=fake_client):
                with patch.multiple(
                    "src.asr.custom",
                    ASR_PROVIDER="openai",
                    ASR_API_KEY="",
                    ASR_API_URL="",
                    ASR_MODEL="",
                    OPENAI_API_KEY="openai-key",
                    OPENAI_API_URL="https://api.openai.com/v1/audio/transcriptions",
                    OPENAI_MODEL="whisper-1",
                ):
                    result = asyncio.run(CustomProvider().transcribe(str(audio_path)))
        finally:
            audio_path.unlink(missing_ok=True)

        self.assertEqual(result.text, "hello world")
        self.assertEqual(result.provider, "OpenAI Whisper")
        self.assertEqual(len(fake_client.post_calls), 1)

        call = fake_client.post_calls[0]
        self.assertEqual(call["url"], "https://api.openai.com/v1/audio/transcriptions")
        self.assertEqual(call["data"]["model"], "whisper-1")
        self.assertEqual(call["headers"]["Authorization"], "Bearer openai-key")
