# Douyin MCP Server

让 AI 助手直接读取抖音内容：搜索视频、查看详情、抓评论、分析博主、下载视频、语音转文字。

这个项目适合几类场景：

- 内容选题和行业调研
- 竞品账号分析
- 评论区观点收集
- 教程类视频知识提取
- 把抖音内容接进 Codex / Claude CLI 这类 AI 工作流

## 项目价值

相比手动刷抖音，这个项目的价值不是“替你看视频”，而是把抖音变成一个可被 AI 调用的数据入口：

- AI 可以直接搜索指定关键词的视频
- AI 可以读取视频详情、评论、回复和博主信息
- AI 可以下载视频到本地继续处理
- AI 可以把视频语音自动转成文字，并保存为本地 `.txt`
- 你可以把这些能力接到自己的研究、整理、归档流程里

## 功能概览

当前提供 16 个 MCP 工具：

| 工具 | 用途 |
|------|------|
| `get_login_qrcode` | 获取扫码登录入口 |
| `check_login_status` | 检查当前 Cookie 是否有效 |
| `logout` | 清除本地 Cookie 文件，退出当前登录 |
| `search_videos` | 搜索视频 |
| `get_video_detail` | 获取单条视频详情 |
| `get_video_comments` | 获取评论 |
| `get_sub_comments` | 获取评论回复 |
| `resolve_share_url` | 解析抖音分享短链接 |
| `get_user_info` | 获取博主资料 |
| `get_user_posts` | 获取博主作品列表 |
| `get_homefeed` | 获取推荐流 |
| `download_video` | 下载视频到本地 |
| `download_aweme_images` | 下载图文作品中的全部图片 |
| `ocr_aweme_images` | 下载并 OCR 识别图片文字 |
| `transcribe_video` | 单条视频转文字 |
| `batch_transcribe` | 批量搜索并转写视频 |

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/yourname/douyinmcp.git
cd douyinmcp
uv sync
```

如果你还没安装 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc
```

### 2. 登录抖音

```bash
uv run login.py
```

默认会打开浏览器，你用手机抖音扫码或账号密码登录即可。

登录成功后，Cookie 默认保存到：

```bash
~/.config/douyinmcp/cookies.txt
```

如果你想退出登录，可以用两种方式：

```bash
uv run login.py --logout
```

或者直接让 AI 调用：

```text
退出抖音登录
```

### 3. 配置到 Codex CLI

先确认两个路径：

```bash
which uv
pwd
```

然后添加 MCP：

```bash
codex mcp add douyin -- /Users/你的用户名/.local/bin/uv --directory /项目完整路径/douyinmcp run main.py
```

如果你还要用视频转文字，再额外带上 ASR 环境变量。以火山引擎为例：

```bash
codex mcp add douyin \
  --env ASR_PROVIDER=volcengine \
  --env VOLCENGINE_APP_ID=你的AppID \
  --env VOLCENGINE_ACCESS_TOKEN='你的AccessToken' \
  --env VOLCENGINE_MODEL=bigmodel \
  --env VOLCENGINE_RESOURCE_ID=volc.bigasr.auc_turbo \
  --env VOLCENGINE_API_URL='https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash' \
  -- /Users/你的用户名/.local/bin/uv --directory /项目完整路径/douyinmcp run main.py
```

### 4. 配置到 Claude CLI

```bash
claude mcp add douyin -- /Users/你的用户名/.local/bin/uv --directory /项目完整路径/douyinmcp run main.py
```

如果你需要语音转文字，同样补上 ASR 变量即可：

```bash
claude mcp add douyin \
  -e ASR_PROVIDER=volcengine \
  -e VOLCENGINE_APP_ID=你的AppID \
  -e VOLCENGINE_ACCESS_TOKEN=你的AccessToken \
  -e VOLCENGINE_MODEL=bigmodel \
  -e VOLCENGINE_RESOURCE_ID=volc.bigasr.auc_turbo \
  -e VOLCENGINE_API_URL=https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash \
  -- /Users/你的用户名/.local/bin/uv --directory /项目完整路径/douyinmcp run main.py
```

### 5. 你可以直接这样用

把 MCP 配好以后，可以直接对 AI 说：

- `帮我检查抖音登录状态`
- `搜索 5 条关于 AI 编程 的抖音视频，按点赞最多排序`
- `把第一条视频的前 10 条评论读给我`
- `下载刚才那条视频到 ~/Downloads`
- `下载这条图文作品的所有图片`
- `识别这条图文图片里的文字`
- `把这条视频转成文字`
- `批量转写 3 条关于 跨境电商 的抖音视频`
- `退出抖音登录`

## Cookie 机制说明

这个项目不会把你的 Cookie 硬编码到代码里。代码只会按顺序读取已有登录态：

1. `DOUYIN_COOKIE` 环境变量
2. `DOUYIN_COOKIE_PATH` 指向的文件
3. 默认文件 `~/.config/douyinmcp/cookies.txt`
4. 旧版兼容文件 `./cookies.txt`

所以如果你安装 MCP 后没有被要求重新登录，通常是因为：

- 你的 MCP 配置里已经带了 `DOUYIN_COOKIE`
- 或者本机已经存在有效 Cookie 文件

如果通过 Shell 传 `DOUYIN_COOKIE`，必须加单引号：

```bash
DOUYIN_COOKIE='sessionid=abc; ttwid=xyz' uv run main.py
```

## 视频转文字说明

