"""
抖音扫码登录工具 — 自动获取 Cookie 并安全保存到本地文件。

用法：
    uv run login.py              # 默认：浏览器扫码登录（Playwright）
    uv run login.py --api        # 备用：纯 API 模式（可能被反爬拦截）

流程（浏览器模式）：
    自动打开 Chrome → 显示抖音登录页 → 手机扫码或账密登录 → 自动保存 Cookie
"""

import argparse
import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

from src.config import COOKIE_PATH
from src.cookies import normalize_cookie_string

# ====== 常量 ======

DOUYIN_HOME = "https://www.douyin.com"
QR_EXPIRE_TIME = 120     # 二维码过期时间（秒）
MAX_RETRIES = 3           # 最多重试次数

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)

COOKIE_FILE = Path(COOKIE_PATH).expanduser()


def _save_cookies(cookie_str: str) -> bool:
    """将 Cookie 字符串安全写入文件（原子替换 + 0600 权限）。"""
    normalized = normalize_cookie_string(cookie_str)
    if not normalized.value:
        print("❌ 未能提取到有效 Cookie，保存已取消")
        return False
    if normalized.invalid_parts:
        print(f"⚠️ Cookie 中存在 {normalized.invalid_parts} 个无效片段，保存前已自动忽略")

    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(prefix="cookies_", dir=str(COOKIE_FILE.parent))
    temp_file = Path(temp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(normalized.value)
            f.flush()
            os.fsync(f.fileno())

        # 安全：仅当前用户可读写（0o600 = -rw-------）
        try:
            os.chmod(str(temp_file), 0o600)
        except OSError:
            pass  # Windows 不支持 chmod，忽略

        os.replace(str(temp_file), str(COOKIE_FILE))
        try:
            os.chmod(str(COOKIE_FILE), 0o600)
        except OSError:
            pass
    finally:
        # 若替换失败，清理临时文件
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass

    # 防呆：确保 .gitignore 中包含 cookies.txt
    gitignore_path = Path(__file__).parent / ".gitignore"
    _ensure_gitignore(gitignore_path)

    print(f"🎉 Cookie 已保存到 {COOKIE_FILE}（{len(normalized.value)} 字符）")
    return True


def _clear_cookies() -> bool:
    """删除本地 Cookie 文件。"""
    deleted = False

    for cookie_file in [COOKIE_FILE]:
        if not cookie_file.exists():
            continue
        try:
            cookie_file.unlink()
            print(f"🗑️ 已删除 Cookie 文件：{cookie_file}")
            deleted = True
        except OSError as exc:
            print(f"❌ 删除 Cookie 文件失败：{cookie_file} ({exc})")
            return False

    if os.getenv("DOUYIN_COOKIE", "").strip():
        print("⚠️ 当前进程还设置了环境变量 DOUYIN_COOKIE。")
        print("   本脚本无法替你删除环境变量，请手动从 MCP 配置里移除后重启客户端。")

    if not deleted:
        print("ℹ️ 未发现本地 Cookie 文件，无需删除。")

    return True


def _ensure_gitignore(gitignore_path: Path):
    """确保 .gitignore 中有 cookies.txt 条目，防止意外 git push。"""
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if "cookies.txt" not in content:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# 抖音 Cookie（敏感文件，不入 Git）\ncookies.txt\n")
            print("🛡️ 已自动将 cookies.txt 加入 .gitignore")
    else:
        gitignore_path.write_text(
            "# 抖音 Cookie（敏感文件，不入 Git）\ncookies.txt\n\n"
            "# Python\n__pycache__/\n*.pyc\n.venv/\n",
            encoding="utf-8",
        )
        print("🛡️ 已创建 .gitignore 并添加 cookies.txt")


# ====== 方案 A：Playwright 浏览器登录（默认推荐）======


def _install_playwright():
    """自动安装 playwright 和 chromium。"""
    import subprocess

    project_root = Path(__file__).parent

    print("⚙️ 正在安装 playwright（首次使用需要约 1 分钟）...")
    # 使用 uv sync 安装可选依赖组
    ret = subprocess.run(
        ["uv", "sync", "--extra", "browser-login"],
        cwd=str(project_root),
    )
    if ret.returncode != 0:
        print("❌ playwright 安装失败，请手动运行：")
        print("   uv sync --extra browser-login")
        return False

    print("⚙️ 正在下载 Chromium 浏览器...")
    ret = subprocess.run(
        ["uv", "run", "playwright", "install", "chromium"],
        cwd=str(project_root),
    )
    if ret.returncode != 0:
        print("❌ Chromium 下载失败，请手动运行：")
        print("   uv run playwright install chromium")
        return False

    print("✅ playwright 安装完成！\n")
    return True



async def browser_login():
    """通过 Playwright 浏览器手动登录（主推方法）。"""
    # 检查 playwright 是否已安装
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("📦 playwright 未安装，正在自动安装...")
        if not _install_playwright():
            return False
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("❌ playwright 安装后仍无法导入，请手动运行：pip install playwright")
            return False

    # 尝试 stealth 插件（可选，减少被检测概率）
    try:
        from playwright_stealth import stealth_async
        has_stealth = True
    except ImportError:
        has_stealth = False

    print("\n🌐 正在启动浏览器...")
    print("   请在打开的浏览器窗口中登录抖音（扫码或账号密码均可）")
    print("   登录完成后脚本会自动检测并保存 Cookie，无需任何操作\n")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )
            page = await context.new_page()

            # 应用 stealth 插件（如果有）
            if has_stealth:
                await stealth_async(page)

            await page.goto(DOUYIN_HOME)
            print("  ⏳ 等待你在浏览器中完成登录（最多 5 分钟）...")
            print("      提示：页面会自动打开抖音登录框，用手机扫码即可\n")

            # 等待登录成功（最多 5 分钟）
            for i in range(150):  # 150 * 2s = 300s = 5min
                await page.wait_for_timeout(2000)
                cookies = await context.cookies()
                cookie_names = {c["name"] for c in cookies}
                if "sessionid" in cookie_names or "sessionid_ss" in cookie_names:
                    print("  ✅ 检测到登录成功！")
                    break
                # 每 30 秒打印提示
                if i > 0 and i % 15 == 0:
                    remaining = (150 - i) * 2
                    print(f"  ⏳ 还在等待登录... 剩余约 {remaining} 秒")
            else:
                print("❌ 登录超时（5 分钟），请重新运行 uv run login.py")
                await browser.close()
                return False

            # 提取 Cookie
            all_cookies = await context.cookies()
            cookie_str = "; ".join(
                f'{c["name"]}={c["value"]}' for c in all_cookies
                if c["domain"].endswith("douyin.com")
            )

            await browser.close()

            if cookie_str:
                return _save_cookies(cookie_str)
            else:
                print("❌ 未能提取到有效 Cookie")
                return False

    except Exception as e:
        print(f"❌ 浏览器启动失败：{e}")
        print("   如果你在无 GUI 的服务器上，请用 --api 模式，或手动复制 Cookie")
        return False


