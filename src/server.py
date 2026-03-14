"""抖音 MCP Server — 提供15个工具访问抖音数据。

技术架构：
- fastmcp 框架处理 MCP 协议
- httpx 发送 HTTP 请求
- py_mini_racer 本地 V8 引擎生成 a_bogus 签名
- static_ffmpeg 自带 ffmpeg 二进制（Phase 2 音频提取用）
"""

import asyncio
import json
import logging
import random
import re
import threading
from urllib.parse import urlparse
from dataclasses import asdict
from datetime import datetime

import httpx
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from .client import DouYinApiClient
from .config import (
    COOKIE_STRING,
    COOKIE_PATH,
    DEFAULT_COOKIE_PATH,
    ASR_PROVIDER,
    AUDIO_CHUNK_DURATION,
    AUDIO_CHUNK_MAX_FILE_SIZE_MB,
    AUDIO_CHUNK_THRESHOLD,
    AUTO_SAVE_TRANSCRIPTS,
    MAX_AUDIO_DURATION,
    OCR_PROVIDER,
    TRANSCRIPT_DIR,
    DOWNLOAD_DIR,
)
from .errors import (
    CookieExpiredError,
    ASRNotConfiguredError,
    OCRNotConfiguredError,
    VideoDurationExceededError,
    FFmpegError,
    NoSpeechDetectedError,
    safe_tool_call,
)
from .cookies import normalize_cookie_string
from .models import (
    SearchChannelType,
    SearchSortType,
    PublishTimeType,
    HomeFeedTagIdType,
)


# 日志配置
logger = logging.getLogger("douyinmcp")


def _init_ffmpeg():
    """初始化 static-ffmpeg，确保 ffmpeg 二进制可用。"""
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        logger.info("✅ ffmpeg 已就绪（static-ffmpeg）")
    except ImportError:
        logger.warning("⚠️ static-ffmpeg 未安装，transcribe_video 将不可用")
    except Exception as e:
        logger.warning(f"⚠️ ffmpeg 初始化失败：{e}")


def _validate_cookie(raw: str, source: str) -> str:
    """验证 Cookie 格式并检查关键字段。"""
    normalized = normalize_cookie_string(raw)
    if not normalized.value:
        logger.warning(f"⚠️ {source} Cookie 为空或格式异常（未找到有效 key=value）。")
        return ""

    if normalized.invalid_parts:
        logger.warning(
            f"⚠️ {source} Cookie 中存在 {normalized.invalid_parts} 个无效片段，已自动忽略。"
        )

    # 检查必要字段
    if not normalized.has_session:
        logger.warning(
            f"⚠️ {source} 中未找到 sessionid，Cookie 可能无效。"
            "  请确保包含 sessionid 或 sessionid_ss 字段。"
        )
    else:
        logger.info(f"✅ Cookie 已加载（来源: {source}, {len(normalized.value)} 字符）")

    return normalized.value


def _candidate_cookie_files() -> list[Path]:
    """返回 Cookie 文件路径。"""
    return [Path(COOKIE_PATH).expanduser()]


def _cookie_files_signature() -> tuple[tuple[str, float], ...]:
    """用于检测 Cookie 文件是否更新的签名。"""
    if COOKIE_STRING:
        return tuple()

    signature: list[tuple[str, float]] = []
    for path in _candidate_cookie_files():
        try:
            mtime = path.stat().st_mtime if path.exists() else 0.0
        except OSError:
            mtime = 0.0
        signature.append((str(path), mtime))
    return tuple(signature)


def load_cookies() -> str:
    """加载 Cookie。

    优先级：环境变量 DOUYIN_COOKIE > DOUYIN_COOKIE_PATH 文件 > 旧版 ./cookies.txt。
    """
    # 优先级1：环境变量直传
    if COOKIE_STRING:
        cookie = _validate_cookie(COOKIE_STRING, source="环境变量 DOUYIN_COOKIE")
        if cookie:
            return cookie

    # 优先级2：文件
    for cookies_file in _candidate_cookie_files():
        if not cookies_file.exists():
            continue
        raw = cookies_file.read_text(encoding="utf-8").strip()
        cookie = _validate_cookie(raw, source=f"文件 {cookies_file}")
        if cookie:
            return cookie

    candidate_paths = ", ".join(str(p) for p in _candidate_cookie_files())
    logger.warning(
        f"⚠️ Cookie 未找到。\n"
        "  请运行: uv run login.py 扫码登录\n"
        f"  或手动将 Cookie 保存到: {candidate_paths}"
    )
    return ""


def _transcript_output_dir() -> Path:
    """返回转写文本输出目录。"""
    return Path(TRANSCRIPT_DIR).expanduser()


def _download_output_dir(save_dir: str = "") -> Path:
    """返回下载输出目录，优先使用显式传入，其次使用环境配置。"""
    if save_dir:
        return Path(save_dir).expanduser()
    return Path(DOWNLOAD_DIR).expanduser()


