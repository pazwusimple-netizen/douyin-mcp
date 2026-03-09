# Roadmap

This file tracks where the project should go next and how to decide tradeoffs.

## Positioning

The project should be positioned as a Douyin MCP server for research, extraction, and workflow automation.

Core value:

- let AI search Douyin
- let AI read comments and creator context
- let AI download media
- let AI OCR image posts
- let AI transcribe speech into reusable text

The product is strongest when it helps with research and content operations, not when it tries to become a generic agent installer.

## Product Split

### Douyin Lite

Low-friction mode intended for faster adoption and easier integration.

Target characteristics:

- easy install
- minimal configuration
- share-link-first workflow
- strong download / OCR / transcript experience

Candidate scope:

- resolve share URL
- video detail
- download video
- download image posts
- OCR image posts
- single transcription
- simple HTTP / streamable entrypoint

### Douyin Pro

High-depth mode intended for logged-in research and analysis.

Target characteristics:

- search and filtering
- comment and reply access
- creator profile and creator posts
- homefeed exploration
- batch processing
- export and reporting

Candidate scope:

- search videos
- comments and sub-comments
- user info and user posts
- batch transcription
- creator reports
- trend and topic summaries

## Priority Plan

### P1: Distribution And Access

These are the highest-leverage next steps.

1. `douyin-lite` mode
2. pip install / one-command startup
3. stable streamable HTTP mode
4. Docker deployment
5. prebuilt binary or bootstrap script
6. `docs/install.md`
7. `docs/update.md`
8. safe-mode / doctor style diagnostics

Why this matters:

- reduces onboarding friction
- makes the project easier to recommend
- improves compatibility with meta-agent tools

### P2: Differentiated Workflow Features

These deepen the moat.

1. batch image-post processing
2. transcript export to `.md` and `.json`
3. comment export
4. creator analysis reports
5. topic summary / hot topic summary

Why this matters:

- makes the tool useful for researchers and operators
- increases output quality for downstream AI workflows

### P3: Publishing

These should be treated as a separate track.

1. AI publish image-post
2. AI publish video
3. scheduled publishing
4. drafts

Why this is not first:

- different auth model
- different product risk
- different maintenance burden

## Publishing Architecture

If publishing is added, keep it separate from the current read/download pipeline.

Recommended structure:

- current modules keep handling read, download, OCR, transcription
- add a dedicated `publisher/` module for publishing logic
- keep auth separated:
  - read path: cookies
  - publish path: OAuth / OpenAPI tokens

## Recommended Publishing Paths

### Preferred: Official OpenAPI

Pros:

- compliant
- more stable
- suitable for a public GitHub project
- long-term maintainable

Cons:

- OAuth required
- permissions may need approval
- higher integration cost

### Secondary: Browser Automation

Pros:

- faster to demo
- easier to show visible results early

Cons:

- more fragile
- more likely to trigger platform controls
- not suitable as the primary long-term path

## Documentation Strategy

Keep docs separated by audience.

Suggested layout:

- `README.md`: what the project does and how to start
- `AGENTS.md`: guidance for future coding agents
- `docs/ROADMAP.md`: product priorities and architecture direction
- `docs/install.md`: installation and deployment
- `docs/update.md`: upgrade and migration notes

## Non-Negotiables

- do not commit real cookies or API keys
- do not store runtime artifacts in the repo by default
- keep `.env.local` local-only
- update tests when core behavior changes
- avoid feature drift away from Douyin-specific strengths