# ====== 方案 B：纯 API 模式（可能被反爬拦截）======


async def api_login():
    """通过抖音 SSO 二维码 API 扫码登录（注意：可能被反爬拦截）。"""
    import httpx

    try:
        import qrcode
    except ImportError:
        print("❌ 缺少 qrcode 库，正在安装...")
        os.system(f"{sys.executable} -m pip install qrcode -q")
        import qrcode

    SSO_BASE = "https://sso.douyin.com"

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": DOUYIN_HOME,
        "Accept": "application/json, text/plain, */*",
    }

    # 二维码状态常量
    STATUS_WAITING = "1"
    STATUS_SCANNED = "2"
    STATUS_CONFIRMED = "5"

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n{'='*50}")
        print(f"📱 抖音扫码登录（第 {attempt}/{MAX_RETRIES} 次）")
        print(f"{'='*50}\n")

        async with httpx.AsyncClient(
            follow_redirects=False, headers=headers, timeout=15
        ) as client:
            # 第1步：获取二维码
            try:
                resp = await client.get(
                    f"{SSO_BASE}/get_qrcode/",
                    params={
                        "aid": "6383",
                        "service": DOUYIN_HOME,
                        "next": DOUYIN_HOME,
                    },
                )
                # 检查是否被反爬
                ct = resp.headers.get("content-type", "")
                if "html" in ct or resp.text.strip().startswith("<"):
                    print("⚠️ 检测到抖音反爬机制（返回了 HTML 而非 JSON）")
                    print("   建议切换到浏览器模式：uv run login.py（不带 --api）\n")
                    return False

                data = resp.json()
            except Exception as e:
                print(f"❌ 获取二维码失败：{e}")
                if attempt < MAX_RETRIES:
                    print("  等待 3 秒后重试...")
                    await asyncio.sleep(3)
                    continue
                return False

            if data.get("error_code") != 0:
                print(f"❌ SSO 返回错误：{data}")
                return False

            qr_data = data.get("data", {})
            token = qr_data.get("token")
            qrcode_url = qr_data.get("qrcode_index_url")

            if not token or not qrcode_url:
                print(f"❌ 二维码数据异常：{qr_data}")
                return False

            # 第2步：在终端展示 ASCII 二维码
            qr = qrcode.QRCode(border=1)
            qr.add_data(qrcode_url)
            qr.print_ascii(invert=True)
            print("\n👆 请用抖音 App 扫描上方二维码")
            print(f"   （二维码 {QR_EXPIRE_TIME} 秒后过期）\n")

            # 第3步：轮询扫码状态
            start_time = time.time()
            confirmed = False
            redirect_url = ""

            while time.time() - start_time < QR_EXPIRE_TIME:
                await asyncio.sleep(2)

                try:
                    check_resp = await client.get(
                        f"{SSO_BASE}/check_qrconnect/",
                        params={"token": token, "aid": "6383", "service": DOUYIN_HOME},
                    )
                    check_data = check_resp.json()
                except Exception as e:
                    print(f"  ⚠️ 轮询出错：{e}")
                    continue

                status_data = check_data.get("data", {})
                status = status_data.get("status", "")

                if status == STATUS_WAITING:
                    elapsed = int(time.time() - start_time)
                    remaining = QR_EXPIRE_TIME - elapsed
                    print(f"\r  ⏳ 等待扫码... ({remaining}s)", end="", flush=True)
                elif status == STATUS_SCANNED:
                    print("\n  ✅ 已扫码，请在手机上确认登录...")
                elif status == STATUS_CONFIRMED:
                    print("\n  ✅ 登录确认成功！")
                    redirect_url = status_data.get("redirect_url", "")
                    confirmed = True
                    break
                else:
                    print(f"\n  ⚠️ 二维码状态异常（status={status}），重新获取...")
                    break

            if not confirmed:
                if attempt < MAX_RETRIES:
                    print("\n⏰ 二维码已过期，重新获取...")
                    continue
                else:
                    print("\n❌ 扫码超时，请重新运行 login.py")
                    return False

            # 第4步：跟随重定向提取 Cookie
            print("  正在提取 Cookie...")
            all_cookies = dict(check_resp.cookies)

            if redirect_url:
                try:
                    redirect_resp = await client.get(redirect_url)
                    all_cookies.update(dict(redirect_resp.cookies))
                except Exception:
                    pass

            # 补全辅助 Cookie
            try:
                home_client = httpx.AsyncClient(
                    follow_redirects=True,
                    headers=headers,
                    cookies=all_cookies,
                    timeout=15,
                )
                home_resp = await home_client.get(DOUYIN_HOME)
                all_cookies.update(dict(home_resp.cookies))
                await home_client.aclose()
            except Exception:
                pass

            cookie_str = "; ".join(f"{k}={v}" for k, v in all_cookies.items())

            if not cookie_str or "sessionid" not in cookie_str:
                print("⚠️ 提取到的 Cookie 中缺少 sessionid，可能登录未完全成功")
                if not cookie_str:
                    return False

            return _save_cookies(cookie_str)

    return False


