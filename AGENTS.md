# AGENTS.md

This repository is a Douyin MCP server focused on turning Douyin into an AI-readable workflow tool.

## Product Direction

Treat the project as two layers:

1. `Douyin Lite`
   - Low-friction entry point
   - Easy install, easy start, easy integrate
   - Share URL parsing, downloads, OCR, transcription, basic metadata

2. `Douyin Pro`
   - Logged-in research workflow
   - Search, comments, sub-comments, creator info, creator posts, homefeed
   - Batch processing and deeper analysis

Do not collapse the project into a generic “Agent-Reach clone”. The differentiator is Douyin depth.

## Current Mainline

Keep the mainline focused on:

- Read data
- Download media
- OCR image posts
- Transcribe video
- Batch research workflows

Publishing features are not the current mainline. If implemented, keep them isolated under a dedicated `publisher/` module and mark them experimental.

## Engineering Priorities

### P1

- `douyin-lite` mode
- pip install / one-command startup
- stable streamable HTTP mode
- Docker deployment
- prebuilt binary or bootstrap script
- `docs/install.md` and `docs/update.md`

### P2

- batch image-post processing
- transcript export to `.md` and `.json`
- comment export
- creator analysis report
- topic summary / trend summary

### P3

- AI publish image-post
- AI publish video
- scheduled publishing
- drafts

## Publishing Strategy

Preferred path:

- Official Douyin OpenAPI
- OAuth-based auth
- Long-term maintainable

Fallback path:

- Browser automation
- Faster to demo
- Higher maintenance and platform risk

If both exist, keep OpenAPI as the strategic path and browser automation as experimental only.

## Rules For Future Agents

- Do not hardcode cookies, tokens, or API keys.
- Keep local secrets in `.env.local`, never in `.env.example`.
- Preserve `.gitignore` protections for cookies, downloads, transcripts, and local env files.
- Prefer user-directory storage over repo-local storage for runtime artifacts.
- Keep README product-oriented; keep implementation planning in `docs/`.
- When adding features, update README, tests, and roadmap together.
- Favor MCP-native batch tools over ad hoc scripts when the feature is user-facing.

## Current Known Runtime Conventions

- Cookie default path: `~/.config/douyinmcp/cookies.txt`
- Transcript default path: `~/.local/share/douyinmcp/transcripts`
- Local secret file: `.env.local`
- OCR extra dependency: `uv sync --extra ocr`

## Handoff Notes

Before doing substantial work, read:

1. `README.md`
2. `docs/ROADMAP.md`
3. relevant tests under `tests/`

When changing core behavior, run the offline unit tests first. Live Douyin tests require valid cookies and, for transcription, valid ASR credentials.
