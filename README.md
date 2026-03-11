# Douyin MCP Server

让 AI 助手直接读取抖音内容：搜索视频、查看详情、抓评论、分析博主、下载视频、语音转文字。

适合的场景：

- 内容选题和行业调研
- 竞品账号分析
- 评论区观点收集
- 教程类视频知识提取
- 把抖音内容接进 Codex / Claude CLI 这类 AI 工作流

## 功能概览

当前提供 15 个 MCP 工具，分为 5 大类。

### 📊 数据获取

**搜索视频** `search_videos`

支持丰富的筛选条件：

- 3 种排序方式：综合排序 / **按点赞最多** / 按最新发布
- 4 种时间筛选：不限 / 1天内 / 1周内 / 半年内
- 4 种搜索类型：综合 / 视频 / 用户 / 直播
- 支持分页，单次最多返回 20 条结果

```
"搜索5条关于AI编程的视频，按点赞最多排序，只看一周内的"
```

**获取视频详情** `get_video_detail`

返回一条视频的完整信息：标题、描述、点赞数、评论数、分享数、收藏数、视频时长（毫秒）、作者信息、下载链接等。

**获取视频评论** `get_video_comments`

支持分页浏览评论列表，每次最多 20 条。返回评论内容、点赞数、回复数、发布时间、评论者信息。

**获取评论回复** `get_sub_comments`

获取某条评论下的子评论（回复），支持分页。适合追踪热门评论下的讨论。

**获取博主资料** `get_user_info`

返回博主的完整资料：昵称、头像、粉丝数、关注数、总获赞数、作品数、简介等。

**获取博主作品列表** `get_user_posts`

按时间顺序列出博主发布的视频，支持分页翻阅历史作品。

**获取推荐流** `get_homefeed`

模拟刷抖音，获取推荐视频流。支持 **16 种内容分类**：全部、知识、体育、汽车、动漫、游戏、影视、生活、旅行、短剧、美食、三农、音乐、动物、亲子、时尚。

```
"帮我看看抖音美食类的推荐视频"
```

**检查登录状态** `check_login_status` / **退出登录** `logout`

检查当前 Cookie 是否有效；清除本地 Cookie 文件退出登录。

### 🔗 链接解析

**解析分享链接** `resolve_share_url`

把抖音分享链接（`https://v.douyin.com/xxx`）解析成视频ID，并自动获取视频详情。适合处理朋友转发给你的"复制链接"。

### 📥 媒体下载

**下载视频** `download_video`

下载抖音视频到本地，返回文件路径、文件大小、以及视频的点赞/评论/收藏等完整统计数据。

**下载图文图片** `download_aweme_images`

下载图文作品中的全部图片到本地目录，生成 manifest 文件方便后续处理。

**图文 OCR** `ocr_aweme_images`

下载图文作品的所有图片，并自动进行文字识别（OCR），输出每张图片中的文字内容。适合处理截图类、知识卡片类的图文内容。

> 使用 OCR 需要额外安装一个依赖包：
> ```bash
> uv sync --extra ocr
> ```
> 这会自动安装 `rapidocr-onnxruntime`（一个纯本地运行的 OCR 引擎），不需要配 API Key，不需要联网，安装完就能用。

### 🔊 语音转文字

**单条转写** `transcribe_video`

完整流程：获取视频详情 → 下载视频 → 提取音频 → 调用 ASR 转写 → 保存为 `.txt` 文件。支持长视频自动切片转写。

**批量转写** `batch_transcribe`

一次搜索 + 批量转写，适合从某个领域批量提取知识。支持 3 种排序（综合/点赞最多/最新），默认取点赞最多的前 3 条转写。

```
"批量转写3条关于跨境电商的抖音视频，按点赞最多排序"
```

### 🔐 登录

**扫码登录** `get_login_qrcode`

在终端生成二维码，用手机抖音扫码即可登录。登录后 Cookie 自动保存，无需重启。

## 快速开始

### 第 1 步：安装依赖

```bash
git clone https://github.com/wuyuxiang2/douyinmcp.git
cd douyinmcp
uv sync
```

