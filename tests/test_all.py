"""Comprehensive test for all Douyin MCP tools."""

import asyncio
import sys
from dataclasses import asdict
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.client import DouYinApiClient, DataFetchError
from src.server import load_cookies
from src.models import (
    SearchChannelType,
    SearchSortType,
    PublishTimeType,
    HomeFeedTagIdType,
)

# Load cookies from configured path
COOKIES = load_cookies()
if not COOKIES:
    print("ERROR: Cookie not found! Run: uv run login.py")
    exit(1)

# Test data - known working IDs
TEST_VIDEO_ID = "7590719110745525567"
TEST_COMMENT_ID = "7590992888545395462"


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.message = ""
        self.data = None

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.name}: {self.message}"


async def test_check_login_status(client: DouYinApiClient) -> TestResult:
    """Test 1: Check login status."""
    result = TestResult("check_login_status")
    try:
        is_logged_in = await client.check_login_status()
        result.success = True
        result.message = f"logged_in={is_logged_in}"
        result.data = {"logged_in": is_logged_in}
    except Exception as e:
        result.message = f"Error: {e}"
    return result


async def test_search_videos(client: DouYinApiClient) -> TestResult:
    """Test 2: Search videos by keyword."""
    result = TestResult("search_videos")
    try:
        response = await client.search_info_by_keyword(
            keyword="美食",
            offset=0,
            count=5,
            search_channel=SearchChannelType.GENERAL,
            sort_type=SearchSortType.GENERAL,
            publish_time=PublishTimeType.UNLIMITED,
        )
        if "status_code" in response and response["status_code"] == 0:
            data = response.get("data", [])
            result.success = True
            result.message = f"Found {len(data)} results"
            result.data = response
        else:
            result.message = f"API returned status_code: {response.get('status_code')}"
            result.data = response
    except DataFetchError as e:
        result.message = f"DataFetchError: {e}"
    except Exception as e:
        result.message = f"Error: {type(e).__name__}: {e}"
    return result


async def test_get_video_detail(client: DouYinApiClient, aweme_id: str = None) -> TestResult:
    """Test 3: Get video detail."""
    result = TestResult("get_video_detail")

    if not aweme_id:
        aweme_id = TEST_VIDEO_ID

    try:
        video = await client.get_video_by_id(aweme_id)
        if video:
            result.success = True
            result.message = f"Got video: {video.title[:30] if video.title else 'No title'}..."
            result.data = asdict(video)
        else:
            result.message = "Video not found (returned None)"
    except DataFetchError as e:
        result.message = f"DataFetchError: {e}"
    except Exception as e:
        result.message = f"Error: {type(e).__name__}: {e}"
    return result


async def test_get_video_comments(client: DouYinApiClient, aweme_id: str = None) -> TestResult:
    """Test 4: Get video comments."""
    result = TestResult("get_video_comments")

    if not aweme_id:
        aweme_id = TEST_VIDEO_ID

    try:
        comments, metadata = await client.get_aweme_comments(
            aweme_id=aweme_id,
            cursor=0,
            count=10,
        )
        result.success = True
        result.message = f"Got {len(comments)} comments"
        result.data = {"comments": [asdict(c) for c in comments], "metadata": metadata}
    except DataFetchError as e:
        result.message = f"DataFetchError: {e}"
    except Exception as e:
        result.message = f"Error: {type(e).__name__}: {e}"
    return result


async def test_get_sub_comments(client: DouYinApiClient, comment_id: str = None) -> TestResult:
    """Test 5: Get sub-comments (replies)."""
    result = TestResult("get_sub_comments")

    if not comment_id:
        comment_id = TEST_COMMENT_ID

    try:
        comments, metadata = await client.get_sub_comments(
            comment_id=comment_id,
            cursor=0,
            count=10,
        )
        result.success = True
        result.message = f"Got {len(comments)} replies"
        result.data = {"comments": [asdict(c) for c in comments], "metadata": metadata}
    except DataFetchError as e:
        result.message = f"DataFetchError: {e}"
    except Exception as e:
        result.message = f"Error: {type(e).__name__}: {e}"
    return result


async def test_get_user_info(client: DouYinApiClient, sec_user_id: str = None) -> TestResult:
    """Test 6: Get user info."""
    result = TestResult("get_user_info")

    if not sec_user_id:
        sec_user_id = "MS4wLjABAAAAe5i6-iuzIEcfL12g2CfF8e6-r1H9Lho-LWHd3KxYX8k"

    try:
        user = await client.get_user_info(sec_user_id)
        if user:
            result.success = True
            result.message = f"Got user: {user.nickname}"
            result.data = asdict(user)
        else:
            result.message = "User not found (returned None)"
    except DataFetchError as e:
        result.message = f"DataFetchError: {e}"
    except Exception as e:
        result.message = f"Error: {type(e).__name__}: {e}"
    return result


