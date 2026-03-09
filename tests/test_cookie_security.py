"""Cookie 安全相关单元测试。"""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from src.server import _persist_transcript, _validate_cookie, load_cookies, logout


class CookieSecurityTest(TestCase):
    def test_validate_cookie_normalizes_and_removes_invalid_segments(self):
        raw = " sessionid=abc123 ; bad_segment ; ttwid = xyz ; sessionid_ss=def \n"
        cleaned = _validate_cookie(raw, source="unit-test")

        self.assertIn("sessionid=abc123", cleaned)
        self.assertIn("ttwid=xyz", cleaned)
        self.assertIn("sessionid_ss=def", cleaned)
        self.assertNotIn("bad_segment", cleaned)
        self.assertNotIn("\n", cleaned)

    def test_load_cookies_uses_legacy_file_as_fallback(self):
        with TemporaryDirectory() as tmp:
            new_path = Path(tmp) / "new_cookie.txt"
            legacy_path = Path(tmp) / "legacy_cookie.txt"
            legacy_path.write_text("sessionid=legacy123", encoding="utf-8")

            with patch.multiple(
                "src.server",
                COOKIE_STRING="",
                COOKIE_PATH=str(new_path),
                COOKIE_PATH_FROM_ENV=False,
                LEGACY_COOKIE_PATH=legacy_path,
            ):
                cookie = load_cookies()

        self.assertEqual(cookie, "sessionid=legacy123")

    def test_load_cookies_prefers_env_cookie(self):
        with TemporaryDirectory() as tmp:
            new_path = Path(tmp) / "new_cookie.txt"
            legacy_path = Path(tmp) / "legacy_cookie.txt"
            legacy_path.write_text("sessionid=legacy123", encoding="utf-8")

            with patch.multiple(
                "src.server",
                COOKIE_STRING="sessionid=env123",
                COOKIE_PATH=str(new_path),
                COOKIE_PATH_FROM_ENV=False,
                LEGACY_COOKIE_PATH=legacy_path,
            ):
                cookie = load_cookies()

        self.assertEqual(cookie, "sessionid=env123")

    def test_logout_deletes_cookie_files(self):
        with TemporaryDirectory() as tmp:
            new_path = Path(tmp) / "new_cookie.txt"
            legacy_path = Path(tmp) / "legacy_cookie.txt"
            new_path.write_text("sessionid=new123", encoding="utf-8")
            legacy_path.write_text("sessionid=legacy123", encoding="utf-8")

            with patch.multiple(
                "src.server",
                COOKIE_STRING="",
                COOKIE_PATH=str(new_path),
                COOKIE_PATH_FROM_ENV=False,
                LEGACY_COOKIE_PATH=legacy_path,
            ):
                result = asyncio.run(logout())

        self.assertTrue(result["success"])
        self.assertEqual(
            set(result["deleted_files"]),
            {str(new_path), str(legacy_path)},
        )
        self.assertFalse(new_path.exists())
        self.assertFalse(legacy_path.exists())

    def test_logout_cannot_clear_env_cookie(self):
        with TemporaryDirectory() as tmp:
            new_path = Path(tmp) / "new_cookie.txt"

            with patch.multiple(
                "src.server",
                COOKIE_STRING="sessionid=env123",
                COOKIE_PATH=str(new_path),
                COOKIE_PATH_FROM_ENV=True,
                LEGACY_COOKIE_PATH=Path(tmp) / "legacy_cookie.txt",
            ):
                result = asyncio.run(logout())

        self.assertFalse(result["success"])
        self.assertTrue(result["requires_manual_action"])
        self.assertIn("DOUYIN_COOKIE", result["message"])

    def test_persist_transcript_writes_txt_file(self):
        with TemporaryDirectory() as tmp:
            with patch.multiple(
                "src.server",
                AUTO_SAVE_TRANSCRIPTS=True,
                TRANSCRIPT_DIR=str(Path(tmp) / "transcripts"),
            ):
                saved_path, save_error = _persist_transcript(
                    aweme_id="123456",
                    title="测试视频",
                    author="作者A",
                    aweme_url="https://example.com/video/123456",
                    liked_count="99",
                    collected_count="12",
                    duration=12.3,
                    provider="单元测试 ASR",
                    text="这里是转写正文",
                )
                content = Path(saved_path).read_text(encoding="utf-8")

        self.assertEqual(save_error, "")
        self.assertTrue(saved_path.endswith("_123456.txt"))
        self.assertIn("标题: 测试视频", content)
        self.assertIn("这里是转写正文", content)
