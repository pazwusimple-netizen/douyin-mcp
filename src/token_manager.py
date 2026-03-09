"""Token generation and management for Douyin API."""

import time
import random
import string
import httpx
from typing import Optional
from dataclasses import dataclass

from .models import VerifyParams


# Constants
DOUYIN_FIXED_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)

# Base64 encoded fingerprint data for msToken request
DOUYIN_MS_TOKEN_REQ_STR_DATA = (
    "3AMILhBmPpVr7L9Lr7tCGwdIidmDvRbFQ5Sq6YJocqWx5L9s5L9l5L985L9C3qxU"
    "LhTm5L9o5L9h5L985L9j5L9c5L9c5L9x5LWdLexbKfWDVd9iyywf7eCDVdVCGwdI"
    # ... (truncated for brevity, use full data in production)
)


def random_string(length: int) -> str:
    """Generate a random alphanumeric string."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


class TokenManager:
    """Manages token generation for Douyin API requests."""

    def __init__(self, user_agent: str = DOUYIN_FIXED_USER_AGENT):
        self.user_agent = user_agent

    async def get_ms_token(self) -> str:
        """
        Get msToken.
        Tries to generate real msToken first, falls back to fake msToken.
        """
        try:
            return await self._gen_real_ms_token()
        except Exception:
            return self._gen_fake_ms_token()

    async def _gen_real_ms_token(self) -> str:
        """
        Generate real msToken by calling bytedance API.
        POST https://mssdk.bytedance.com/web/common
        """
        url = "https://mssdk.bytedance.com/web/common"
        payload = {
            "magic": 538969122,
            "version": 1,
            "dataType": 8,
            "strData": DOUYIN_MS_TOKEN_REQ_STR_DATA,
            "tspFromClient": int(time.time() * 1000),
            "url": 0
        }
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": self.user_agent
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            cookies = response.cookies
            ms_token = cookies.get("msToken", "")

            if len(ms_token) not in (120, 128):
                raise ValueError("Invalid msToken length")

            return ms_token

    def _gen_fake_ms_token(self) -> str:
        """Generate fake msToken (126 random chars + '==')."""
        return random_string(126) + "=="

    async def gen_webid(self) -> str:
        """
        Generate webid.
        Tries server generation first, falls back to local algorithm.
        """
        try:
            return await self._gen_webid_from_server()
        except Exception:
            return self._gen_webid_local()

    async def _gen_webid_from_server(self) -> str:
        """
        Generate webid from server.
        POST https://mcs.zijieapi.com/webid
        """
        url = "https://mcs.zijieapi.com/webid"
        params = {
            "aid": "6383",
            "sdk_version": "5.1.18_zip",
            "device_platform": "web"
        }
        payload = {
            "app_id": 6383,
            "referer": "https://www.douyin.com/",
            "url": "https://www.douyin.com/",
            "user_agent": self.user_agent,
            "user_unique_id": ""
        }
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json; charset=UTF-8",
            "Referer": "https://www.douyin.com/"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, params=params, json=payload, headers=headers, timeout=10
            )
            data = response.json()
            web_id = data.get("web_id", "")

            if not web_id:
                raise ValueError("Failed to get webid from server")

            return web_id

    def _gen_webid_local(self) -> str:
        """Generate webid using local UUID-like algorithm."""
        def e(t: Optional[int] = None) -> str:
            if t is not None:
                return str(t ^ (int(16 * random.random()) >> (t // 4)))
            else:
                return "".join([
                    str(int(1e7)),
                    "-",
                    str(int(1e3)),
                    "-",
                    str(int(4e3)),
                    "-",
                    str(int(8e3)),
                    "-",
                    str(int(1e11)),
                ])

        template = e(None)
        web_id_full = "".join(
            e(int(x)) if x in "018" else x for x in template
        )
        return web_id_full.replace("-", "")[:19]


class VerifyFpManager:
    """Manages verify fingerprint generation."""

    BASE_STR = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    @classmethod
    def gen_verify_fp(cls) -> str:
        """
        Generate verifyFp.
        Format: verify_<base36_timestamp>_<uuid>
        """
        # Step 1: Generate Base36 timestamp
        milliseconds = int(round(time.time() * 1000))
        base36 = ""

        while milliseconds > 0:
            remainder = milliseconds % 36
            if remainder < 10:
                base36 = str(remainder) + base36
            else:
                base36 = chr(ord("a") + remainder - 10) + base36
            milliseconds = int(milliseconds / 36)

        # Step 2: Generate 36-char UUID
        o = [""] * 36
        o[8] = o[13] = o[18] = o[23] = "_"
        o[14] = "4"

        for i in range(36):
            if not o[i]:
                n = int(random.random() * 62)
                if i == 19:
                    n = (3 & n) | 8
                o[i] = cls.BASE_STR[n]

        uuid_part = "".join(o)

        # Step 3: Combine
        return f"verify_{base36}_{uuid_part}"

    @classmethod
    def gen_s_v_web_id(cls) -> str:
        """Generate s_v_web_id (same algorithm as verifyFp)."""
        return cls.gen_verify_fp()


async def get_common_verify_params(user_agent: str = DOUYIN_FIXED_USER_AGENT) -> VerifyParams:
    """
    Get all common verification parameters.

    Returns:
        VerifyParams containing ms_token, webid, verify_fp, s_v_web_id
    """
    token_manager = TokenManager(user_agent)

    ms_token = await token_manager.get_ms_token()
    webid = await token_manager.gen_webid()
    verify_fp = VerifyFpManager.gen_verify_fp()
    s_v_web_id = VerifyFpManager.gen_s_v_web_id()

    return VerifyParams(
        ms_token=ms_token,
        webid=webid,
        verify_fp=verify_fp,
        s_v_web_id=s_v_web_id
    )
