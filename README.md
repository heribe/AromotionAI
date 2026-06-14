<div align="center">

# AromotionAI

**面向调香师的 AI 创香决策助手**

通过分析社交媒体博主及其粉丝群体画像，生成用户标签，再基于冰山理论模型预测香调方向，辅助调香师进行创香决策。

![Frontend MVP](https://img.shields.io/badge/前端-Frontend%20MVP-3c8c5a?style=flat-square)
![Backend MVP](https://img.shields.io/badge/后端-Backend%20MVP-3c8c5a?style=flat-square)
![Frontend-Backend Integrated](https://img.shields.io/badge/前后端-全链路打通-3c8c5a?style=flat-square)
![React 19](https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646cff?style=flat-square&logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.1.0-009688?style=flat-square&logo=fastapi&logoColor=white)
![Tests](https://img.shields.io/badge/tests-229%20passed-brightgreen?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker&logoColor=white)

</div>

---

## 一、概述

**AromotionAI** 是一款为**调香师**打造的 AI 辅助工具。它从社交媒体博主链接出发，自动完成「数据采集 → 画像分析 → 标签生成 → 香调推荐」的全链路工作，让调香决策从经验驱动走向数据驱动。

**核心价值**：把"博主的粉丝群体是怎样一群人"翻译成"应该调出怎样一支香水"。

### 核心流程

```
输入博主链接
      ↓
┌─────────────────────────────────────────┐
│  Part 1 · 用户画像分析                  │
│  数据采集 → 视觉/评论分析 → 四维度标签   │
└─────────────────────────────────────────┘
      ↓  (调香师微调标签)
┌─────────────────────────────────────────┐
│  Part 2 · 香调推荐                      │
│  冰山理论推理 → 多套香调方案 → 对话微调  │
└─────────────────────────────────────────┘
      ↓
生成结果落入历史记录
```

> **前后端已全链路打通**：从「输入博主链接 → SSE 实时进度 → 画像报告 → 标签筛选 → 香调生成 → 对话微调」全程走真实后端数据。后端经 L1–L4 端到端验证（真实抖音数据 + 真实 GLM），详见 [`PROGRESS.md`](PROGRESS.md)。

---

## 二、核心特性

### Part 1 · 用户画像分析

- **四维度标签体系**：气候-消费带、香氛消费推断、穿搭-香调映射、生活方式-用香场景
- **三档预设分析等级**：快速 / 标准 / 深度，无需复杂配置即可上手
- **SSE 实时进度推送**：每个子步骤状态变更可观测
- **多维度可视化**：每个维度均以图表 + 比例 + 文字总结呈现

### Part 2 · 香调推荐

- **冰山理论分层推理**：显性行为层 → 情感/价值层 → 潜意识/内在需求
- **沉浸式三栏调配室**：参考资料坞 + 配方画布 + AI 助手，避免页面跳转割裂感
- **内嵌式精油萃取动画**：推理过程以可视化动画呈现，配合终端日志
- **对话式微调**：对生成方案进行追问、修改、重新生成

### 工程设计

**后端**
- **AI 模型可插拔**：GLM（文本 `glm-5.2` / 视觉 `glm-4.6v`） / OpenAI / DeepSeek 通过 Provider 接口接入，按槽位（chat / vision / fragrance）绑定 ✅
- **平台采集器可扩展**：抽象 `PlatformCollector` 接口，抖音采集器已落地（curl_cffi 主通道 + Playwright 评论采集），预留小红书 / 微博
- **双通道采集策略**：curl_cffi（轻量 API，抓博主资料 / 作品列表）+ Playwright（浏览器自动化，抓评论，含真实 IP 属地）
- **存储层可切换**：本地 / 云存储抽象统一接口；开发用 SQLite 零迁移开箱即用，生产可切 PostgreSQL
- **SSE 实时进度**：`TaskManager` 内存级任务编排，`/analysis/{task_id}/progress` 推送 7 个子步骤状态 ✅
- **测试基线**：**229 passed / 11 skipped / 0 failed**（164 单元 + 65 e2e 打真实 `app/`），L1–L4 分层端到端验证累计修复 10 个单测盲区问题

**前端对接层**（后端零改动，适配层在前端）
- **HTTP 客户端**：`services/http.ts` 统一 axios 实例 + 响应拦截器自动解包 `BaseResponse{code,message,data}` 信封
- **适配层**：`services/adapters.ts` 负责后端 snake_case ↔ 前端 camelCase 字段映射、报告 dict→dimensions 数组转换、标签 key 透传
- **SSE 客户端**：`services/sse.ts` 封装 EventSource，解析 `progress`/`step_complete`/`complete`/`error` 四类事件
- **数据源门面**：`services/index.ts` 通过 `VITE_USE_MOCK` 环境变量切换真实后端 / Mock 数据，保留离线预览能力
- **Vite 代理**：开发环境 `/api/v1` 自动转发到后端 `:8000`，同源避免 CORS

---

## 三、效果预览

> 截图位于 `docs/screenshots/`，依次为首页、画像报告、标签筛选、调配室。

<table>
  <tr>
    <td width="50%" align="center"><b>首页 · 任务工作台</b></td>
    <td width="50%" align="center"><b>画像报告 · 四维度分析</b></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/dashboard.png" alt="首页任务工作台"></td>
    <td><img src="docs/screenshots/profile-report.png" alt="画像报告"></td>
  </tr>
  <tr>
    <td align="center"><b>标签筛选</b></td>
    <td align="center"><b>调配室 · 三栏沉浸式工作台</b></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/tag-selection.png" alt="标签筛选"></td>
    <td><img src="docs/screenshots/fragrance-lab.png" alt="调配室三栏工作台"></td>
  </tr>
</table>

---

## 四、技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 | React 19 / Vite 8 / TypeScript 5 | 核心框架 + 构建 |
| 前端 UI | Ant Design 6 / @ant-design/charts / lucide-react | 组件库 + 图表 + 矢量图标 |
| 前端状态 | Zustand / React Router v6 | 轻量状态管理 + 路由 |
| 前端请求 | Axios | HTTP 客户端 |
| 后端 | FastAPI / SQLAlchemy 2 / Pydantic 2 | Web 框架 + ORM + 校验（开发 SQLite 零迁移） |
| 后端采集 | curl_cffi / Playwright / ffmpeg | 反反爬 API 通道 + 浏览器自动化 + 视频抽帧 |
| AI 能力 | GLM `glm-5.2`（文本）/ `glm-4.6v`（视觉） | 可插拔 Provider，按槽位绑定，预留 OpenAI / DeepSeek |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | 通过 SQLAlchemy 切换 |
| 实时通信 | SSE (Server-Sent Events) | 任务进度推送 |
| 测试 | pytest / pytest-asyncio / httpx | 229 用例（单元 + e2e 打真实 app） |
| 部署 | Docker / Docker Compose / Nginx | 容器化一键部署，nginx 反代 + SSE 透传 |
| 工具链 | uv (Python) / npm (前端) | 包管理 |

---

## 五、项目结构

```
AromotionAI/
├── backend/                    # 后端项目 (FastAPI + SQLAlchemy + Playwright)
│   ├── app/
│   │   ├── api/v1/             # REST + SSE 路由：cookies / analysis / fragrance
│   │   ├── platforms/douyin/   # 抖音采集器（curl_cffi 主 + Playwright 评论）
│   │   ├── analyzers/          # 视觉/评论分析 + 画像聚合 + 媒体处理（ffmpeg）
│   │   ├── engines/            # 香调推荐引擎（冰山理论 Prompt 工程）
│   │   ├── ai/                 # AI Provider（GLM/OpenAI/DeepSeek）+ 槽位绑定
│   │   ├── services/           # 业务编排（Analysis / Fragrance / Cookie / Task）
│   │   ├── core/               # TaskManager（SSE 进度）等基础设施
│   │   ├── models/  schemas/   # SQLAlchemy 模型 + Pydantic 校验
│   │   └── config.py           # Settings（读 .env）
│   ├── tests/                  # 单元测试 + e2e（打真实 app，mock 隔离外部依赖）
│   ├── Dockerfile              # 后端镜像（Playwright 官方镜像 + ffmpeg）
│   ├── .dockerignore
│   └── data/                   # SQLite + 媒体 + cookie（已 gitignore）
├── frontend/                   # 前端项目 (React + Vite + TS)
│   └── src/
│       ├── pages/              # 页面：Dashboard / TaskProgress / ProfileReport / TagSelection / FragranceRecommend
│       ├── components/         # 公共与布局组件
│       ├── services/           # 对接层：http / api / adapters / sse / index(门面) + Mock 数据
│       ├── stores/             # Zustand 状态管理（analysis / fragrance）
│       ├── types/              # TypeScript 类型定义（数据契约）
│       └── router/             # 路由配置
│   ├── Dockerfile              # 前端镜像（node build → nginx 托管）
│   ├── nginx.conf              # 静态托管 + SPA fallback + 反代后端（含 SSE 配置）
│   └── .dockerignore
├── docs/                       # 开发文档（唯一事实来源 SSOT）
│   ├── 00-global-dev-guide.md  # 全局架构与开发规范
│   ├── 01-part1-backend.md     # Part1 后端开发文档
│   ├── 02-part1-frontend.md    # Part1 前端开发文档
│   ├── 03-part2-backend.md     # Part2 后端开发文档
│   ├── 04-part2-frontend.md    # Part2 前端开发文档
│   └── screenshots/            # README 截图资源
├── docker-compose.yml          # 单机部署编排（backend + frontend/nginx）
├── .env.example                # 部署环境变量模板（GLM_API_KEY 等）
├── PROJECT.md                  # 架构 / 里程碑 / 接口契约 / 代码布局
├── PROGRESS.md                 # 开发进度 + L1–L4 端到端验证记录
├── DEPLOY.md                   # 部署指南（Docker Compose）
└── README.md
```

> 后端启动、配置、测试详见 [`backend/README.md`](backend/README.md)；服务器部署详见 [`DEPLOY.md`](DEPLOY.md)；本地开发见下文「快速开始」。

---

## 六、快速开始

### 环境要求

| 工具 | 最低版本 | 说明 |
|---|---|---|
| Node.js | 18+ | 前端运行环境 |
| npm | 9+ | 随 Node 安装 |
| Python | 3.11+ | 后端运行环境 |
| [uv](https://docs.astral.sh/uv/) | latest | Python 包管理 |
| ffmpeg | — | 后端视频抽帧（图片处理不强依赖，缺失会降级） |

### 前端

```bash
# 克隆仓库
git clone <repo-url>
cd AromotionAI

# 安装前端依赖
cd frontend
npm install
npm run dev       # 启动开发服务器 → http://localhost:5173
```

其他可用脚本：

| 命令 | 作用 |
|---|---|
| `npm run dev` | 启动 Vite 开发服务器（HMR） |
| `npm run build` | 类型检查 + 生产构建 |
| `npm run preview` | 本地预览生产构建产物 |
| `npm run lint` | ESLint 代码检查 |

### 后端

```bash
cd backend
uv sync                                  # 安装依赖
cp .env.example .env                     # 编辑 .env，填入 GLM_API_KEY（必填）
uv run playwright install chromium       # 评论采集需要的浏览器（约 294MB）

# 启动服务 → http://localhost:8000
uv run uvicorn app.main:app --reload --port 8000
```

- API 文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- 启动后 SQLite 自动建表，零迁移开箱即用

> 抖音采集还需把浏览器导出的 Cookie（JSON 数组格式）放到 `backend/data/cookies/douyin.json`，采集器会自动读取。完整配置项见 [`backend/README.md`](backend/README.md)。

### 测试

```bash
cd backend
# 单元测试（mock 模式，不调真实 AI / 抖音 API）
AROMOTION_TEST_MODE=mock uv run pytest --ignore=tests/e2e
# 端到端测试（打真实 app，仍用 mock 隔离外部依赖）
AROMOTION_TEST_MODE=mock uv run pytest tests/e2e/
```

### 前端路由

| 路径 | 页面 |
|---|---|
| `/dashboard` | 首页 / 任务工作台（默认入口） |
| `/task/:taskId` | 任务进度（SSE 实时 7 子步骤） |
| `/report/:taskId` | 画像报告 |
| `/tags/:taskId` | 标签筛选 |
| `/recommend/:id` | 香调调配室（id 为 sessionId） |

### 前后端联调

前后端已**全链路打通**，开发环境默认走真实后端：

- 前端通过 `VITE_API_BASE=/api/v1`（相对路径）发请求，Vite dev server 的 `server.proxy` 自动转发到后端 `:8000`，同源避免 CORS
- 切回纯前端预览（无需后端）：在 `frontend/.env.development` 设 `VITE_USE_MOCK=true`，前端走 `mockData.ts` / `mockFragranceData.ts` 提供模拟数据
- 数据流：页面 → Zustand store → `services/index.ts`（数据源门面，按 `VITE_USE_MOCK` 选 mock 或真实）→ `services/api.ts`（真实）→ `services/http.ts`（axios + 信封解包）→ `services/adapters.ts`（字段映射）

> 前端对接层详情见上文「工程设计 → 前端对接层」。

---

## 七、开发路线图

### 已完成 ✅

| 内容 | 说明 |
|---|---|
| 前端 MVP | 4 个核心页面 + 路由 + 布局 |
| 画像报告四维度可视化 | 气候-消费带 / 香氛消费 / 穿搭-香调 / 生活方式（地域分布基于真实 IP 属地） |
| 调配室三栏工作台 | 参考资料坞 + 配方画布 + AI 助手 + 精油萃取动画 |
| 后端基础设施 (M1) | DB 模型 / 配置 / `/api/v1/cookies` 端点 |
| 抖音数据采集 (M2) | curl_cffi 资料+作品 / Playwright 评论 / ffmpeg 抽帧 |
| AI 分析器与画像聚合 (M3) | 视觉 `glm-4.6v` + 评论 `glm-5.2` + ProfileAggregator 四维度 |
| 任务管理与 SSE (M4) | TaskManager + AnalysisService 编排 + 17 个 REST/SSE 端点 |
| 香调推荐引擎 (M5) | 冰山理论 Prompt 工程 + 多方案生成 + 对话微调 |
| 集成与测试 (M6) | 229 用例全绿（164 单元 + 65 e2e 打真实 app） |
| L1–L4 端到端验证 | 真实抖音数据 + 真实 GLM 跑通完整业务闘环，修复 10 个单测盲区 |
| **前后端全链路对接** | 前端适配层（http/api/adapters/sse/门面）+ SSE 进度页，全程走真实后端 |
| **Docker Compose 部署** | 两容器（backend + frontend/nginx），SSE 透传 + 数据卷持久化 |

### 进行中 / 规划 ⏳

| 内容 | 说明 |
|---|---|
| 香材 notes 结构化 | 后端 GLM 偶尔未按结构返回前/中/后调香材，需加强 prompt 或解析兜底 |
| SSE 前端流式 | provider 流式目前仅内部累积，前端实时显示生成过程需全链路透传 |
| HTTPS / 域名 | 当前 HTTP + IP，后续在 nginx 加 Let's Encrypt 或前置 Caddy |
| 运行时配置模块 | 分析等级预设 / AI 槽位绑定提升为 HTTP 接口（10 个 e2e 待解除 skip） |
| Cookie 上传 UI | 前端管理抖音 Cookie（当前靠 `douyin.json` 文件 fallback） |
| 更多平台采集器 | 小红书 / 微博（接口已预留） |

> 里程碑详细状态见 [`PROGRESS.md`](PROGRESS.md)，架构与接口契约见 [`PROJECT.md`](PROJECT.md)，部署见 [`DEPLOY.md`](DEPLOY.md)。

---

## 八、部署

单机部署：**Linux VPS + Docker Compose**，两个容器（前端 nginx + 后端 FastAPI），SQLite 持久化到宿主机卷。

```bash
# 1. 上传代码 + 配置环境变量
git clone <repo> aromotion && cd aromotion
cp .env.example .env          # 填 GLM_API_KEY

# 2. 放置抖音 Cookie
mkdir -p data/backend/cookies # 把 douyin.json 放这里

# 3. 一键启动（首次构建 5-15 分钟）
docker compose up -d --build
```

访问 `http://<服务器IP>` 即可。关键设计：
- **Playwright 官方镜像**：自带 chromium + 系统依赖，规避浏览器自动化安装坑
- **nginx SSE 专项配置**：`proxy_buffering off` + 600s 超时，保证任务进度实时推送
- **数据卷**：SQLite / 媒体 / Cookie 挂载到宿主机，容器重建不丢
- **敏感凭据**：GLM_API_KEY 走宿主机 `.env`（不入库），Cookie 手动上传到挂载卷

> 完整部署步骤、运维（日志/重启/备份/Cookie 更新）、FAQ 详见 [`DEPLOY.md`](DEPLOY.md)。

---

## 九、文档导航

| 文档 | 内容 |
|---|---|
| [DEPLOY.md](DEPLOY.md) | **部署指南**：Docker Compose 单机部署、运维、FAQ |
| [backend/README.md](backend/README.md) | 后端启动、Cookie 配置、环境变量、测试 |
| [PROGRESS.md](PROGRESS.md) | 里程碑进度 + L1–L4 端到端验证记录（含 10 个修复） |
| [PROJECT.md](PROJECT.md) | 架构、里程碑、接口契约、完整代码布局 |
| [00-global-dev-guide.md](docs/00-global-dev-guide.md) | 全局架构、技术栈、API 规范、数据模型（SSOT） |
| [01-part1-backend.md](docs/01-part1-backend.md) | Part1 后端：采集、分析、画像生成 |
| [02-part1-frontend.md](docs/02-part1-frontend.md) | Part1 前端：画像报告、标签筛选 UI |
| [03-part2-backend.md](docs/03-part2-backend.md) | Part2 后端：冰山模型、香调推理、对话 |
| [04-part2-frontend.md](docs/04-part2-frontend.md) | Part2 前端：调配室三栏工作台 |

---

<div align="center">

<sub>Built with React · Vite · TypeScript · Ant Design · FastAPI · SQLAlchemy · Playwright · GLM</sub>

</div>