def _safe_filename(name: str, fallback: str = "transcript") -> str:
    """清理文件名中的非法字符，并限制长度。"""
    cleaned = re.sub(r'[\\/:*?"<>|]+', " ", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    if not cleaned:
        cleaned = fallback
    return cleaned[:80].rstrip()


def _persist_transcript(
    aweme_id: str,
    title: str,
    author: str,
    aweme_url: str,
    liked_count: str,
    collected_count: str,
    duration: float,
    provider: str,
    text: str,
    warning: str = "",
) -> tuple[str, str]:
    """将转写结果保存到本地 txt 文件。"""
    if not AUTO_SAVE_TRANSCRIPTS:
        return "", ""

    try:
        out_dir = _transcript_output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{_safe_filename(title, fallback=aweme_id)}_{aweme_id}.txt"
        output_path = out_dir / filename
        exported_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

        lines = [
            f"标题: {title}",
            f"作者: {author}",
            f"视频ID: {aweme_id}",
            f"视频链接: {aweme_url}",
            f"点赞: {liked_count}",
            f"收藏: {collected_count}",
            f"时长(秒): {duration:.1f}",
            f"ASR服务: {provider}",
            f"导出时间: {exported_at}",
        ]
        if warning:
            lines.append(f"提示: {warning}")
        lines.extend(["", "转写文本：", text])

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return str(output_path), ""
    except OSError as exc:
        logger.warning(f"⚠️ 转写文本保存失败（{aweme_id}）：{exc}")
        return "", str(exc)


def _guess_file_suffix(url: str, fallback: str = ".jpg") -> str:
    """从 URL 猜测文件后缀。"""
    path = urlparse(url).path.lower()
    for suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"):
        if path.endswith(suffix):
            return suffix
    return fallback


def _format_seconds(total_seconds: float) -> str:
    """格式化秒数为 HH:MM:SS。"""
    seconds = max(int(total_seconds), 0)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _should_chunk_audio(duration: float, file_size_mb: float) -> bool:
    """根据时长和体积决定是否切片。"""
    return duration > AUDIO_CHUNK_THRESHOLD or file_size_mb > AUDIO_CHUNK_MAX_FILE_SIZE_MB


def _merge_segment_transcripts(segments: list[dict]) -> str:
    """合并分段转写文本，并附带起始时间。"""
    valid_segments = [segment for segment in segments if segment.get("text", "").strip()]
    if not valid_segments:
        return ""
    if len(valid_segments) == 1:
        return valid_segments[0]["text"].strip()

    lines = []
    for segment in valid_segments:
        start_at = _format_seconds(segment.get("start_seconds", 0))
        lines.append(f"[{start_at}] {segment['text'].strip()}")
    return "\n\n".join(lines)


def _persist_ocr_result(
    base_dir: Path,
    aweme_id: str,
    title: str,
    results: list[dict],
) -> tuple[str, str]:
    """将 OCR 结果保存为本地文本和 JSON 文件。"""
    try:
        all_text = []
        payload = {
            "aweme_id": aweme_id,
            "title": title,
            "results": results,
        }

        for item in results:
            all_text.append(f"# {Path(item['image_path']).name}")
            all_text.append(item.get("text", "").strip())
            all_text.append("")

        text_path = base_dir / "ocr.txt"
        json_path = base_dir / "ocr.json"
        text_path.write_text("\n".join(all_text).strip() + "\n", encoding="utf-8")
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(text_path), str(json_path)
    except OSError as exc:
        logger.warning(f"⚠️ OCR 结果保存失败（{aweme_id}）：{exc}")
        return "", ""


async def _reset_client_cache() -> None:
    """清空缓存的 API client，供 Cookie 更新或退出登录后复用。"""
    global _client, _cookie_signature

    old_client: Optional[DouYinApiClient] = None
    with _client_lock:
        old_client = _client
        _client = None
        _cookie_signature = tuple()

    if old_client is not None:
        try:
            await old_client.close()
        except Exception:
            pass


# ====== 初始化 ======

# 确保 ffmpeg 可用
_init_ffmpeg()

# MCP 服务器实例
mcp = FastMCP(
    name="Douyin MCP",
    instructions="""
    抖音 MCP Server — 让AI助手能读懂抖音。

    可用工具（共15个）：
    📊 数据获取：
    - check_login_status: 检查Cookie登录状态
    - logout: 清除本地 Cookie 文件，退出当前登录
    - search_videos: 关键词搜索视频
    - get_video_detail: 获取视频详情（点赞/评论/分享/收藏/时长）
    - get_video_comments: 获取视频评论
    - get_sub_comments: 获取评论回复
    - get_user_info: 获取用户资料
    - get_user_posts: 获取用户作品列表
    - get_homefeed: 获取推荐视频流

    🔗 链接解析：
    - resolve_share_url: 解析分享短链接

    📥 媒体下载：
    - download_video: 下载视频到本地并返回视频信息
    - download_aweme_images: 下载图文作品中的全部图片
    - ocr_aweme_images: 下载并 OCR 识别图文图片内容

    🔊 语音转文字：
    - transcribe_video: 视频语音转文字
    - batch_transcribe: 批量搜索并转写视频，用于知识提取

    配置方式：
    - Cookie: 默认保存到 ~/.config/douyinmcp/cookies.txt（可用 DOUYIN_COOKIE_PATH 覆盖）
    - ASR: 通过环境变量配置 ASR_PROVIDER 和对应 API Key
    - 转写文本: 默认保存到 ~/Downloads/douyinmcp/transcripts（可用 DOUYIN_TRANSCRIPT_DIR 覆盖）
    - 下载目录: 默认保存到 ~/Downloads/douyinmcp（可用 DOUYIN_DOWNLOAD_DIR 覆盖）

    注意：签名通过本地 V8 引擎生成，无需外部签名服务。
    """,
)

# 全局 API 客户端实例（带并发锁的热重载机制）
_client: Optional[DouYinApiClient] = None
_cookie_signature: tuple[tuple[str, float], ...] = tuple()
_client_lock = threading.Lock()


def get_client() -> DouYinApiClient:
    """获取或创建 API 客户端实例。

    自动检测 Cookie 文件是否更新，若有更新则静默重建 Client。
    使用 threading.Lock 防止并发工具调用时的竞态条件。
    """
    global _client, _cookie_signature

    with _client_lock:
        current_signature = _cookie_files_signature()
        if _client is not None and current_signature != _cookie_signature:
            logger.info("🔄 检测到 Cookie 文件更新，重新加载")
            # 异步关闭旧 client 的连接池
            old_client = _client
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(old_client.close())
                else:
                    loop.run_until_complete(old_client.close())
            except Exception:
                pass  # 关闭失败不影响新 client 创建
            _client = None

        if _client is None:
            cookies = load_cookies()
            if not cookies:
                raise CookieExpiredError()
            _client = DouYinApiClient(cookies=cookies)
            _cookie_signature = current_signature

    return _client


# ====== MCP 工具定义 ======


@mcp.tool
@safe_tool_call
async def check_login_status() -> dict:
    """检查当前抖音Cookie的登录状态。

    Returns:
        dict: 包含 logged_in 布尔值
    """
    client = get_client()
    is_logged_in = await client.check_login_status()
    return {"logged_in": is_logged_in}


@mcp.tool
@safe_tool_call
async def logout() -> dict:
    """退出抖音登录，清除本地 Cookie 文件。

    Returns:
        dict: 包含是否成功、删除的文件路径和说明信息
    """
    deleted_files = []
    delete_errors = []

    for cookie_file in _candidate_cookie_files():
        if not cookie_file.exists():
            continue
        try:
            cookie_file.unlink()
            deleted_files.append(str(cookie_file))
        except OSError as exc:
            delete_errors.append(f"{cookie_file}: {exc}")

    await _reset_client_cache()

    if COOKIE_STRING:
        return {
            "success": False,
            "deleted_files": deleted_files,
            "errors": delete_errors,
            "requires_manual_action": True,
            "message": (
                "当前登录态来自环境变量 DOUYIN_COOKIE。"
                "工具无法替你删除 MCP 配置里的环境变量。"
                "请在客户端配置中移除 DOUYIN_COOKIE 后重启 MCP。"
            ),
        }

    if delete_errors:
        return {
            "success": False,
            "deleted_files": deleted_files,
            "errors": delete_errors,
            "requires_manual_action": False,
            "message": "部分 Cookie 文件删除失败，请查看 errors。",
        }

    return {
        "success": True,
        "deleted_files": deleted_files,
        "errors": [],
        "requires_manual_action": False,
        "message": "已清除本地 Cookie 文件。下次使用时需要重新登录。",
    }


@mcp.tool
@safe_tool_call
async def search_videos(
    keyword: str,
    offset: int = 0,
    count: int = 10,
    search_channel: str = "general",
    sort_type: int = 0,
    publish_time: int = 0,
) -> dict:
    """根据关键词搜索抖音视频。

    Args:
        keyword: 搜索关键词
        offset: 分页偏移量（默认0）
        count: 每页结果数（默认10，最大20）
        search_channel: 搜索类型 - "general"(综合), "video"(视频), "user"(用户), "live"(直播)
        sort_type: 排序方式 - 0(综合), 1(点赞最多), 2(最新)
        publish_time: 时间筛选 - 0(不限), 1(1天内), 7(1周内), 180(半年内)

    Returns:
        dict: 包含搜索结果的视频列表
    """
    client = get_client()

    channel_map = {
        "general": SearchChannelType.GENERAL,
        "video": SearchChannelType.VIDEO,
        "user": SearchChannelType.USER,
        "live": SearchChannelType.LIVE,
    }
    channel = channel_map.get(search_channel.lower(), SearchChannelType.GENERAL)

    sort_enum = SearchSortType(sort_type) if sort_type in [0, 1, 2] else SearchSortType.GENERAL
    time_enum = PublishTimeType(publish_time) if publish_time in [0, 1, 7, 180] else PublishTimeType.UNLIMITED

    # 首次搜索
    result = await client.search_info_by_keyword(
        keyword=keyword,
        offset=offset,
        count=count,
        search_channel=channel,
        sort_type=sort_enum,
        publish_time=time_enum,
    )

    # ========== verify_check 检测与自动重试 ==========
    nil_info = result.get("search_nil_info", {})
    if nil_info.get("search_nil_type") == "verify_check":
        logger.warning(f"⚠️ 搜索「{keyword}」被 verify_check 拦截，尝试刷新 token 后重试…")

        # 刷新 verify_params（重新获取 msToken/webid/verifyFp）
        client.verify_params = None
        await client._init_verify_params()

        # 等待 8~15 秒后重试（留足冷却时间）
        retry_wait = random.uniform(8.0, 15.0)
        logger.info(f"⏳ 等待 {retry_wait:.1f} 秒后重试搜索…")
        await asyncio.sleep(retry_wait)

        # 重试搜索
        result = await client.search_info_by_keyword(
            keyword=keyword,
            offset=offset,
            count=count,
            search_channel=channel,
            sort_type=sort_enum,
            publish_time=time_enum,
        )

        # 如果重试后仍被拦截，自动回退到浏览器搜索
        nil_info_retry = result.get("search_nil_info", {})
        if nil_info_retry.get("search_nil_type") == "verify_check":
            logger.warning(f"⚠️ 搜索「{keyword}」HTTP重试仍被拦截，回退到浏览器搜索…")
            try:
                from .browser_search import get_browser_search_provider
                provider = await get_browser_search_provider()
                browser_result = await provider.search(keyword, count)
                if browser_result.get("results"):
                    logger.info(f"✅ 浏览器搜索「{keyword}」成功，获得 {browser_result['count']} 条结果")
                    return browser_result
                else:
                    logger.warning(f"❌ 浏览器搜索「{keyword}」也未获取到结果")
            except Exception as e:
                logger.error(f"❌ 浏览器搜索失败: {e}")
            result["_verify_check_warning"] = (
                "搜索被抖音风控系统拦截（verify_check），浏览器搜索也未成功。"
                "建议：1) 等待几分钟后重试 "
                "2) 更换Cookie重新登录"
            )
        else:
            logger.info(f"✅ 搜索「{keyword}」重试成功")

    return result


@mcp.tool
@safe_tool_call
async def get_video_detail(aweme_id: str) -> dict:
    """获取抖音视频的详细信息。

    Args:
        aweme_id: 视频ID（数字字符串）

    Returns:
        dict: 包含视频标题、描述、统计数据（点赞/评论/分享）、
              作者信息、时长(毫秒)、下载链接等
    """
    client = get_client()
    video = await client.get_video_by_id(aweme_id)
    if video:
        return {"success": True, "video": asdict(video)}
    return {"success": False, "error": "视频未找到"}


@mcp.tool
@safe_tool_call
async def get_video_comments(
    aweme_id: str,
    cursor: int = 0,
    count: int = 20,
    source_keyword: str = "",
) -> dict:
    """获取抖音视频的评论列表。

    Args:
        aweme_id: 视频ID
        cursor: 分页游标（默认0）
        count: 每页评论数（默认20）
        source_keyword: 可选搜索关键词（用于referer）

    Returns:
        dict: 包含评论列表和分页元数据
    """
    client = get_client()
    comments, metadata = await client.get_aweme_comments(
        aweme_id=aweme_id,
        cursor=cursor,
        count=count,
        source_keyword=source_keyword,
    )
    return {
        "success": True,
        "comments": [asdict(c) for c in comments],
        "metadata": metadata,
    }


@mcp.tool
@safe_tool_call
async def get_sub_comments(
    comment_id: str,
    cursor: int = 0,
    count: int = 20,
    source_keyword: str = "",
) -> dict:
    """获取抖音评论的回复（子评论）。

    Args:
        comment_id: 父评论ID
        cursor: 分页游标（默认0）
        count: 每页回复数（默认20）
        source_keyword: 可选搜索关键词（用于referer）

    Returns:
        dict: 包含回复列表和分页元数据
    """
    client = get_client()
    comments, metadata = await client.get_sub_comments(
        comment_id=comment_id,
        cursor=cursor,
        count=count,
        source_keyword=source_keyword,
    )
    return {
        "success": True,
        "comments": [asdict(c) for c in comments],
        "metadata": metadata,
    }


@mcp.tool
@safe_tool_call
async def get_user_info(sec_user_id: str) -> dict:
    """获取抖音用户的个人资料。

    Args:
        sec_user_id: 用户安全ID（以MS4wLjABAAAA开头）

    Returns:
        dict: 包含昵称、头像、粉丝数、关注数、总获赞、作品数等
    """
    client = get_client()
    user = await client.get_user_info(sec_user_id)
    if user:
        return {"success": True, "user": asdict(user)}
    return {"success": False, "error": "用户未找到"}


@mcp.tool
@safe_tool_call
async def get_user_posts(
    sec_user_id: str,
    max_cursor: str = "0",
    count: int = 18,
) -> dict:
    """获取抖音用户发布的视频列表。

    Args:
        sec_user_id: 用户安全ID
        max_cursor: 分页游标（默认"0"）
        count: 每页视频数（默认18）

    Returns:
        dict: 包含视频列表和分页信息
    """
    client = get_client()
    return await client.get_user_aweme_posts(
        sec_user_id=sec_user_id,
        max_cursor=max_cursor,
        count=count,
    )


@mcp.tool
@safe_tool_call
async def get_homefeed(
    tag: str = "all",
    count: int = 20,
    refresh_index: int = 0,
) -> dict:
    """获取抖音推荐视频流。

    Args:
        tag: 内容分类 - "all"(全部), "knowledge"(知识), "sports"(体育),
             "auto"(汽车), "anime"(动漫), "game"(游戏), "movie"(影视),
             "life_vlog"(生活), "travel"(旅行), "mini_drama"(短剧),
             "food"(美食), "agriculture"(三农), "music"(音乐),
             "animal"(动物), "parenting"(亲子), "fashion"(时尚)
        count: 返回视频数（默认20）
        refresh_index: 刷新索引，用于分页（默认0）

    Returns:
        dict: 包含推荐视频列表
    """
    client = get_client()

    tag_map = {
        "all": HomeFeedTagIdType.ALL,
        "knowledge": HomeFeedTagIdType.KNOWLEDGE,
        "sports": HomeFeedTagIdType.SPORTS,
        "auto": HomeFeedTagIdType.AUTO,
        "anime": HomeFeedTagIdType.ANIME,
        "game": HomeFeedTagIdType.GAME,
        "movie": HomeFeedTagIdType.MOVIE,
        "life_vlog": HomeFeedTagIdType.LIFE_VLOG,
        "travel": HomeFeedTagIdType.TRAVEL,
        "mini_drama": HomeFeedTagIdType.MINI_DRAMA,
        "food": HomeFeedTagIdType.FOOD,
        "agriculture": HomeFeedTagIdType.AGRICULTURE,
        "music": HomeFeedTagIdType.MUSIC,
        "animal": HomeFeedTagIdType.ANIMAL,
        "parenting": HomeFeedTagIdType.PARENTING,
        "fashion": HomeFeedTagIdType.FASHION,
    }
    tag_enum = tag_map.get(tag.lower(), HomeFeedTagIdType.ALL)

    return await client.get_homefeed_aweme_list(
        tag_id=tag_enum,
        count=count,
        refresh_index=refresh_index,
    )

# ====== 登录工具 ======


@mcp.tool
@safe_tool_call
async def get_login_qrcode() -> dict:
    """获取抖音扫码登录二维码。

    当 Cookie 失效或未登录时，AI 助手可调用此工具启动后台二维码登录流程。
    二维码会打印到终端中；扫码成功后 Cookie 会自动保存，无需重启服务。

    Returns:
        dict: 包含登录状态和提示信息
    """
    import subprocess
    import sys

    project_root = Path(__file__).parent.parent
    login_script = project_root / "login.py"

    if not login_script.exists():
        return {
            "logged_in": False,
            "message": (
                "❌ 未找到 login.py 登录脚本。\n"
                "请在终端运行: uv run login.py 进行扫码登录"
            ),
        }

    # 尝试启动 login.py 子进程（非阻塞）
    try:
        subprocess.Popen(
            [sys.executable, str(login_script), "--api"],
            cwd=str(project_root),
        )
        return {
            "logged_in": False,
            "launched": True,
            "mode": "api_qrcode",
            "cookie_path": str(Path(COOKIE_PATH).expanduser()),
            "message": (
                "📱 已在后台启动登录程序！\n\n"
                "请切换到终端窗口，你会看到一个二维码：\n"
                "1. 打开手机抖音 App\n"
                "2. 扫描终端中的二维码\n"
                "3. 手机上确认登录\n"
                "4. 终端会显示 🎉 成功\n\n"
                "登录完成后回来告诉我，我会自动使用新的 Cookie。"
            ),
        }
    except Exception as e:
        return {
            "logged_in": False,
            "launched": False,
            "mode": "api_qrcode",
            "cookie_path": str(Path(COOKIE_PATH).expanduser()),
            "message": (
                f"⚠️ 启动登录程序失败（{e}）。\n"
                "请手动在终端运行:\n"
                f"  cd {project_root}\n"
                "  uv run login.py --api"
            ),
        }





# ====== Phase 2 新工具 ======


def _get_asr_provider():
    """根据配置获取 ASR Provider 实例。

    支持的 ASR_PROVIDER 值：
    - siliconflow（默认）：硅基流动 SenseVoice
    - volcengine：火山引擎
    - openai：OpenAI Whisper（或任何 OpenAI 兼容服务）
    - custom：通用自定义接口（需设置 ASR_API_URL + ASR_API_KEY）
    """
    provider_name = ASR_PROVIDER.lower().strip()

    if provider_name == "siliconflow":
        from .asr.siliconflow import SiliconFlowProvider
        return SiliconFlowProvider()
    elif provider_name == "volcengine":
        from .asr.volcengine import VolcengineProvider
        return VolcengineProvider()
    elif provider_name in ("openai", "custom"):
        from .asr.custom import CustomProvider
        return CustomProvider()
    else:
        logger.warning(
            f"⚠️ ASR_PROVIDER='{ASR_PROVIDER}' 未识别，回退到 siliconflow。"
            f" 支持的值：siliconflow, volcengine, openai, custom"
        )
        from .asr.siliconflow import SiliconFlowProvider
        return SiliconFlowProvider()


@mcp.tool
@safe_tool_call
async def resolve_share_url(share_url: str) -> dict:
    """解析抖音分享短链接，获取视频ID和详情。

    支持解析 https://v.douyin.com/xxx 形式的分享链接。
    解析出 aweme_id 后自动获取视频详情。

    Args:
        share_url: 抖音分享链接（如 https://v.douyin.com/iRNBho5G/）

    Returns:
        dict: 包含 aweme_id 和视频详情
    """
    from .video.resolver import resolve_share_url as _resolve

    aweme_id = await _resolve(share_url)

    # 解析成功后自动获取视频详情
    client = get_client()
    video = await client.get_video_by_id(aweme_id)

    result = {"success": True, "aweme_id": aweme_id}
    if video:
        result["video"] = asdict(video)
    return result


async def _download_aweme_images_internal(aweme_id: str, save_dir: str = "") -> dict:
    """下载图文作品中的全部图片，并生成 manifest。"""
    from .video.audio import download_to_path

    client = get_client()
    video = await client.get_video_by_id(aweme_id)
    if not video:
        return {"success": False, "error": f"作品 {aweme_id} 未找到"}

    if not video.image_urls:
        return {"success": False, "error": "该作品不是图文，或暂未解析到图片链接"}

    root_dir = _download_output_dir(save_dir)
    bundle_dir = root_dir / f"{_safe_filename(video.title, fallback=aweme_id)}_{aweme_id}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []
    for index, image_url in enumerate(video.image_urls, start=1):
        suffix = _guess_file_suffix(image_url)
        target_path = bundle_dir / f"{index:02d}{suffix}"
        await download_to_path(image_url, str(target_path), cookies=client.cookies)
        image_paths.append(str(target_path))

    manifest = {
        "aweme_id": aweme_id,
        "title": video.title,
        "author": video.nickname,
        "aweme_url": video.aweme_url,
        "image_count": len(image_paths),
        "image_paths": image_paths,
        "image_urls": video.image_urls,
    }
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "success": True,
        "directory": str(bundle_dir),
        "manifest_path": str(manifest_path),
        "image_count": len(image_paths),
        "image_paths": image_paths,
        "video": {
            "title": video.title,
            "aweme_id": aweme_id,
            "aweme_url": video.aweme_url,
            "author": video.nickname,
            "liked_count": video.liked_count,
            "comment_count": video.comment_count,
            "share_count": video.share_count,
            "collected_count": video.collected_count,
        },
    }


