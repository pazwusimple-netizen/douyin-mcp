"""本地 .env 配置加载测试。"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from src.config import _load_env_file


class EnvLocalTest(TestCase):
    def test_load_env_file_reads_basic_key_values(self):
        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.local"
            env_path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "ASR_PROVIDER=volcengine",
                        "export VOLCENGINE_APP_ID='appid-123'",
                        'VOLCENGINE_ACCESS_TOKEN="token-456"',
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=False):
                _load_env_file(env_path)
                self.assertEqual(os.environ["ASR_PROVIDER"], "volcengine")
                self.assertEqual(os.environ["VOLCENGINE_APP_ID"], "appid-123")
                self.assertEqual(os.environ["VOLCENGINE_ACCESS_TOKEN"], "token-456")

    def test_load_env_file_does_not_override_existing_env_by_default(self):
        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.local"
            env_path.write_text("ASR_PROVIDER=volcengine", encoding="utf-8")

            with patch.dict(os.environ, {"ASR_PROVIDER": "openai"}, clear=False):
                _load_env_file(env_path, override=False)
                self.assertEqual(os.environ["ASR_PROVIDER"], "openai")

    def test_load_env_file_can_override_when_requested(self):
        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.local"
            env_path.write_text("ASR_PROVIDER=volcengine", encoding="utf-8")

            with patch.dict(os.environ, {"ASR_PROVIDER": "openai"}, clear=False):
                _load_env_file(env_path, override=True)
                self.assertEqual(os.environ["ASR_PROVIDER"], "volcengine")
