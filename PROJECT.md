# Project: AromotionAI-backend

## Architecture
AromotionAI is an AI-assisted tool for perfumers. The backend is built using Python 3.11+, FastAPI, SQLAlchemy (SQLite/PostgreSQL), and Playwright/curl_cffi for data collection.

### Core Architecture Components
1. **API Layer (`app/api/v1`)**: Exposes REST and SSE endpoints for Cookie management, analysis tasks, and fragrance recommendations.
2. **Platform Collectors (`app/platforms`)**: Collects user profile, post list, and comments. Uses a double-channel strategy (curl_cffi / Playwright).
3. **Media Processor (`app/analyzers/media_processor.py`)**: Preprocesses images (resizing, converting format) and extracts video frames using ffmpeg.
4. **Analyzers (`app/analyzers`)**: Performs visual and semantic analysis using AI models.
5. **AI Registry (`app/ai`)**: Manages GLM, DeepSeek, and OpenAI providers with a unified API.
6. **Task Manager & SSE (`app/core`)**: Handles asynchronous background tasks and pushes real-time progress via Server-Sent Events.
7. **Fragrance Engine (`app/fragrance`)**: Leverages Iceberg Theory via prompt engineering to suggest fragrance plans.

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| E2E | E2E Testing Suite | Create independent, requirement-driven E2E tests (Tiers 1-4) | None | DONE (TEST_READY.md published) |
| 1 | Infrastructure & Cookie Mgmt | DB setup, models, configuration, and `/api/v1/cookies` endpoints | None | DONE (Commit: ec2b7194) |
| 2 | Data Collection & Media Proc | Douyin data collector (Playwright/curl) and ffmpeg media processing | M1 | DONE |
| 3 | AI Analyzers & Profile Agg | Visual and semantic analyzers, profile aggregator | M1, M2 | DONE (Commit: 3e7ccbe) |
| 4 | Task Manager & SSE API | Background task scheduling, SSE progress stream, task list API | M1, M2, M3 | PLANNED |
| 5 | Fragrance Recommend Engine | Iceberg model prompting, Chat API, historical session management | M1, M4 | PLANNED |
| 6 | Integration & Final Gate | Pass 100% of E2E test suite and adversarial coverage hardening | M1, M2, M3, M4, M5, E2E | PLANNED |

---

## Interface Contracts

### 1. Cookie Management Service
- `validate_cookie(platform: str) -> bool`
- `get_valid_cookie(platform: str) -> PlatformCookie | None`

### 2. Platform Collector Interface
- `get_blogger_profile(blogger_url: str) -> BloggerProfile`
- `get_blogger_posts(blogger_uid: str, count: int) -> list[Post]`
- `collect_comments(post_id: str, count: int) -> list[Comment]`
- `select_posts(posts: list[dict], config: dict) -> list[dict]`

### 3. Media Processor Interface
- `preprocess_image(input_path: str, output_path: str = None) -> str`
- `extract_video_frames(video_path: str, output_dir: str, frame_count: int) -> list[str]`
- `create_grid_image(image_paths: list[str], output_path: str, grid_size: int, cell_size: int) -> str`

### 4. AI Registry & Analyzers
- `BaseAIProvider.chat_completion(prompt: str, images: list[str] = None) -> dict`
- `VisualAnalyzer.analyze_cover(image_path: str) -> dict`
- `CommentAnalyzer.analyze_comments(comments: list[dict]) -> dict`
- `ProfileAggregator.aggregate(...) -> ProfileReport`

### 5. Task Manager & Async Engine
- `TaskManager.submit(task_id: str, coro) -> None`
- `TaskManager.emit(task_id: str, event_type: str, data: dict) -> None`
- `TaskManager.subscribe(task_id: str) -> AsyncIterator[dict]`

---

## Code Layout

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI entry point
│   ├── config.py                   # Configuration management
│   ├── database.py                 # SQLAlchemy connection
│   │
│   ├── api/                        # API routes
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # v1 main router
│   │   │   ├── analysis.py         # Part1: analysis APIs
│   │   │   ├── fragrance.py        # Part2: fragrance APIs
│   │   │   ├── cookies.py          # Cookie management APIs
│   │   │   └── tasks.py            # Task status APIs
│   │   └── deps.py                 # Dependencies
│   │
│   ├── models/                     # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── analysis.py             # Analysis task model
│   │   ├── blogger.py              # Blogger data model
│   │   ├── profile.py              # Profile tags model
│   │   ├── fragrance.py            # Fragrance recommendation model
│   │   └── cookie.py               # Cookie model
│   │
│   ├── schemas/                    # Pydantic validation schemas
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── fragrance.py
│   │   ├── cookie.py
│   │   └── common.py
│   │
│   ├── services/                   # Business logic layers
│   │   ├── __init__.py
│   │   ├── analysis_service.py     # Analysis workflow orchestration
│   │   ├── fragrance_service.py    # Fragrance recommendation service
│   │   └── cookie_service.py       # Cookie management service
│   │
│   ├── core/                       # Core modules
│   │   ├── __init__.py
│   │   ├── task_manager.py         # Async task manager
│   │   ├── sse.py                  # SSE utilities
│   │   └── exceptions.py           # Custom exceptions
│   │
│   ├── platforms/                  # Platform data collectors
│   │   ├── __init__.py
│   │   ├── base.py                 # Platform abstract base class
│   │   ├── douyin/                 # Douyin collector
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   ├── parser.py
│   │   │   └── config.py
│   │   └── xiaohongshu/            # Red/Little Red Book (reserved)
│   │       └── __init__.py
│   │
│   ├── analyzers/                  # Pluggable AI analyzers
│   │   ├── __init__.py
│   │   ├── base.py                 # Base analyzer class
│   │   ├── visual_analyzer.py      # Vision analysis (covers, frames)
│   │   ├── comment_analyzer.py     # Semantic analysis of comments
│   │   ├── profile_aggregator.py   # Merges analysis to 4-dimension report
│   │   └── media_processor.py      # Media scaling/ffmpeg frames helper
│   │
│   ├── ai/                         # LLM provider integration
│   │   ├── __init__.py
│   │   ├── base.py                 # Base AI provider class
│   │   ├── provider_glm.py         # Zhipu GLM API
│   │   ├── provider_openai.py      # OpenAI API
│   │   ├── provider_deepseek.py    # DeepSeek API
│   │   └── registry.py             # Model registration registry
│   │
│   ├── fragrance/                  # Fragrance recommendation engine
│   │   ├── __init__.py
│   │   ├── base.py                 # Recommender engine base class
│   │   ├── iceberg_model.py        # Iceberg theory prompting implementation
│   │   ├── prompt_templates.py     # Prompts definitions
│   │   └── chat.py                 # Interactive chat session management
│   │
│   └── storage/                    # File storage layer
│       ├── __init__.py
│       ├── base.py                 # Storage interface base
│       ├── local.py                # Local storage
│       └── cloud.py                # Cloud storage (reserved)
│
├── alembic/                        # DB migrations
├── alembic.ini
├── pyproject.toml                  # Python dependency definition
└── data/                           # Runtime storage
    ├── db/                         # SQLite databases
    ├── media/                      # Downloaded images & video frames
    └── cookies/                    # Uploaded Cookie JSONs
```
