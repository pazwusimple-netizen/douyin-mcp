"""Data models for Douyin API responses."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, IntEnum


def _pick_first_url(image_data: dict) -> str:
    """从抖音图片对象中提取最合适的 URL。"""
    candidate_paths = [
        ("display_image", "url_list"),
        ("owner_watermark_image", "url_list"),
        ("download_url", "url_list"),
        ("origin_url", "url_list"),
        ("label_large", "url_list"),
    ]

    for outer_key, inner_key in candidate_paths:
        value = image_data.get(outer_key, {})
        if isinstance(value, dict) and value.get(inner_key):
            return value[inner_key][0]

    if image_data.get("url_list"):
        return image_data["url_list"][0]
    if image_data.get("download_url_list"):
        return image_data["download_url_list"][0]
    return ""


def _extract_image_urls(data: dict) -> list[str]:
    """兼容多种 aweme 图文结构，提取图片链接。"""
    image_urls = []

    candidate_lists = [
        data.get("images", []),
        data.get("image_infos", []),
        data.get("image_post_info", {}).get("images", []),
        data.get("image_post_info", {}).get("image_list", []),
    ]

    for items in candidate_lists:
        if not items:
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            url = _pick_first_url(item)
            if url:
                image_urls.append(url)
        if image_urls:
            break

    deduped = []
    seen = set()
    for url in image_urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


class SearchChannelType(str, Enum):
    """Search channel type enumeration."""
    GENERAL = "aweme_general"
    VIDEO = "aweme_video_web"
    USER = "aweme_user_web"
    LIVE = "aweme_live"


class SearchSortType(IntEnum):
    """Search sort type enumeration."""
    GENERAL = 0
    MOST_LIKE = 1
    LATEST = 2


class PublishTimeType(IntEnum):
    """Publish time filter enumeration."""
    UNLIMITED = 0
    ONE_DAY = 1
    ONE_WEEK = 7
    SIX_MONTH = 180


class HomeFeedTagIdType(IntEnum):
    """Home feed tag ID enumeration."""
    ALL = 0
    KNOWLEDGE = 300213
    SPORTS = 300207
    AUTO = 300218
    ANIME = 300206
    GAME = 300205
    MOVIE = 300215
    LIFE_VLOG = 300216
    TRAVEL = 300221
    MINI_DRAMA = 300214
    FOOD = 300204
    AGRICULTURE = 300219
    MUSIC = 300209
    ANIMAL = 300220
    PARENTING = 300217
    FASHION = 300222


@dataclass
class DouyinAweme:
    """Douyin video/aweme data model."""
    aweme_id: str = ""
    aweme_type: str = ""
    title: str = ""
    desc: str = ""
    create_time: str = ""
    liked_count: str = ""
    comment_count: str = ""
    share_count: str = ""
    collected_count: str = ""
    aweme_url: str = ""
    cover_url: str = ""
    video_download_url: str = ""
    video_duration: int = 0  # 视频时长（毫秒），来自 video.duration
    source_keyword: str = ""
    is_ai_generated: int = 0
    user_id: str = ""
    sec_uid: str = ""
    short_user_id: str = ""
    user_unique_id: str = ""
    nickname: str = ""
    avatar: str = ""
    user_signature: str = ""
    ip_location: str = ""
    image_urls: list[str] = field(default_factory=list)
    image_count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "DouyinAweme":
        """Create DouyinAweme from API response dict."""
        author = data.get("author", {})
        video = data.get("video", {})
        statistics = data.get("statistics", {})
        image_urls = _extract_image_urls(data)

        cover_url = ""
        if video.get("cover", {}).get("url_list"):
            cover_url = video["cover"]["url_list"][0]
        elif image_urls:
            cover_url = image_urls[0]

        download_url = ""
        play_addr = video.get("play_addr", {})
        if play_addr.get("url_list"):
            download_url = play_addr["url_list"][0]

        return cls(
            aweme_id=str(data.get("aweme_id", "")),
            aweme_type=str(data.get("aweme_type", "")),
            title=data.get("preview_title", "") or data.get("desc", ""),
            desc=data.get("desc", ""),
            create_time=str(data.get("create_time", "")),
            liked_count=str(statistics.get("digg_count", 0)),
            comment_count=str(statistics.get("comment_count", 0)),
            share_count=str(statistics.get("share_count", 0)),
            collected_count=str(statistics.get("collect_count", 0)),
            aweme_url=data.get("share_url", ""),
            cover_url=cover_url,
            video_download_url=download_url,
            video_duration=video.get("duration", 0),  # 视频时长（毫秒）
            source_keyword=data.get("source_keyword", ""),
            is_ai_generated=data.get("is_ai_generated", 0),
            user_id=str(author.get("uid", "")),
            sec_uid=author.get("sec_uid", ""),
            short_user_id=str(author.get("short_id", "")),
            user_unique_id=str(author.get("unique_id", "")),
            nickname=author.get("nickname", ""),
            avatar=author.get("avatar_thumb", {}).get("url_list", [""])[0] if author.get("avatar_thumb") else "",
            user_signature=author.get("signature", ""),
            ip_location=data.get("ip_label", ""),
            image_urls=image_urls,
            image_count=len(image_urls),
        )


@dataclass
class DouyinAwemeComment:
    """Douyin comment data model."""
    comment_id: str = ""
    aweme_id: str = ""
    content: str = ""
    create_time: str = ""
    sub_comment_count: str = ""
    parent_comment_id: str = ""
    reply_to_reply_id: str = ""
    like_count: str = ""
    pictures: str = ""
    ip_location: str = ""
    user_id: str = ""
    sec_uid: str = ""
    short_user_id: str = ""
    user_unique_id: str = ""
    nickname: str = ""
    avatar: str = ""
    user_signature: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "DouyinAwemeComment":
        """Create DouyinAwemeComment from API response dict."""
        user = data.get("user", {})

        pictures = []
        if data.get("image_list"):
            for img in data["image_list"]:
                if img.get("origin_url", {}).get("url_list"):
                    pictures.append(img["origin_url"]["url_list"][0])

        return cls(
            comment_id=str(data.get("cid", "")),
            aweme_id=str(data.get("aweme_id", "")),
            content=data.get("text", ""),
            create_time=str(data.get("create_time", "")),
            sub_comment_count=str(data.get("reply_comment_total", 0)),
            parent_comment_id=str(data.get("reply_id", "0")),
            reply_to_reply_id=str(data.get("reply_to_reply_id", "0")),
            like_count=str(data.get("digg_count", 0)),
            pictures=",".join(pictures),
            ip_location=data.get("ip_label", ""),
            user_id=str(user.get("uid", "")),
            sec_uid=user.get("sec_uid", ""),
            short_user_id=str(user.get("short_id", "")),
            user_unique_id=str(user.get("unique_id", "")),
            nickname=user.get("nickname", ""),
            avatar=user.get("avatar_thumb", {}).get("url_list", [""])[0] if user.get("avatar_thumb") else "",
            user_signature=user.get("signature", ""),
        )


@dataclass
class DouyinCreator:
    """Douyin creator/user data model."""
    user_id: str = ""
    sec_uid: str = ""
    nickname: str = ""
    avatar: str = ""
    ip_location: str = ""
    desc: str = ""
    gender: str = ""
    follows: str = ""
    fans: str = ""
    interaction: str = ""
    videos_count: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "DouyinCreator":
        """Create DouyinCreator from API response dict."""
        user = data.get("user", {})

        gender_map = {0: "unknown", 1: "male", 2: "female"}
        gender = gender_map.get(user.get("gender", 0), "unknown")

        return cls(
            user_id=str(user.get("uid", "")),
            sec_uid=user.get("sec_uid", ""),
            nickname=user.get("nickname", ""),
            avatar=user.get("avatar_larger", {}).get("url_list", [""])[0] if user.get("avatar_larger") else "",
            ip_location=user.get("ip_location", ""),
            desc=user.get("signature", ""),
            gender=gender,
            follows=str(user.get("following_count", 0)),
            fans=str(user.get("follower_count", 0)),
            interaction=str(user.get("total_favorited", 0)),
            videos_count=str(user.get("aweme_count", 0)),
        )


@dataclass
class VerifyParams:
    """Verification parameters for API requests."""
    ms_token: str = ""
    webid: str = ""
    verify_fp: str = ""
    s_v_web_id: str = ""


@dataclass
class TranscriptionResult:
    """语音转文字结果。"""
    text: str = ""              # 完整转写文本
    duration: float = 0.0       # 音频时长（秒）
    provider: str = ""          # 使用的ASR服务名
    warning: str = ""           # 警告信息（如"未检测到人声"）
