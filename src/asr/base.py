"""ASR Provider 抽象基类。

所有语音识别服务都必须实现这个接口，
这样切换服务商只需改一个环境变量。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ASRResult:
    """ASR识别结果"""
    text: str = ""        # 识别出的文字
    duration: float = 0.0  # 音频时长（秒）
    provider: str = ""     # 服务商名称


class ASRProvider(ABC):
    """ASR Provider 抽象基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """检查是否已配置必要的API Key等。
        
        这是 Fail Fast 的关键——在做任何耗时操作之前先检查。
        """
        ...

    @abstractmethod
    async def transcribe(self, audio_path: str) -> ASRResult:
        """将音频文件转为文字。

        Args:
            audio_path: 本地音频文件路径（mp3格式）

        Returns:
            ASRResult: 识别结果
        """
        ...

    def get_config_hint(self) -> str:
        """返回配置提示信息，用于用户未配置时的友好提示。"""
        return f"请配置 {self.name} 的API密钥。"