@mcp.tool
@safe_tool_call
async def download_video(aweme_id: str, save_dir: str = "") -> dict:
    """下载抖音视频到本地，并返回视频的完整信息和链接。

    下载后返回本地文件路径、视频链接、以及点赞/评论/收藏等统计数据。

    Args:
        aweme_id: 视频ID（数字字符串）
        save_dir: 保存目录（默认走 DOUYIN_DOWNLOAD_DIR，未配置时为 ~/Downloads）

    Returns:
        dict: 包含 file_path(本地路径), file_size_mb, video(视频详情)
    """
    import re
    from .video.audio import download_video as _download

    # 获取视频详情
    client = get_client()
    video = await client.get_video_by_id(aweme_id)
    if not video:
        return {"success": False, "error": f"视频 {aweme_id} 未找到"}

    if not video.video_download_url:
        return {"success": False, "error": "无法获取视频下载地址"}

    # 确定保存目录
    save_path = _download_output_dir(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    # 用视频标题生成文件名（清理非法字符）
    safe_title = re.sub(r'[\\/:*?"<>|#]', '', video.title or "抖音视频")
    safe_title = safe_title.strip()[:80]  # 限制长度
    if not safe_title:
        safe_title = f"douyin_{aweme_id}"
    target_file = save_path / f"{safe_title}.mp4"

    # 如果文件已存在，添加序号
    counter = 1
    while target_file.exists():
        target_file = save_path / f"{safe_title}_{counter}.mp4"
        counter += 1

    # 下载到临时文件
    temp_path = await _download(video.video_download_url, cookies=client.cookies)

    # 移动到目标位置
    import shutil
    shutil.move(temp_path, str(target_file))

    file_size_mb = target_file.stat().st_size / (1024 * 1024)
    duration_sec = round(video.video_duration / 1000, 1)  # 毫秒转秒

    return {
        "success": True,
        "file_path": str(target_file),
        "file_size_mb": round(file_size_mb, 2),
        "video": {
            "title": video.title,
            "aweme_id": aweme_id,
            "aweme_url": video.aweme_url,
            "duration_seconds": duration_sec,
            "author": video.nickname,
            "liked_count": video.liked_count,
            "comment_count": video.comment_count,
            "share_count": video.share_count,
            "collected_count": video.collected_count,
            "cover_url": video.cover_url,
            "video_download_url": video.video_download_url,
        },
    }


@mcp.tool
@safe_tool_call
async def download_aweme_images(aweme_id: str, save_dir: str = "") -> dict:
    """下载抖音图文作品中的全部图片。

    Args:
        aweme_id: 作品ID（数字字符串）
        save_dir: 保存目录（默认走 DOUYIN_DOWNLOAD_DIR，未配置时为 ~/Downloads）

    Returns:
        dict: 包含目录、图片路径和 manifest 文件
    """
    return await _download_aweme_images_internal(aweme_id, save_dir=save_dir)


@mcp.tool
@safe_tool_call
async def ocr_aweme_images(aweme_id: str, save_dir: str = "") -> dict:
    """下载并 OCR 识别抖音图文作品中的图片文字。

    Args:
        aweme_id: 作品ID（数字字符串）
        save_dir: 保存目录（默认走 DOUYIN_DOWNLOAD_DIR，未配置时为 ~/Downloads）

    Returns:
        dict: 包含 OCR 文本、逐图结果和本地保存路径
    """
    if OCR_PROVIDER != "rapidocr":
        raise OCRNotConfiguredError(OCR_PROVIDER)

    from .ocr import run_ocr

    download_result = await _download_aweme_images_internal(aweme_id, save_dir=save_dir)
    if not download_result.get("success"):
        return download_result

    results = []
    for image_path in download_result["image_paths"]:
        results.append(run_ocr(image_path))

    text_path, json_path = _persist_ocr_result(
        Path(download_result["directory"]),
        aweme_id=aweme_id,
        title=download_result["video"]["title"],
        results=results,
    )

    return {
        "success": True,
        "aweme_id": aweme_id,
        "directory": download_result["directory"],
        "image_count": download_result["image_count"],
        "results": results,
        "ocr_text_path": text_path,
        "ocr_json_path": json_path,
    }


# ====== 转写核心逻辑（供 transcribe_video 和 batch_transcribe 复用） ======


async def _transcribe_single(aweme_id: str) -> dict:
    """转写单个视频的内部实现。

    返回转写结果 dict，如果失败抛出异常。
    """
    from .video.audio import (
        download_video as _download,
        extract_audio,
        get_audio_duration,
        cleanup_temp_files,
        split_audio,
    )

    # 检查 ASR 配置
    provider = _get_asr_provider()
    if not provider.is_configured():
        raise ASRNotConfiguredError(ASR_PROVIDER)

    # 获取视频详情
    client = get_client()
    video = await client.get_video_by_id(aweme_id)
    if not video:
        return {"success": False, "error": f"视频 {aweme_id} 未找到"}

    # 检查时长限制
    duration_sec = video.video_duration / 1000
    if duration_sec > MAX_AUDIO_DURATION:
        raise VideoDurationExceededError(int(duration_sec), MAX_AUDIO_DURATION)

    if not video.video_download_url:
        return {"success": False, "error": "无法获取视频下载地址"}

    video_path = ""
    audio_path = ""
    segment_paths: list[str] = []

    try:
        # 下载视频
        video_path = await _download(
            video.video_download_url,
            cookies=client.cookies,
        )

        # 提取音频
        try:
            audio_path = extract_audio(video_path)
        except RuntimeError as e:
            raise FFmpegError(str(e))

        # 立即清理视频文件
        cleanup_temp_files(video_path)
        video_path = ""

        audio_duration = get_audio_duration(audio_path)
        audio_size_mb = Path(audio_path).stat().st_size / (1024 * 1024)

        segment_results = []
        if _should_chunk_audio(audio_duration, audio_size_mb):
            logger.info(
                "长音频触发切片转写: duration=%.1fs, size=%.1fMB",
                audio_duration,
                audio_size_mb,
            )
            segment_paths = split_audio(audio_path, segment_duration=AUDIO_CHUNK_DURATION)
        else:
            segment_paths = [audio_path]

        current_start = 0.0
        for segment_path in segment_paths:
            segment_duration = get_audio_duration(segment_path)
            asr_result = await provider.transcribe(segment_path)
            segment_results.append({
                "path": segment_path,
                "duration": segment_duration,
                "start_seconds": current_start,
                "text": asr_result.text.strip(),
            })
            current_start += segment_duration

        save_warning = ""
        merged_text = _merge_segment_transcripts(segment_results)
        segment_count = len(segment_paths)

        if not merged_text:
            saved_path, save_warning = _persist_transcript(
                aweme_id=aweme_id,
                title=video.title,
                author=video.nickname,
                aweme_url=video.aweme_url,
                liked_count=video.liked_count,
                collected_count=video.collected_count,
                duration=audio_duration,
                provider=provider.name,
                text="",
                warning="未检测到人声，可能是纯音乐或纯画面视频",
            )
            return {
                "success": True,
                "text": "",
                "duration": audio_duration,
                "provider": provider.name,
                "warning": "未检测到人声，可能是纯音乐或纯画面视频",
                "video_title": video.title,
                "author": video.nickname,
                "aweme_url": video.aweme_url,
                "liked_count": video.liked_count,
                "collected_count": video.collected_count,
                "segmented": segment_count > 1,
                "segment_count": segment_count,
                "saved_path": saved_path,
                "save_error": save_warning,
            }

        saved_path, save_warning = _persist_transcript(
            aweme_id=aweme_id,
            title=video.title,
            author=video.nickname,
            aweme_url=video.aweme_url,
            liked_count=video.liked_count,
            collected_count=video.collected_count,
            duration=audio_duration,
            provider=provider.name,
            text=merged_text,
        )

        return {
            "success": True,
            "text": merged_text,
            "duration": audio_duration,
            "provider": provider.name,
            "video_title": video.title,
            # 补全字段，避免 batch_transcribe 二次调用 get_video_by_id
            "author": video.nickname,
            "aweme_url": video.aweme_url,
            "liked_count": video.liked_count,
            "collected_count": video.collected_count,
            "segmented": segment_count > 1,
            "segment_count": segment_count,
            "saved_path": saved_path,
            "save_error": save_warning,
        }

    finally:
        cleanup_temp_files(video_path, audio_path, *segment_paths)
        if audio_path and segment_paths and audio_path != segment_paths[0]:
            cleanup_temp_files(str(Path(audio_path).with_name(f"{Path(audio_path).stem}_segments")))


@mcp.tool
@safe_tool_call
async def transcribe_video(aweme_id: str) -> dict:
    """将抖音视频中的语音转化为文字。

    完整流程：获取视频详情 → 下载视频 → 提取音频(mp3) → 调用ASR → 返回文字
    注意：只接受 aweme_id。如果用户给了分享链接，请先调用 resolve_share_url。

    Args:
        aweme_id: 视频ID（数字字符串）

    Returns:
        dict: 包含 text(转写文本), duration(时长), provider(服务商), saved_path(本地文本路径)
    """
    return await _transcribe_single(aweme_id)


@mcp.tool
@safe_tool_call
async def batch_transcribe(
    keyword: str,
    count: int = 3,
    sort_type: int = 1,
) -> dict:
    """批量搜索并转写抖音视频，用于从视频中提取某领域的知识。

    流程：搜索关键词 → 获取前N个视频 → 逐个转写语音为文字 → 汇总返回。
    适合场景：想从抖音教程视频中批量获取某领域知识（如美妆教程、烹饪技巧等）。

    Args:
        keyword: 搜索关键词（如"泰式千金妆教程"、"红烧肉做法"）
        count: 转写视频数量（默认3，最大5，防止耗时过长）
        sort_type: 排序方式 - 0(综合), 1(点赞最多，默认，优先高质量内容), 2(最新)

    Returns:
        dict: 包含 results(转写结果列表)、failed(失败列表) 和本地保存路径
    """
    # 限制数量，防止耗时过久和API消耗过大
    count = min(max(count, 1), 5)

    # 第1步：搜索视频
    client = get_client()

    # 映射排序类型
    sort_map = {
        0: SearchSortType.GENERAL,
        1: SearchSortType.MOST_LIKE,
        2: SearchSortType.LATEST,
    }
    sort_enum = sort_map.get(sort_type, SearchSortType.MOST_LIKE)

    search_result = await client.search_info_by_keyword(
        keyword=keyword,
        count=count + 2,  # 多搜几个，防止有些视频转写失败
        search_channel=SearchChannelType.VIDEO,
        sort_type=sort_enum,
    )

    # 提取搜索到的视频列表
    video_list = search_result.get("data", [])
    if not video_list:
        return {
            "success": True,
            "keyword": keyword,
            "total_transcribed": 0,
            "results": [],
            "failed": [],
            "message": f"未搜索到关键词 '{keyword}' 相关视频",
        }

    results = []
    failed = []
    transcribed = 0

    for item in video_list:
        if transcribed >= count:
            break

        aweme_id = item.get("aweme_info", {}).get("aweme_id") or item.get("aweme_id", "")
        title = item.get("aweme_info", {}).get("desc") or item.get("desc", "未知标题")

        if not aweme_id:
            continue

        # 防风控随机延迟（从第2个视频开始）
        if transcribed > 0:
            delay = random.uniform(2.0, 4.0)
            logger.info(f"[batch_transcribe] 防风控延迟 {delay:.1f}s ...")
            await asyncio.sleep(delay)

        logger.info(f"[batch_transcribe] 正在转写 {transcribed + 1}/{count}: {title[:30]}...")

        try:
            result = await _transcribe_single(aweme_id)

            if result.get("success") and result.get("text"):
                # 直接使用 _transcribe_single 返回的补全字段，无需二次请求
                results.append({
                    "title": result.get("video_title", title),
                    "author": result.get("author", ""),
                    "aweme_id": aweme_id,
                    "aweme_url": result.get("aweme_url", ""),
                    "liked_count": result.get("liked_count", ""),
                    "collected_count": result.get("collected_count", ""),
                    "duration_seconds": round(result.get("duration", 0), 1),
                    "transcript": result["text"],
                    "segmented": result.get("segmented", False),
                    "segment_count": result.get("segment_count", 1),
                    "saved_path": result.get("saved_path", ""),
                    "save_error": result.get("save_error", ""),
                })
                transcribed += 1
            else:
                # 没有识别到文字（纯音乐等），跳过不计入失败
                logger.info(f"[batch_transcribe] 跳过无人声视频: {title[:30]}")
                continue

        except Exception as e:
            failed.append({
                "aweme_id": aweme_id,
                "title": title,
                "error": str(e),
            })
            logger.warning(f"[batch_transcribe] 转写失败 {aweme_id}: {e}")

    return {
        "success": True,
        "keyword": keyword,
        "total_transcribed": len(results),
        "transcript_dir": str(_transcript_output_dir()) if AUTO_SAVE_TRANSCRIPTS else "",
        "results": results,
        "failed": failed,
    }