async def test_get_user_posts(client: DouYinApiClient, sec_user_id: str = None) -> TestResult:
    """Test 7: Get user posts."""
    result = TestResult("get_user_posts")

    if not sec_user_id:
        sec_user_id = "MS4wLjABAAAAe5i6-iuzIEcfL12g2CfF8e6-r1H9Lho-LWHd3KxYX8k"

    try:
        response = await client.get_user_aweme_posts(
            sec_user_id=sec_user_id,
            max_cursor="0",
            count=10,
        )
        if "status_code" in response and response["status_code"] == 0:
            aweme_list = response.get("aweme_list", [])
            result.success = True
            result.message = f"Got {len(aweme_list)} posts"
            result.data = response
        else:
            result.message = f"API returned status_code: {response.get('status_code')}"
            result.data = response
    except DataFetchError as e:
        result.message = f"DataFetchError: {e}"
    except Exception as e:
        result.message = f"Error: {type(e).__name__}: {e}"
    return result


async def test_get_homefeed(client: DouYinApiClient) -> TestResult:
    """Test 8: Get home feed."""
    result = TestResult("get_homefeed")

    try:
        response = await client.get_homefeed_aweme_list(
            tag_id=HomeFeedTagIdType.ALL,
            count=10,
            refresh_index=0,
        )
        if "status_code" in response and response["status_code"] == 0:
            aweme_list = response.get("aweme_list", [])
            result.success = True
            result.message = f"Got {len(aweme_list)} videos from feed"
            result.data = response
        else:
            result.message = f"API returned status_code: {response.get('status_code')}"
            result.data = response
    except DataFetchError as e:
        result.message = f"DataFetchError: {e}"
    except Exception as e:
        result.message = f"Error: {type(e).__name__}: {e}"
    return result


async def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("Douyin MCP - Comprehensive Test Suite")
    print("=" * 60)
    print()

    # Initialize client
    client = DouYinApiClient(cookies=COOKIES)
    print(f"Client initialized with cookies ({len(COOKIES)} chars)")
    print()

    results = []

    # Test 1: Login status
    print("Testing check_login_status...")
    r1 = await test_check_login_status(client)
    results.append(r1)
    print(f"  {r1}")
    print()

    # Test 2: Search videos
    print("Testing search_videos...")
    r2 = await test_search_videos(client)
    results.append(r2)
    print(f"  {r2}")
    print()

    # Test 3: Video detail (using fixed test video ID)
    print(f"Testing get_video_detail (video_id={TEST_VIDEO_ID})...")
    r3 = await test_get_video_detail(client, TEST_VIDEO_ID)
    results.append(r3)
    print(f"  {r3}")

    # Extract sec_user_id from video detail for user tests
    sec_user_id = None
    if r3.success and r3.data:
        sec_user_id = r3.data.get("sec_uid")
        if sec_user_id:
            print(f"  → Extracted user ID: {sec_user_id[:40]}...")
    print()

    # Test 4: Video comments
    print(f"Testing get_video_comments (video_id={TEST_VIDEO_ID})...")
    r4 = await test_get_video_comments(client, TEST_VIDEO_ID)
    results.append(r4)
    print(f"  {r4}")
    print()

    # Test 5: Sub-comments (using fixed test comment ID)
    print(f"Testing get_sub_comments (comment_id={TEST_COMMENT_ID})...")
    r5 = await test_get_sub_comments(client, TEST_COMMENT_ID)
    results.append(r5)
    print(f"  {r5}")
    print()

    # Test 6: User info
    print(f"Testing get_user_info (sec_user_id={sec_user_id[:40] if sec_user_id else 'default'}...)...")
    r6 = await test_get_user_info(client, sec_user_id)
    results.append(r6)
    print(f"  {r6}")
    print()

    # Test 7: User posts
    print(f"Testing get_user_posts (sec_user_id={sec_user_id[:40] if sec_user_id else 'default'}...)...")
    r7 = await test_get_user_posts(client, sec_user_id)
    results.append(r7)
    print(f"  {r7}")
    print()

    # Test 8: Home feed
    print("Testing get_homefeed...")
    r8 = await test_get_homefeed(client)
    results.append(r8)
    print(f"  {r8}")
    print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for r in results if r.success)
    total = len(results)

    for r in results:
        print(f"  {r}")

    print()
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