如果你还没安装 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc
```

### 第 2 步：登录抖音

```bash
uv run login.py
```

用手机抖音扫码或账号密码登录即可。登录成功后 Cookie 自动保存到 `~/.config/douyinmcp/cookies.txt`，后续不需要重复登录。

### 第 3 步：确认两个路径

后面配置 MCP 时需要用到这两个值，先记下来：

```bash
which uv       # 查看 uv 的完整路径，比如 /Users/你的用户名/.local/bin/uv
pwd             # 查看当前项目目录的完整路径，比如 /Users/你的用户名/douyinmcp
```

> `which uv` 就是问系统"uv 这个命令装在哪里"，`pwd` 就是问"我现在在哪个文件夹"。

### 第 4 步：添加 MCP

根据你使用的工具，选择对应的配置方式。把示例中的路径替换成第 3 步中你记下的真实路径。

---

#### Codex CLI

```bash
codex mcp add douyin -- /你的uv路径/uv --directory /你的项目路径/douyinmcp run main.py
```

#### Claude CLI

```bash
claude mcp add douyin -- /你的uv路径/uv --directory /你的项目路径/douyinmcp run main.py
```

#### Claude Desktop（桌面应用）

用**文本编辑器**（推荐 VS Code 或系统自带的 TextEdit）打开配置文件：

```bash
# Mac 上的文件路径
~/Library/Application Support/Claude/claude_desktop_config.json
```

> 如果这个文件不存在，直接新建一个就行。

在文件中写入（或在已有的 `mcpServers` 里加上 `douyin` 这一段）：

```json
{
  "mcpServers": {
    "douyin": {
      "command": "/你的uv路径/uv",
      "args": ["--directory", "/你的项目路径/douyinmcp", "run", "main.py"]
    }
  }
}
```

保存后**重启 Claude Desktop**，在对话框底部会出现锤子 🔨 图标，说明 MCP 已连接。

#### Cursor

用**文本编辑器**打开配置文件：

```bash
# 项目级配置（仅当前项目生效）
你的项目路径/.cursor/mcp.json

# 或 全局配置（所有项目生效）
~/.cursor/mcp.json
```

> 如果文件不存在，直接新建一个就行。

JSON 格式和 Claude Desktop 一样：

```json
{
  "mcpServers": {
    "douyin": {
      "command": "/你的uv路径/uv",
      "args": ["--directory", "/你的项目路径/douyinmcp", "run", "main.py"]
    }
  }
}
```

保存后，在 Cursor 的 Settings → MCP 中就能看到 douyin 服务已连接。

#### Antigravity（Google Gemini IDE）

在 Antigravity 中打开 MCP Store（左侧边栏），点击 **Manage MCP Servers → View raw config**，会打开配置文件：

```bash
# 文件路径
~/.gemini/antigravity/mcp_config.json
```

在 `mcpServers` 中加上 `douyin`：

```json
{
  "mcpServers": {
    "douyin": {
      "command": "/你的uv路径/uv",
      "args": ["--directory", "/你的项目路径/douyinmcp", "run", "main.py"],
      "timeout": 120000
    }
  }
}
```

> `timeout` 设大一些（120 秒），因为视频转写等操作可能需要较长时间。

保存后在 MCP Store 中刷新，看到 douyin 显示为 connected 即可。

---

到这里，搜索、看评论、下载视频这些功能已经能用了。

### 第 5 步：配置 ASR 密钥（需要你自己操作！）

> ⚠️ **重要提示**：ASR 密钥包含你的私人 API Key，**请你自己在系统终端里手动配置**，不要让 AI 帮你操作这一步，避免密钥泄露。

如果你需要用"视频转文字"功能，需要配一个 ASR 服务商的 API Key。下面以硅基流动（免费额度最多）为例。

**方式 A：写到 MCP 配置里（推荐）**

适合 CLI 工具（Codex / Claude CLI）：在终端重新添加 MCP 时带上密钥：

```bash
# Codex CLI
codex mcp add douyin \
  --env ASR_PROVIDER=siliconflow \
  --env SILICONFLOW_API_KEY='sk-你的Key' \
  -- /你的uv路径/uv --directory /你的项目路径/douyinmcp run main.py

# Claude CLI
claude mcp add douyin \
  -e ASR_PROVIDER=siliconflow \
  -e SILICONFLOW_API_KEY=你的Key \
  -- /你的uv路径/uv --directory /你的项目路径/douyinmcp run main.py