# ====== 主入口 ======


def main():
    parser = argparse.ArgumentParser(
        description="抖音扫码登录工具 — 自动获取 Cookie",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  uv run login.py              # 浏览器扫码（推荐，自动安装 playwright）
  uv run login.py --api        # 终端 API 模式（可能被反爬拦截）
  uv run login.py --logout     # 删除本地 Cookie，退出当前登录
        """,
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="使用纯 API 模式（注意：可能被抖音反爬机制拦截）",
    )
    # 保持向后兼容：--browser 仍然有效
    parser.add_argument(
        "--browser",
        action="store_true",
        help="（同默认模式）使用 Playwright 浏览器登录",
    )
    parser.add_argument(
        "--logout",
        action="store_true",
        help="删除本地 Cookie 文件，退出当前登录",
    )
    args = parser.parse_args()

    print("\n🎬 抖音 MCP — Cookie 登录工具\n")

    if args.logout:
        success = _clear_cookies()
        if success:
            print("\n✅ 已完成退出操作。下次使用前需要重新登录。")
        else:
            print("\n❌ 退出操作失败。")
        sys.exit(0 if success else 1)

    if args.api:
        success = asyncio.run(api_login())
        if not success:
            print("\n💡 提示：API 模式被拦截时，请改用默认的浏览器模式：")
            print("   uv run login.py")
    else:
        # 默认：浏览器模式
        success = asyncio.run(browser_login())

    if success:
        print("\n✅ 登录完成！现在可以使用抖音 MCP 工具了。")
        print("   验证方式：让 AI 助手调用 check_login_status 工具")
    else:
        print("\n❌ 登录失败。")
        print(f"   💡 备选方式：手动将浏览器 Cookie 粘贴到 {COOKIE_FILE}")
        print("      1. 浏览器打开 douyin.com 并登录")
        print("      2. F12 → Network → 任意请求 → 找到 Cookie 请求头")
        print(f"      3. 复制完整 Cookie 粘贴到 {COOKIE_FILE}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
