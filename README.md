<div align="center">

# AromotionAI

**面向调香师的 AI 创香决策助手**

通过分析社交媒体博主及其粉丝群体画像，生成用户标签，再基于冰山理论模型预测香调方向，辅助调香师进行创香决策。

![Frontend MVP](https://img.shields.io/badge/前端-Frontend%20MVP-3c8c5a?style=flat-square)
![Backend In Development](https://img.shields.io/badge/后端-In%20Development-c9a227?style=flat-square)
![React 19](https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646cff?style=flat-square&logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-规划中-009688?style=flat-square&logo=fastapi&logoColor=white)

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

- **AI 模型可插拔**：GLM / OpenAI / DeepSeek 等通过 Provider 接口接入，按槽位绑定
- **平台采集器可扩展**：抽象 `PlatformCollector` 接口，首版抖音，预留小红书/微博
- **存储层可切换**：本地 / 云存储抽象统一接口
- **零配置开发**：开发环境使用 SQLite，开箱即用

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
| 后端 (规划) | FastAPI / SQLAlchemy 2 / Alembic / Pydantic 2 | Web 框架 + ORM + 迁移 + 校验 |
| 后端采集 | Playwright / curl_cffi / ffmpeg | 浏览器自动化 + 反反爬 + 视频处理 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | 通过 SQLAlchemy 切换 |
| 实时通信 | SSE (Server-Sent Events) | 任务进度推送 |
| 部署 | Docker + Docker Compose | 容器化 |
| 工具链 | uv (Python) / npm (前端) | 包管理 |

---

## 五、项目结构

```
AromotionAI/
├── docs/                       # 开发文档（唯一事实来源 SSOT）
│   ├── 00-global-dev-guide.md  # 全局架构与开发规范
│   ├── 01-part1-backend.md     # Part1 后端开发文档
│   ├── 02-part1-frontend.md    # Part1 前端开发文档
│   ├── 03-part2-backend.md     # Part2 后端开发文档
│   ├── 04-part2-frontend.md    # Part2 前端开发文档
│   └── screenshots/            # README 截图资源
├── frontend/                   # 前端项目 (React + Vite + TS)
│   └── src/
│       ├── pages/              # 页面：Dashboard / ProfileReport / TagSelection / FragranceRecommend
│       ├── components/         # 公共与布局组件
│       ├── services/           # API 调用封装 + Mock 数据
│       ├── stores/             # Zustand 状态管理
│       ├── types/              # TypeScript 类型定义
│       └── router/             # 路由配置
├── others/                     # 历史实验代码（参考）
└── GEMINI.md                   # AI 助手开发约束
```

> 后端目录 (`backend/`) 暂未落地，规划结构详见 [`docs/00-global-dev-guide.md`](docs/00-global-dev-guide.md) 第三章。

---

## 六、快速开始

### 环境要求

| 工具 | 最低版本 | 说明 |
|---|---|---|
| Node.js | 18+ | 前端运行环境 |
| npm | 9+ | 随 Node 安装 |

### 1. Installation

```bash
# 克隆仓库
git clone <repo-url>
cd AromotionAI

# 安装前端依赖
cd frontend
npm install
```

### 2. How to Run

```bash
# 在 frontend/ 目录下
npm run dev       # 启动开发服务器 → http://localhost:5173
```

其他可用脚本：

| 命令 | 作用 |
|---|---|
| `npm run dev` | 启动 Vite 开发服务器（HMR） |
| `npm run build` | 类型检查 + 生产构建 |
| `npm run preview` | 本地预览生产构建产物 |
| `npm run lint` | ESLint 代码检查 |

### 3. 前端路由

| 路径 | 页面 |
|---|---|
| `/dashboard` | 首页 / 任务工作台（默认入口） |
| `/report/:taskId` | 画像报告 |
| `/tags/:taskId` | 标签筛选 |
| `/recommend` | 香调调配室 |

### 4. 关于后端

后端（FastAPI）目前 **In Development**，暂不可运行。前端当前通过 `src/services/mockData.ts` 和 `mockFragranceData.ts` 提供模拟数据，**无需后端即可完整预览所有页面**。

后端开发完成后，启动方式将在本节补充（基于 `uv` 工具链）。

---

## 七、开发路线图

| 状态 | 内容 |
|---|---|
| ✅ | 前端 MVP（4 个核心页面 + 路由 + 布局） |
| ✅ | 画像报告四维度可视化 |
| ✅ | 调配室三栏工作台 + 精油萃取动画 |
| ⏳ | 后端 API + 数据模型 + Alembic 迁移 |
| ⏳ | 抖音平台数据采集器 |
| ⏳ | AI 模型可插拔接入（GLM / OpenAI / DeepSeek） |
| ⏳ | SSE 实时进度打通前后端 |
| ⏳ | 对话式微调 SSE 流式输出 |
| ⏳ | Docker Compose 一键部署 |

---

## 八、文档导航

| 文档 | 内容 |
|---|---|
| [00-global-dev-guide.md](docs/00-global-dev-guide.md) | 全局架构、技术栈、API 规范、数据模型（SSOT） |
| [01-part1-backend.md](docs/01-part1-backend.md) | Part1 后端：采集、分析、画像生成 |
| [02-part1-frontend.md](docs/02-part1-frontend.md) | Part1 前端：画像报告、标签筛选 UI |
| [03-part2-backend.md](docs/03-part2-backend.md) | Part2 后端：冰山模型、香调推理、对话 |
| [04-part2-frontend.md](docs/04-part2-frontend.md) | Part2 前端：调配室三栏工作台 |

---

<div align="center">

<sub>Built with React · Vite · TypeScript · Ant Design</sub>

</div>
