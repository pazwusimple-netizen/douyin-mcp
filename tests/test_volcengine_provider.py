"""火山引擎 ASR Provider 单元测试（离线）。"""

import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import patch

from src.asr.volcengine import VolcengineProvider


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = "", headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

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

    async def post(self, url: str, json: dict, headers: dict):
        self.post_calls.append({"url": url, "json": json, "headers": headers})
        return self.response


class VolcengineProviderTest(TestCase):
    def test_is_configured_requires_app_id_and_token(self):
        provider = VolcengineProvider()

        with patch.multiple(
            "src.asr.volcengine",
            VOLCENGINE_APP_ID="",
            VOLCENGINE_ACCESS_TOKEN="token",
        ):
            self.assertFalse(provider.is_configured())

        with patch.multiple(
            "src.asr.volcengine",
            VOLCENGINE_APP_ID="app",
            VOLCENGINE_ACCESS_TOKEN="token",
        ):
            self.assertTrue(provider.is_configured())

    def test_transcribe_builds_expected_request_and_parses_text(self):
        with NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake-audio")
            audio_path = Path(f.name)

        fake_response = _FakeResponse(
            status_code=200,
            payload={"code": 0, "result": [{"text": "你好"}, {"text": "世界"}]},
            headers={"X-Api-Status-Code": "20000000"},
        )
        fake_client = _FakeAsyncClient(fake_response)

        try:
            with patch("src.asr.volcengine.httpx.AsyncClient", return_value=fake_client):
                with patch.multiple(
                    "src.asr.volcengine",
                    VOLCENGINE_APP_ID="app-id-1",
                    VOLCENGINE_ACCESS_TOKEN="token-1",
                    VOLCENGINE_RESOURCE_ID="volc.bigasr.auc_turbo",
                    VOLCENGINE_AUDIO_FORMAT="mp3",
                    VOLCENGINE_MODEL="bigmodel",
                    VOLCENGINE_MODEL_VERSION="",
                    VOLCENGINE_API_URL="https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash",
                    VOLCENGINE_CLUSTER="cluster-1",
                ):
                    result = asyncio.run(VolcengineProvider().transcribe(str(audio_path)))
        finally:
            audio_path.unlink(missing_ok=True)

        self.assertEqual(result.text, "你好世界")
        self.assertEqual(result.provider, "火山引擎 ASR")
        self.assertEqual(len(fake_client.post_calls), 1)

        call = fake_client.post_calls[0]
        self.assertEqual(call["url"], "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash")
        self.assertEqual(call["json"]["user"]["uid"], "app-id-1")
        self.assertEqual(call["json"]["request"]["model_name"], "bigmodel")
        self.assertIn("data", call["json"]["audio"])
        self.assertEqual(call["headers"]["X-Api-App-Key"], "app-id-1")
        self.assertEqual(call["headers"]["X-Api-Access-Key"], "token-1")
        self.assertEqual(call["headers"]["X-Api-Resource-Id"], "volc.bigasr.auc_turbo")
        self.assertIn("X-Api-Request-Id", call["headers"])
        self.assertEqual(call["headers"]["X-Api-Sequence"], "-1")

    def test_transcribe_raises_runtime_error_on_api_error(self):
        with NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake-audio")
            audio_path = Path(f.name)

        fake_response = _FakeResponse(
            status_code=200,
            payload={"code": 1001, "message": "invalid token"},
            headers={"X-Api-Status-Code": "12345678", "X-Api-Message": "invalid token"},
        )
        fake_client = _FakeAsyncClient(fake_response)

        try:
            with patch("src.asr.volcengine.httpx.AsyncClient", return_value=fake_client):
                with patch.multiple(
                    "src.asr.volcengine",
                    VOLCENGINE_APP_ID="app-id-1",
                    VOLCENGINE_ACCESS_TOKEN="token-1",
                    VOLCENGINE_API_URL="https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash",
                    VOLCENGINE_CLUSTER="cluster-1",
                    VOLCENGINE_AUDIO_FORMAT="mp3",
                    VOLCENGINE_MODEL="bigmodel",
                    VOLCENGINE_MODEL_VERSION="",
                    VOLCENGINE_RESOURCE_ID="volc.bigasr.auc_turbo",
                ):
                    with self.assertRaises(RuntimeError):
                        asyncio.run(VolcengineProvider().transcribe(str(audio_path)))
        finally:
            audio_path.unlink(missing_ok=True)

    def test_transcribe_legacy_v1_uses_authorization_header(self):
        with NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake-audio")
            audio_path = Path(f.name)

        fake_response = _FakeResponse(
            status_code=200,
            payload={"code": 0, "result": [{"text": "legacy"}]},
        )
        fake_client = _FakeAsyncClient(fake_response)

        try:
            with patch("src.asr.volcengine.httpx.AsyncClient", return_value=fake_client):
                with patch.multiple(
                    "src.asr.volcengine",
                    VOLCENGINE_APP_ID="app-id-legacy",
                    VOLCENGINE_ACCESS_TOKEN="token-legacy",
                    VOLCENGINE_API_URL="https://openspeech.bytedance.com/api/v1/asr",
                    VOLCENGINE_CLUSTER="cluster-legacy",
                    VOLCENGINE_AUDIO_FORMAT="mp3",
                    VOLCENGINE_MODEL="sensevoice",
                    VOLCENGINE_MODEL_VERSION="",
                    VOLCENGINE_RESOURCE_ID="volc.bigasr.auc_turbo",
                ):
                    result = asyncio.run(VolcengineProvider().transcribe(str(audio_path)))
        finally:
            audio_path.unlink(missing_ok=True)

        self.assertEqual(result.text, "legacy")
        call = fake_client.post_calls[0]
        self.assertEqual(call["json"]["app"]["appid"], "app-id-legacy")
        self.assertEqual(call["json"]["app"]["token"], "token-legacy")
        self.assertEqual(call["headers"]["Authorization"], "Bearer; token-legacy")