只有 `transcribe_video` 和 `batch_transcribe` 需要 ASR 提供商，其他抖音数据工具不需要 API Key。
如果你要用图片 OCR，再额外安装 OCR 可选依赖：

```bash
uv sync --extra ocr
```

当前支持：

- `siliconflow`
- `volcengine`
- `openai`
- `custom`（兼容 OpenAI Whisper 风格接口）

### 转写 `.txt` 会放在哪里？

默认保存到：

```bash
~/.local/share/douyinmcp/transcripts
```

每次转写成功后：

- `transcribe_video` 会返回 `saved_path`
- `batch_transcribe` 也会给每条结果返回 `saved_path`

你也可以改保存目录：

```bash
DOUYIN_TRANSCRIPT_DIR=/你自己的目录
```

如果你不想自动保存转写文本，可以关闭：

```bash
DOUYIN_AUTO_SAVE_TRANSCRIPTS=false
```

### 长视频现在怎么处理？

现在超过阈值的长音频会自动切片转写，再合并成一个完整结果。

- 默认超过 `600` 秒自动切片
- 默认每段切成 `480` 秒
- 默认单段超过 `45MB` 也会触发切片
- 默认整个视频最长支持到 `7200` 秒

### 常用环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOUYIN_COOKIE` | - | 直接传 Cookie 字符串 |
| `DOUYIN_COOKIE_PATH` | `~/.config/douyinmcp/cookies.txt` | Cookie 文件路径 |
| `DOUYIN_AUTO_SAVE_TRANSCRIPTS` | `true` | 是否自动保存转写文本 |
| `DOUYIN_TRANSCRIPT_DIR` | `~/.local/share/douyinmcp/transcripts` | 转写文本目录 |
| `OCR_PROVIDER` | `rapidocr` | OCR 提供商（当前支持 rapidocr） |
| `ASR_PROVIDER` | `siliconflow` | ASR 提供商 |
| `ASR_API_KEY` | - | 通用 ASR Key |
| `ASR_API_URL` | - | 自定义 ASR 地址 |
| `ASR_MODEL` | - | 自定义 ASR 模型 |
| `SILICONFLOW_API_KEY` | - | 硅基流动 Key |
| `OPENAI_API_KEY` | - | OpenAI Key |
| `OPENAI_MODEL` | `whisper-1` | OpenAI 模型 |
| `OPENAI_API_URL` | `https://api.openai.com/v1/audio/transcriptions` | OpenAI ASR 地址 |
| `VOLCENGINE_APP_ID` | - | 火山引擎 App ID |
| `VOLCENGINE_ACCESS_TOKEN` | - | 火山引擎 Access Token |
| `VOLCENGINE_MODEL` | `bigmodel` | 火山模型 |
| `VOLCENGINE_MODEL_VERSION` | - | 火山模型版本 |
| `VOLCENGINE_RESOURCE_ID` | `volc.bigasr.auc_turbo` | 火山资源标识 |
| `VOLCENGINE_API_URL` | `https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash` | 火山接口地址 |
| `VOLCENGINE_API_KEY` | - | 旧版兼容字段 |
| `MAX_AUDIO_DURATION` | `7200` | 最大转写时长（秒） |
| `AUDIO_CHUNK_THRESHOLD` | `600` | 超过该时长自动切片 |
| `AUDIO_CHUNK_DURATION` | `480` | 每段切片时长 |
| `AUDIO_CHUNK_MAX_FILE_SIZE_MB` | `45` | 超过该体积自动切片 |

## 安全与 GitHub 发布建议

为了准备公开仓库，建议遵守这几条：

- 不要把真实 `cookies.txt` 放在项目根目录
- 不要把下载的视频、临时研究目录、缓存文件一起提交
- 不要把 API Key 直接写进 README、代码或截图
- 如果历史里曾提交过 Cookie 或 Key，公开前先轮换凭证

本项目默认已经把这些内容往“仓库外”放：

- Cookie 默认放 `~/.config/douyinmcp/cookies.txt`
- 转写文本默认放 `~/.local/share/douyinmcp/transcripts`
- 项目根目录下的 `cookies.txt`、`downloads/`、`transcripts/`、临时目录都不应进入 Git

## 项目结构

```text
douyinmcp/
├── main.py
├── login.py
├── pyproject.toml
├── src/
│   ├── server.py
│   ├── client.py
│   ├── config.py
│   ├── errors.py
│   ├── models.py
│   ├── sign.py
│   ├── token_manager.py
│   ├── asr/
│   └── video/
├── tests/
├── test_tools.py
└── LICENSE
```

## 本地开发

### 语法检查

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPYCACHEPREFIX=/tmp/pycache uv run python -m py_compile \
  main.py login.py test_tools.py src/*.py src/asr/*.py src/video/*.py tests/*.py
```

### 离线单元测试

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPYCACHEPREFIX=/tmp/pycache uv run python -m unittest \
  tests.test_cookie_security tests.test_media_features tests.test_volcengine_provider tests.test_custom_provider -v
```

### 联机测试

先准备好有效 Cookie，再运行：

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPYCACHEPREFIX=/tmp/pycache uv run python tests/test_all.py
```

## Acknowledgements

本项目在早期开发阶段，参考过仓库内曾保留的 `_reference_repo` 对照代码与文档思路，用来帮助梳理抖音网页接口结构、字段映射和 MCP 工具设计方向。

感谢相关开源作者提供的启发和思路。

公开发布版本中，开发期用的对照目录已经移除，避免把无关材料一起带进正式仓库。

## License

[MIT](LICENSE)
