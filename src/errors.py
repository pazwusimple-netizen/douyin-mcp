"""统一错误处理模块 — MCP工具永远不崩溃，返回友好错误信息。"""

import functools


class DouyinMCPError(Exception):
    """抖音MCP基础异常"""

    def __init__(self, message: str, suggestion: str = ""):
        self.message = message
        self.suggestion = suggestion  # 告诉用户怎么修
        super().__init__(message)

    def to_user_message(self) -> str:
        """生成友好的用户提示信息"""
        msg = f"❌ {self.message}"
        if self.suggestion:
            msg += f"\n💡 {self.suggestion}"
        return msg


class CookieExpiredError(DouyinMCPError):
    """Cookie过期"""

    def __init__(self):
        super().__init__(
            "Cookie已失效，无法访问抖音数据。",
            "请运行: uv run login.py 重新登录（手机扫码即可）",
        )


class SignatureError(DouyinMCPError):
    """签名生成失败"""

    def __init__(self, detail: str = ""):
        super().__init__(
            f"签名生成失败：{detail}" if detail else "签名生成失败。",
            "请检查 douyin.js 文件是否完整。",
        )


class ASRNotConfiguredError(DouyinMCPError):
    """ASR未配置"""

    def __init__(self, provider: str = ""):
        msg = f"ASR Provider '{provider}' 未配置。" if provider else "ASR未配置。"
        super().__init__(
            msg,
            "请在MCP配置的 env 中添加 ASR_PROVIDER 和对应的 API Key。"
            "例如：ASR_PROVIDER=siliconflow, SILICONFLOW_API_KEY=sk-xxx",
        )


class VideoDurationExceededError(DouyinMCPError):
    """视频超出时长限制"""

    def __init__(self, duration: int, max_duration: int):
        super().__init__(
            f"视频时长 {duration} 秒超过 {max_duration} 秒的限制。",
            "可通过环境变量 MAX_AUDIO_DURATION 调整限制。",
        )


class FFmpegError(DouyinMCPError):
    """FFmpeg处理失败"""

    def __init__(self, detail: str = ""):
        super().__init__(
            f"音频提取失败：{detail}" if detail else "音频提取失败。",
            "请检查视频URL是否有效。",
        )


class NoSpeechDetectedError(DouyinMCPError):
    """视频无人声"""

    def __init__(self):
        super().__init__(
            "未检测到人声。",
            "该视频可能是纯音乐、纯画面或语音过短。",
        )


class VerificationRequiredError(DouyinMCPError):
    """触发验证码"""

    def __init__(self):
        super().__init__(
            "触发了抖音验证码。",
            "请降低请求频率或更换Cookie。",
        )


class DataFetchError(DouyinMCPError):
    """数据获取失败（通用网络/API错误）"""

    def __init__(self, detail: str = ""):
        super().__init__(
            f"数据获取失败：{detail}" if detail else "数据获取失败。",
            "请检查网络连接，或Cookie是否仍然有效。",
        )


def safe_tool_call(func):
    """装饰器：包裹MCP工具函数，确保任何异常都被捕获并返回友好信息。

    使用方式:
        @safe_tool_call
        async def my_tool(...):
            ...
    """

    @functools.wraps(func)  # 保留原函数签名/文档/名称（fastmcp 需要）
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except DouyinMCPError as e:
            return e.to_user_message()
        except Exception as e:
            return f"❌ 发生未预期的错误：{type(e).__name__}: {e}\n💡 请检查日志或联系开发者。"

    return wrapper
