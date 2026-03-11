"""Login helper tests."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import login
from src.server import get_login_qrcode


class LoginHelperTest(TestCase):
    def test_save_cookies_normalizes_before_writing(self):
        with TemporaryDirectory() as tmp:
            cookie_path = Path(tmp) / "cookies.txt"
            with (
                patch("login.COOKIE_FILE", cookie_path),
                patch("login._ensure_gitignore"),
            ):
                success = login._save_cookies(
                    "sessionid=abc123; Path=/; bad_segment; ttwid=xyz"
                )

            self.assertTrue(success)
            self.assertEqual(
                cookie_path.read_text(encoding="utf-8"),
                "sessionid=abc123; ttwid=xyz",
            )

    def test_save_cookies_rejects_empty_cookie(self):
        with TemporaryDirectory() as tmp:
            cookie_path = Path(tmp) / "cookies.txt"
            with (
                patch("login.COOKIE_FILE", cookie_path),
                patch("login._ensure_gitignore"),
            ):
                success = login._save_cookies("bad_segment; Secure")

            self.assertFalse(success)
            self.assertFalse(cookie_path.exists())

    def test_get_login_qrcode_uses_api_qrcode_mode(self):
        with patch("subprocess.Popen") as mock_popen:
            result = asyncio.run(get_login_qrcode())

        self.assertFalse(result["logged_in"])
        self.assertTrue(result["launched"])
        self.assertEqual(result["mode"], "api_qrcode")
        self.assertIn("二维码", result["message"])
        command = mock_popen.call_args.args[0]
        self.assertEqual(command[-1], "--api")
