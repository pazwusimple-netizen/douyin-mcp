"""错误包装与工具返回格式测试。"""

import asyncio
from unittest import TestCase

from src.client import DataFetchError as ClientDataFetchError
from src.errors import DataFetchError, safe_tool_call


class ErrorHandlingTest(TestCase):
    def test_client_data_fetch_error_is_tool_error(self):
        error = ClientDataFetchError("Request blocked or empty response")

        self.assertIsInstance(error, DataFetchError)
        self.assertIn("Request blocked or empty response", error.message)

    def test_safe_tool_call_returns_dict_for_known_error(self):
        @safe_tool_call
        async def broken_tool():
            raise DataFetchError("Request blocked or empty response")

        result = asyncio.run(broken_tool())

        self.assertEqual(result["success"], False)
        self.assertEqual(result["error_type"], "DataFetchError")
        self.assertIn("数据获取失败", result["error"])
        self.assertIn("Cookie", result["suggestion"])

    def test_safe_tool_call_returns_dict_for_unexpected_error(self):
        @safe_tool_call
        async def broken_tool():
            raise RuntimeError("boom")

        result = asyncio.run(broken_tool())

        self.assertEqual(result["success"], False)
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertIn("boom", result["error"])
