"""音频提取模块。

职责分离：
- httpx 负责网络下载（擅长处理Cookie/Headers/重定向）
- ffmpeg 负责媒体转码（擅长音视频处理）
- 两者不混用
"""

import logging
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import httpx

from ..config import AUDIO_BITRATE
from ..token_manager import DOUYIN_FIXED_USER_AGENT

logger = logging.getLogger("douyinmcp.video.audio")


async def download_video(
    video_url: str,
    cookies: str = "",
) -> str:
    """用httpx下载视频到临时文件。

    Args:
        video_url: 视频下载地址
        cookies: Cookie字符串（用于绕过防盗链）

    Returns:
        临时视频文件的绝对路径
    """
    # 生成唯一临时文件名
    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir) / f"douyin_{uuid.uuid4().hex[:8]}.mp4"

    headers = {
        "User-Agent": DOUYIN_FIXED_USER_AGENT,
        "Referer": "https://www.douyin.com/",
    }
    if cookies:
        headers["Cookie"] = cookies

    logger.info(f"开始下载视频: {video_url[:80]}...")

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=60,
    ) as client:
        async with client.stream("GET", video_url, headers=headers) as response:
            response.raise_for_status()
            with open(temp_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

    file_size_mb = temp_path.stat().st_size / (1024 * 1024)
    logger.info(f"视频下载完成: {temp_path} ({file_size_mb:.1f}MB)")
    return str(temp_path)


def extract_audio(
    video_path: str,
    output_format: str = "mp3",
) -> str:
    """用ffmpeg从视频中提取音频。

    输出 64kbps mp3，单声道 16kHz（语音识别最优参数）。
    10分钟音频约4.7MB，远低于硅基流动50MB限制。

    Args:
        video_path: 本地视频文件路径
        output_format: 输出格式（默认mp3）

    Returns:
        音频文件的绝对路径
    """
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 输出文件与视频同目录，相同前缀
    audio_path = video_file.with_suffix(f".{output_format}")

    cmd = [
        "ffmpeg",
        "-i", str(video_file),
        "-vn",                    # 不要视频流
        "-acodec", "libmp3lame",  # MP3编码器
        "-b:a", AUDIO_BITRATE,   # 码率（默认64k）
        "-ar", "16000",           # 采样率16kHz（语音识别标准）
        "-ac", "1",               # 单声道
        "-y",                     # 覆盖已有文件
        str(audio_path),
    ]

    logger.info(f"提取音频: {video_file.name} → {audio_path.name}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,  # 2分钟超时
    )

    if result.returncode != 0:
        error_msg = result.stderr[-500:] if result.stderr else "未知错误"
        raise RuntimeError(f"ffmpeg提取音频失败: {error_msg}")

    audio_size_mb = audio_path.stat().st_size / (1024 * 1024)
    logger.info(f"音频提取完成: {audio_path} ({audio_size_mb:.1f}MB)")
    return str(audio_path)


def get_audio_duration(audio_path: str) -> float:
    """用ffprobe获取音频时长（秒）。"""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired):
        return 0.0


def cleanup_temp_files(*paths: str) -> None:
    """清理临时文件。"""
    for path in paths:
        if not path:  # 跳过空字符串
            continue
        try:
            p = Path(path)
            if p.is_file():
                p.unlink()
                logger.debug(f"已清理: {p}")
        except OSError as e:
            logger.warning(f"清理失败 {path}: {e}")
