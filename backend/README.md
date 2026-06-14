# AromotionAI Backend

FastAPI 后端：抖音博主数据采集 → AI 画像分析 → 香调推荐。

```
采集(curl_cffi/playwright) → 视觉(glm-4.6v)+评论(glm-5.2)分析
  → 聚合画像(四维度标签) → 香调推荐(glm-5.2，冰山理论+多方案)
```

## 快速开始

### 环境要求
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（Python 包管理）
- ffmpeg（视频抽帧用；图片处理不强依赖，缺失会降级）

### 1. 安装依赖
```bash
cd backend
uv sync
```

### 2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env，填入 GLM_API_KEY（必填，智谱开放平台 https://open.bigmodel.cn/）
```
Coding Plan 套餐还需设 `ZHIPUAI_BASE_URL`（见 `.env.example`）。

### 3. 放置抖音 Cookie
前端暂无 Cookie 导入功能，把浏览器导出的抖音 Cookie（JSON 数组格式）放到：
```
backend/data/cookies/douyin.json
```
采集器会自动读取（DB 无 cookie 时回退此文件）。完整说明见
[`.env.example`](.env.example) 或 [docs/01-part1-backend.md §8.3](../docs/01-part1-backend.md)。

### 4. 安装 Playwright 浏览器（评论采集需要）
```bash
uv run playwright install chromium
```
> 仅 `get_blogger_profile` / `get_blogger_posts`（curl_cffi）不需要它；`collect_comments`（评论）的主通道需要。

### 5. 启动服务
```bash
uv run uvicorn app.main:app --reload --port 8000
```
- API 文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

启动后数据库（SQLite）自动建表，零迁移开箱即用。

## 测试
```bash
# 单元测试（mock 模式，不调真实 AI/抖音 API）
AROMOTION_TEST_MODE=mock uv run pytest --ignore=tests/e2e

# 端到端测试（打真实 app，仍用 mock 隔离外部依赖）
AROMOTION_TEST_MODE=mock uv run pytest tests/e2e/
```

## 项目结构
```
backend/
├── app/
│   ├── api/v1/            # FastAPI 路由：cookies / analysis / fragrance
│   ├── platforms/douyin/  # 抖音采集器（curl_cffi 主 + playwright 评论）
│   ├── analyzers/         # 视觉/评论分析 + 画像聚合 + 媒体处理
│   ├── engines/           # 香调推荐引擎（Prompt 工程版）
│   ├── ai/                # AI Provider（GLM/OpenAI/DeepSeek）+ Registry 槽位绑定
│   ├── services/          # 业务编排（AnalysisService / FragranceService / TaskService...）
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic 请求/响应
│   ├── core/              # TaskManager（SSE 进度）等基础设施
│   └── config.py          # Settings（读 .env）
├── tests/                 # 单元测试 + e2e
├── data/                  # SQLite + 媒体 + cookie（已 gitignore）
└── .env.example           # 配置模板
```

## 配置项速查
| 变量 | 必填 | 说明 |
|---|---|---|
| `GLM_API_KEY` | ✅ | 智谱 API Key |
| `ZHIPUAI_BASE_URL` | Coding Plan 必填 | `/api/coding/paas/v4` |
| `GLM_MODEL` / `GLM_VISION_MODEL` | 否 | 默认 glm-5.2 / glm-4.6v |
| `COOKIE_DIR` | 否 | Cookie 文件目录，默认 `./data/cookies` |
| `DATABASE_URL` | 否 | 默认 SQLite，生产可改 PostgreSQL |
| `CORS_ORIGINS` | 否 | 前端地址，默认 `http://localhost:5173` |

## 文档
- [docs/00-global-dev-guide.md](../docs/00-global-dev-guide.md) — 全局架构与开发规范（SSOT）
- [docs/01-part1-backend.md](../docs/01-part1-backend.md) — Part1：采集 / 分析 / 画像
- [docs/03-part2-backend.md](../docs/03-part2-backend.md) — Part2：香调推荐
- [PROGRESS.md](../PROGRESS.md) — 开发进度 + 端到端验证记录（含 10 个修复的来龙去脉）
