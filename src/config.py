"""配置管理模块 — 从环境变量读取所有配置。"""

import os
from pathlib import Path


def _default_cookie_path() -> Path:
    """返回默认 Cookie 文件路径（用户目录，避免误提交到仓库）。"""
    xdg_config_home = os.getenv("XDG_CONFIG_HOME", "").strip()
    if xdg_config_home:
        base = Path(xdg_config_home).expanduser()
    else:
        base = Path.home() / ".config"
    return base / "douyinmcp" / "cookies.txt"


def _default_transcript_dir() -> Path:
    """返回默认转写输出目录（用户目录，避免误提交到仓库）。"""
    xdg_data_home = os.getenv("XDG_DATA_HOME", "").strip()
    if xdg_data_home:
        base = Path(xdg_data_home).expanduser()
    else:
        base = Path.home() / ".local" / "share"
    return base / "douyinmcp" / "transcripts"


# ====== ASR（语音转文字）配置 ======
# 服务商选择：siliconflow（默认）/ volcengine / openai / custom
ASR_PROVIDER = os.getenv("ASR_PROVIDER", "siliconflow")

# --- 通用 ASR 配置（所有服务商共用） ---
# 用户可以通过这三个变量对接任何 OpenAI Whisper 兼容的 ASR 服务
ASR_API_KEY = os.getenv("ASR_API_KEY", "")        # 通用 API Key
ASR_API_URL = os.getenv("ASR_API_URL", "")         # 自定义 API 地址
ASR_MODEL = os.getenv("ASR_MODEL", "")             # 自定义模型名

# --- 硅基流动专用配置 ---
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "") or ASR_API_KEY
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "FunAudioLLM/SenseVoiceSmall")
SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"

# --- 火山引擎专用配置 ---
VOLCENGINE_API_KEY = os.getenv("VOLCENGINE_API_KEY", "").strip()
# 新版推荐：分别配置 App ID 与 Access Token
# 兼容旧版：若只设置 VOLCENGINE_API_KEY，则回退为两者都使用该值
VOLCENGINE_APP_ID = os.getenv("VOLCENGINE_APP_ID", "").strip() or VOLCENGINE_API_KEY
VOLCENGINE_ACCESS_TOKEN = (
    os.getenv("VOLCENGINE_ACCESS_TOKEN", "").strip()
    or VOLCENGINE_API_KEY
    or ASR_API_KEY
)
VOLCENGINE_MODEL = os.getenv("VOLCENGINE_MODEL", "bigmodel")
VOLCENGINE_MODEL_VERSION = os.getenv("VOLCENGINE_MODEL_VERSION", "").strip()
VOLCENGINE_CLUSTER = os.getenv("VOLCENGINE_CLUSTER", "volcengine_streaming_common")
VOLCENGINE_AUDIO_FORMAT = os.getenv("VOLCENGINE_AUDIO_FORMAT", "mp3")
VOLCENGINE_RESOURCE_ID = os.getenv("VOLCENGINE_RESOURCE_ID", "volc.bigasr.auc_turbo")
VOLCENGINE_API_URL = os.getenv(
    "VOLCENGINE_API_URL",
    "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash",
)

# --- OpenAI 原生配置 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") or ASR_API_KEY
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "whisper-1")
OPENAI_API_URL = os.getenv(
    "OPENAI_API_URL",
    "https://api.openai.com/v1/audio/transcriptions",
)

# ====== 视频处理配置 ======
# 最大处理视频时长（秒），默认10分钟
MAX_AUDIO_DURATION = int(os.getenv("MAX_AUDIO_DURATION", "600"))
# 音频输出码率（kbps），64k对语音识别足够
AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "64k")

# ====== Cookie 配置 ======
# 方式1：环境变量直传 Cookie 字符串（优先级最高，适合 Docker/CI）
COOKIE_STRING = os.getenv("DOUYIN_COOKIE", "").strip()

# 方式2：从文件读取（默认放用户目录；兼容老项目根目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COOKIE_PATH = _default_cookie_path()
LEGACY_COOKIE_PATH = PROJECT_ROOT / "cookies.txt"
COOKIE_PATH_FROM_ENV = "DOUYIN_COOKIE_PATH" in os.environ
COOKIE_PATH = os.getenv(
    "DOUYIN_COOKIE_PATH",
    str(DEFAULT_COOKIE_PATH),
)

# ====== 转写输出配置 ======
AUTO_SAVE_TRANSCRIPTS = os.getenv("DOUYIN_AUTO_SAVE_TRANSCRIPTS", "true").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
TRANSCRIPT_DIR = os.getenv(
    "DOUYIN_TRANSCRIPT_DIR",
    str(_default_transcript_dir()),
)