```

适合 GUI 工具（Claude Desktop / Cursor）：在 JSON 配置中加上 `env` 字段：

```json
{
  "mcpServers": {
    "douyin": {
      "command": "/你的uv路径/uv",
      "args": ["--directory", "/你的项目路径/douyinmcp", "run", "main.py"],
      "env": {
        "ASR_PROVIDER": "siliconflow",
        "SILICONFLOW_API_KEY": "sk-你的Key"
      }
    }
  }
}
```

**方式 B：写到 `~/.zshrc` 里（全局生效，所有工具都能用）**

```bash
nano ~/.zshrc
```

在文件末尾加上：

```bash
export ASR_PROVIDER=siliconflow
export SILICONFLOW_API_KEY='sk-你的Key'
```

保存退出后执行 `source ~/.zshrc` 使其生效。

> 两种方式都是通过系统环境变量传入，编程 AI 无法通过读取项目文件看到你的密钥。

### 第 6 步：开始使用

配好以后，直接对 AI 说就行：

- `帮我检查抖音登录状态`
- `搜索 5 条关于 AI 编程 的抖音视频，按点赞最多排序`
- `把第一条视频的前 10 条评论读给我`
- `下载刚才那条视频到 ~/Downloads`
- `把这条视频转成文字`
- `批量转写 3 条关于 跨境电商 的抖音视频`

## Cookie 说明

运行 `uv run login.py` 登录后，Cookie 自动保存到 `~/.config/douyinmcp/cookies.txt`，后续使用时程序会自动读取，**你不需要手动操作任何 Cookie 相关的事情**。

如果你需要自定义 Cookie 路径，可以设置环境变量 `DOUYIN_COOKIE_PATH`。

## 文件输出位置

所有产出文件**默认放在 `~/Downloads/douyinmcp/` 下**，统一管理，不污染项目目录：

| 内容 | 默认位置 | 修改方式 |
|------|---------|---------|
| Cookie | `~/.config/douyinmcp/cookies.txt` | `DOUYIN_COOKIE_PATH` |
| 下载视频/图片 | `~/Downloads/douyinmcp/` | `DOUYIN_DOWNLOAD_DIR` |
| 转写文本 `.txt` | `~/Downloads/douyinmcp/transcripts/` | `DOUYIN_TRANSCRIPT_DIR` |

> 不需要手动创建这些文件夹，程序会在第一次使用时自动创建。

## 哪些配置需要你填

绝大多数配置**不需要你动**，代码里都有合理的默认值：

| 配置 | 是否需要填 | 说明 |
|------|-----------|------|
| Cookie | ✅ 需要，但 `login.py` 自动搞定 | 登录后自动保存 |
| ASR 密钥 | ⚠️ 只有**视频转文字**才需要 | 搜索、下载、评论等功能不需要 |
| 下载目录 | ❌ 不需要 | 默认 `~/Downloads/douyinmcp/` |
| 转写目录 | ❌ 不需要 | 有默认路径 |
| OCR 配置 | ❌ 不需要 | 额外装一下依赖即可 |
| 音频切片参数 | ❌ 不需要 | 长视频自动处理 |

## 配置读取方式

所有配置**只从系统环境变量读取**，包括：

- MCP `--env` 传入的
- `~/.zshrc` 里 `export` 的
- 系统级环境变量

项目目录下不需要创建任何 `.env` 文件。`.env.example` 仅作为环境变量参考文档存在。

## 支持的 ASR 服务商

| 服务商 | 配置变量 | 说明 |
|--------|---------|------|
| `siliconflow`（默认） | `SILICONFLOW_API_KEY` | 硅基流动，使用 SenseVoice 模型 |
| `volcengine` | `VOLCENGINE_APP_ID` + `VOLCENGINE_ACCESS_TOKEN` | 火山引擎（字节跳动） |
| `openai` | `OPENAI_API_KEY` | OpenAI Whisper |
| `custom` | `ASR_API_URL` + `ASR_API_KEY` | 任何兼容 OpenAI Whisper 接口的服务 |

## 项目结构

```
douyinmcp/
├── main.py              # 入口
├── login.py             # 扫码登录
├── pyproject.toml       # 依赖管理
├── src/
│   ├── server.py        # MCP 工具定义（15个工具）
│   ├── client.py        # 抖音 API 客户端
│   ├── config.py        # 配置管理
│   ├── errors.py        # 统一错误处理
│   ├── models.py        # 数据模型
│   ├── sign.py          # 签名生成（本地 V8 引擎）
│   ├── cookies.py       # Cookie 解析
│   ├── token_manager.py # Token 管理
│   ├── ocr.py           # OCR 识别
│   ├── asr/             # 语音转文字（4种服务商）
│   └── video/           # 视频处理和音频提取
├── tests/               # 单元测试和联机测试
└── LICENSE
```


## Acknowledgements

本项目在早期开发阶段参考了 [hhy5562877/douyin_mcp](https://github.com/hhy5562877/douyin_mcp) 的代码结构和接口设计思路，用来帮助梳理抖音网页接口结构、字段映射和 MCP 工具设计方向。感谢原作者提供的启发和思路。

## 免责声明

本项目仅供学习和研究使用。使用本项目获取的数据应遵守抖音平台的服务条款和相关法律法规。请勿将本项目用于任何商业用途或违法行为。

## License

[MIT](LICENSE)
