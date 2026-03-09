import asyncio
import json
from src.server import (
    check_login_status,
    search_videos,
    get_video_detail,
    get_video_comments,
    get_sub_comments,
    get_user_info,
    get_user_posts,
    get_homefeed
)

async def test_all_tools():
    print("🚀 开始测试 Phase 1 的所有 8 个工具...\n")
    
    test_aweme_id = "7351608753239559464" # 测试用的视频ID
    test_sec_uid = ""                      # 测试用的用户ID
    
    try:
        # 1. 检查登录状态
        print("1️⃣ 测试 check_login_status:")
        res = await check_login_status()
        print(f"   结果: {res}")
        if isinstance(res, dict) and not res.get("logged_in"):
            print("❌ 错误：Cookie未登录或已过期。测试终止，请先更新 cookies.txt")
            return
        elif isinstance(res, str) and "❌" in res:
            print(f"{res}")
            return
            
        # 2. 搜索视频
        print("\n2️⃣ 测试 search_videos ('python'):")
        res = await search_videos(keyword="python", count=2)
        status = res.get("status_code", -1) if isinstance(res, dict) else -1
        print(f"   Status Code: {status}")
        if status == 0 and res.get("data"):
            aweme_info = res["data"][0].get("aweme_info", {})
            test_aweme_id = str(aweme_info.get("aweme_id", test_aweme_id))
            author = aweme_info.get("author", {})
            test_sec_uid = author.get("sec_uid", "")
            print(f"   提取到视频ID: {test_aweme_id}, 作者SecUID: {test_sec_uid[:15]}...")
        
        # 3. 获取视频详情
        print(f"\n3️⃣ 测试 get_video_detail (视频 {test_aweme_id}):")
        res = await get_video_detail(aweme_id=test_aweme_id)
        print(f"   Success: {res.get('success', False) if isinstance(res, dict) else False}")
        if isinstance(res, dict) and res.get('success'):
            video = res.get('video', {})
            print(f"   标题: {video.get('title')}, 时长: {video.get('video_duration')}ms")
            
        # 4. 获取视频评论
        print(f"\n4️⃣ 测试 get_video_comments (视频 {test_aweme_id}):")
        res = await get_video_comments(aweme_id=test_aweme_id, count=2)
        print(f"   Success: {res.get('success', False) if isinstance(res, dict) else False}")
        if isinstance(res, dict) and res.get('success'):
            comments = res.get('comments', [])
            test_comment_id = comments[0].get('comment_id') if comments else ""
            print(f"   获取到 {len(comments)} 条评论. 选用评论ID: {test_comment_id} 测试子评论")
            
            # 5. 获取子评论
            if test_comment_id:
                print(f"\n5️⃣ 测试 get_sub_comments (评论 {test_comment_id}):")
                res = await get_sub_comments(comment_id=test_comment_id, count=2)
                print(f"   Success: {res.get('success', False) if isinstance(res, dict) else False}")
                
        # 6. 获取用户信息
        if test_sec_uid:
            print(f"\n6️⃣ 测试 get_user_info (用户 {test_sec_uid[:15]}...):")
            res = await get_user_info(sec_user_id=test_sec_uid)
            print(f"   Success: {res.get('success', False) if isinstance(res, dict) else False}")
            if isinstance(res, dict) and res.get('success'):
                user = res.get('user', {})
                print(f"   昵称: {user.get('nickname')}, 粉丝: {user.get('fans')}")
                
            # 7. 获取用户作品
            print(f"\n7️⃣ 测试 get_user_posts (用户 {test_sec_uid[:15]}...):")
            res = await get_user_posts(sec_user_id=test_sec_uid, count=2)
            print(f"   Status Code: {res.get('status_code', -1) if isinstance(res, dict) else -1}")
            
        # 8. 获取推荐流
        print("\n8️⃣ 测试 get_homefeed:")
        res = await get_homefeed(count=2)
        print(f"   Status Code: {res.get('status_code', -1) if isinstance(res, dict) else -1}")
        
        print("\n🎉 全部 8 个基础工具 API 连通性测试完毕！")
            
    except Exception as e:
        print(f"\n❌ 测试抛出异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_all_tools())
