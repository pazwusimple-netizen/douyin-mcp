"""Douyin API Client implementation."""

import json
import urllib.parse
from typing import Optional, Tuple, List, Dict, Any

import httpx

from .models import (
    DouyinAweme,
    DouyinAwemeComment,
    DouyinCreator,
    VerifyParams,
    SearchChannelType,
    SearchSortType,
    PublishTimeType,
    HomeFeedTagIdType,
)
from .token_manager import (
    get_common_verify_params,
    DOUYIN_FIXED_USER_AGENT,
)
from .sign import get_a_bogus, SignError


class DataFetchError(Exception):
    """Exception raised when data fetching fails."""
    pass


class IPBlockError(Exception):
    """Exception raised when IP is blocked."""
    pass


class DouYinApiClient:
    """Douyin API Client for accessing Douyin data."""

    BASE_URL = "https://www.douyin.com"

    # Common request parameters
    COMMON_PARAMS = {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "publish_video_strategy_type": "2",
        "update_version_code": "170400",
        "pc_client_type": "1",
        "version_code": "170400",
        "version_name": "17.4.0",
        "cookie_enabled": "true",
        "screen_width": "2560",
        "screen_height": "1440",
        "browser_language": "zh-CN",
        "browser_platform": "MacIntel",
        "browser_name": "Chrome",
        "browser_version": "135.0.0.0",
        "browser_online": "true",
        "engine_name": "Blink",
        "engine_version": "135.0.0.0",
        "os_name": "Mac+OS",
        "os_version": "10.15.7",
        "cpu_core_num": "8",
        "device_memory": "8",
        "platform": "PC",
        "downlink": "4.45",
        "effective_type": "4g",
        "round_trip_time": "100",
    }

    def __init__(
        self,
        cookies: str = "",
        proxy: Optional[str] = None,
    ):
        """
        初始化抖音 API 客户端。

        Args:
            cookies: Cookie 字符串
            proxy: 可选代理 URL
        """
        self.cookies = cookies
        self.proxy = proxy
        self.user_agent = DOUYIN_FIXED_USER_AGENT
        self.verify_params: Optional[VerifyParams] = None
        # 持久化 HTTP 客户端，复用连接池（避免每次请求重建 TCP+TLS）
        self._http_client = httpx.AsyncClient(
            proxy=self.proxy,
            timeout=10,
        )

    async def close(self):
        """关闭 HTTP 客户端，释放连接池资源。"""
        if self._http_client:
            await self._http_client.aclose()

    async def _init_verify_params(self) -> None:
        """Initialize verification parameters."""
        if self.verify_params is None:
            self.verify_params = await get_common_verify_params(self.user_agent)

    def _get_headers(self, is_post: bool = False, remove_origin: bool = False) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Accept": "application/json",
            "accept-language": "zh-CN,zh;q=0.9",
            "Cookie": self.cookies,
            "referer": "https://www.douyin.com/discover" if is_post else "https://www.douyin.com/user/self",
            "user-agent": self.user_agent,
        }

        if is_post:
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            headers["X-Secsdk-Csrf-Token"] = "DOWNGRADE"
        else:
            headers["Content-Type"] = "application/json"

        if not remove_origin and not is_post:
            headers["origin"] = "https://www.douyin.com"

        return headers

    def _get_sign(self, query_params: str, post_data: str = "") -> str:
        """
        Get a_bogus signature using local JavaScript signer.

        Args:
            query_params: URL encoded query parameters
            post_data: POST request body (empty for GET)

        Returns:
            a_bogus signature string
        """
        try:
            return get_a_bogus(query_params, post_data, self.user_agent)
        except SignError as e:
            raise DataFetchError(f"Signing failed: {e}")

    async def _request(
        self,
        method: str,
        uri: str,
        params: Dict[str, Any],
        need_sign: bool = True,
        headers: Optional[Dict[str, str]] = None,
        post_data: str = "",
    ) -> Dict[str, Any]:
        """
        Make API request.

        Args:
            method: HTTP method (GET/POST)
            uri: API endpoint URI
            params: Query parameters
            need_sign: Whether to add a_bogus signature
            headers: Optional custom headers
            post_data: POST request body

        Returns:
            API response as dict
        """
        await self._init_verify_params()

        # Merge common params and verify params
        all_params = {
            **self.COMMON_PARAMS,
            **params,
            "webid": self.verify_params.webid,
            "msToken": self.verify_params.ms_token,
        }

        query_string = urllib.parse.urlencode(all_params)

        # Add signature if needed
        if need_sign:
            a_bogus = self._get_sign(query_string, post_data)
            all_params["a_bogus"] = a_bogus
            query_string = urllib.parse.urlencode(all_params)

        url = f"{self.BASE_URL}{uri}?{query_string}"

        if headers is None:
            headers = self._get_headers(is_post=(method.upper() == "POST"))

        # 复用持久化 HTTP 客户端连接池
        if method.upper() == "GET":
            response = await self._http_client.get(url, headers=headers)
        else:
            response = await self._http_client.post(url, headers=headers)

        if response.text == "" or response.text == "blocked":
            raise DataFetchError("Request blocked or empty response")

        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise DataFetchError(f"Failed to parse response: {e}")

    async def check_login_status(self) -> bool:
        """
        Check if user is logged in.

        Returns:
            True if logged in, False otherwise
        """
        try:
            result = await self._request(
                "GET",
                "/aweme/v1/web/history/read/",
                {"max_cursor": 0, "count": 20}
            )
            return result.get("status_code") == 0
        except Exception:
            return False

    async def search_info_by_keyword(
        self,
        keyword: str,
        offset: int = 0,
        search_channel: SearchChannelType = SearchChannelType.GENERAL,
        sort_type: SearchSortType = SearchSortType.GENERAL,
        publish_time: PublishTimeType = PublishTimeType.UNLIMITED,
        count: int = 10,
    ) -> Dict[str, Any]:
        """
        Search videos by keyword.

        Args:
            keyword: Search keyword
            offset: Pagination offset
            search_channel: Search channel type
            sort_type: Sort type
            publish_time: Publish time filter
            count: Number of results per page

        Returns:
            Search results dict
        """
        params = {
            "keyword": keyword,
            "offset": offset,
            "search_channel": search_channel.value,
            "sort_type": sort_type.value,
            "publish_time": publish_time.value,
            "count": str(count),
            "enable_history": "1",
            "search_source": "tab_search",
            "query_correct_type": "1",
            "is_filter_search": "0",
            "from_group_id": "7378810571505847586",
            "need_filter_settings": "1",
            "list_type": "multi",
        }

        # Add filter_selected if sort or time filter is set
        if sort_type != SearchSortType.GENERAL or publish_time != PublishTimeType.UNLIMITED:
            params["is_filter_search"] = "1"
            params["filter_selected"] = json.dumps({
                "sort_type": str(sort_type.value),
                "publish_time": str(publish_time.value)
            })

        # Search endpoint doesn't need signature
        return await self._request(
            "GET",
            "/aweme/v1/web/general/search/single/",
            params,
            need_sign=False
        )

    async def get_video_by_id(self, aweme_id: str) -> Optional[DouyinAweme]:
        """
        Get video details by ID.

        Args:
            aweme_id: Video/aweme ID

        Returns:
            DouyinAweme object or None
        """
        await self._init_verify_params()

        params = {
            "aweme_id": aweme_id,
            "verifyFp": self.verify_params.verify_fp,
            "fp": self.verify_params.verify_fp,
        }

        headers = self._get_headers(remove_origin=True)

        result = await self._request(
            "GET",
            "/aweme/v1/web/aweme/detail/",
            params,
            headers=headers
        )

        aweme_detail = result.get("aweme_detail")
        if aweme_detail:
            return DouyinAweme.from_dict(aweme_detail)
        return None

    async def get_aweme_comments(
        self,
        aweme_id: str,
        cursor: int = 0,
        count: int = 20,
        source_keyword: str = "",
    ) -> Tuple[List[DouyinAwemeComment], Dict[str, Any]]:
        """
        Get video comments.

        Args:
            aweme_id: Video/aweme ID
            cursor: Pagination cursor
            count: Number of comments per page
            source_keyword: Search keyword for referer

        Returns:
            Tuple of (comments list, metadata dict)
        """
        await self._init_verify_params()

        params = {
            "aweme_id": aweme_id,
            "cursor": cursor,
            "count": count,
            "item_type": 0,
            "verifyFp": self.verify_params.verify_fp,
            "fp": self.verify_params.verify_fp,
        }

        # Build special referer
        referer_base = f"https://www.douyin.com/search/{urllib.parse.quote(source_keyword, safe=':/')}"
        referer = f"{referer_base}?aid=6383&publish_time=0&sort_type=0&source=search_history&type=general"

        headers = self._get_headers()
        headers["Referer"] = referer

        result = await self._request(
            "GET",
            "/aweme/v1/web/comment/list/",
            params,
            headers=headers
        )

        comments = []
        for comment_data in result.get("comments", []):
            comments.append(DouyinAwemeComment.from_dict(comment_data))

        metadata = {
            "cursor": result.get("cursor", 0),
            "has_more": result.get("has_more", False),
            "total": result.get("total", 0),
        }

        return comments, metadata

    async def get_sub_comments(
        self,
        comment_id: str,
        cursor: int = 0,
        count: int = 20,
        source_keyword: str = "",
    ) -> Tuple[List[DouyinAwemeComment], Dict[str, Any]]:
        """
        Get sub-comments (replies) for a comment.

        Args:
            comment_id: Parent comment ID
            cursor: Pagination cursor
            count: Number of replies per page
            source_keyword: Search keyword for referer

        Returns:
            Tuple of (comments list, metadata dict)
        """
        await self._init_verify_params()

        params = {
            "comment_id": comment_id,
            "cursor": cursor,
            "count": count,
            "item_type": 0,
            "verifyFp": self.verify_params.verify_fp,
            "fp": self.verify_params.verify_fp,
        }

        # Build special referer
        referer_base = f"https://www.douyin.com/search/{urllib.parse.quote(source_keyword, safe=':/')}"
        referer = f"{referer_base}?aid=6383&publish_time=0&sort_type=0&source=search_history&type=general"

        headers = self._get_headers()
        headers["Referer"] = referer

        result = await self._request(
            "GET",
            "/aweme/v1/web/comment/list/reply/",
            params,
            headers=headers
        )

        comments = []
        for comment_data in result.get("comments", []):
            comments.append(DouyinAwemeComment.from_dict(comment_data))

        metadata = {
            "cursor": result.get("cursor", 0),
            "has_more": result.get("has_more", False),
        }

        return comments, metadata

    async def get_user_info(self, sec_user_id: str) -> Optional[DouyinCreator]:
        """
        Get user profile information.

        Args:
            sec_user_id: User's security ID

        Returns:
            DouyinCreator object or None
        """
        await self._init_verify_params()

        params = {
            "sec_user_id": sec_user_id,
            "publish_video_strategy_type": 2,
            "personal_center_strategy": 1,
            "verifyFp": self.verify_params.verify_fp,
            "fp": self.verify_params.verify_fp,
        }

        result = await self._request(
            "GET",
            "/aweme/v1/web/user/profile/other/",
            params
        )

        if result.get("status_code") == 0:
            return DouyinCreator.from_dict(result)
        return None

    async def get_user_aweme_posts(
        self,
        sec_user_id: str,
        max_cursor: str = "0",
        count: int = 18,
    ) -> Dict[str, Any]:
        """
        Get user's video posts.

        Args:
            sec_user_id: User's security ID
            max_cursor: Pagination cursor
            count: Number of videos per page

        Returns:
            API response dict with video list
        """
        await self._init_verify_params()

        params = {
            "sec_user_id": sec_user_id,
            "count": count,
            "max_cursor": max_cursor,
            "locate_query": "false",
            "publish_video_strategy_type": 2,
            "verifyFp": self.verify_params.verify_fp,
            "fp": self.verify_params.verify_fp,
        }

        return await self._request(
            "GET",
            "/aweme/v1/web/aweme/post/",
            params
        )

    async def get_homefeed_aweme_list(
        self,
        tag_id: HomeFeedTagIdType = HomeFeedTagIdType.ALL,
        count: int = 20,
        refresh_index: int = 0,
    ) -> Dict[str, Any]:
        """
        Get home feed recommended videos.

        Args:
            tag_id: Content category tag
            count: Number of videos to return
            refresh_index: Refresh index for pagination

        Returns:
            API response dict with video list
        """
        params = {
            "refresh_index": refresh_index,
            "video_type_select": tag_id.value,
            "count": count,
        }

        # 自定义 Referer 为首页
        headers = self._get_headers()
        headers["Referer"] = "https://www.douyin.com/"

        return await self._request(
            "GET",
            "/aweme/v1/web/tab/feed/",
            params,
            headers=headers,
        )
