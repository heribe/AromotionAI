# AromotionAI — 全局开发文档

> **文档版本**: v1.0  
> **创建时间**: 2026-06-13  
> **文档类型**: 全局架构与开发规范

---

## 一、项目概述

### 1.1 产品定位

AromotionAI 是一款面向**调香师**的 AI 辅助工具，通过分析社交媒体博主及其粉丝群体画像，生成用户标签，再基于冰山理论模型预测香调方向、推荐原因和香调故事，帮助调香师进行创香决策。

### 1.2 核心流程

```
输入博主链接
    ↓
Part1: 用户画像分析 (处于进行中任务列表)
    ├── 数据采集（博主信息、帖子、评论、评论者）
    ├── 内容分析（视觉分析、评论语义分析）
    ├── 标签生成（四维度标签 + 比例）
    └── 首页展示 [查看进度现场] 按钮，点击进入分析详情
    ↓
状态变为 待筛选标签 (waiting_tags)
任务停留在“进行中列表”，并展示 [前往筛选标签] 按钮
    ↓
标签筛选页（系统预选 + 调香师微调）
点击生成后，状态变为 processing，仍在进行中列表
    ↓
Part2: 香调推荐 (处于进行中任务列表)
    ├── 首页展示 [进入调配室] 按钮，点击进入沉浸式三栏工作台
    ├── 中央画布展示“内嵌式精油萃取动画”与实时终端日志，左侧展示已选标签
    ├── 冰山理论模型推理完毕
    ├── 触发“退场过渡”及“阶梯式上浮”动画，多套香调方案平滑浮现
    └── 对话式微调（追问、修改方案）
    ↓
生成全部完成，任务落入历史记录表格
```

### 1.3 系统角色

| 角色 | 第一版 | 后续 |
|---|---|---|
| 调香师 | 主要用户，无需登录 | 需要登录，独立分析历史 |
| 管理员 | 不需要 | 用户管理、系统配置 |

---

## 二、技术栈

### 2.1 前端

| 技术 | 版本建议 | 用途 |
|---|---|---|
| React | 18+ | 核心框架 |
| Vite | 5+ | 构建工具 |
| TypeScript | 5+ | 类型安全 |
| Ant Design | 5+ | UI 组件库 |
| @ant-design/charts | 最新 | 数据可视化图表 |
| React Router | v6 | 前端路由 |
| Zustand | 4+ | 轻量级状态管理 |
| Axios | 最新 | HTTP 请求 |

### 2.2 后端

| 技术 | 版本建议 | 用途 |
|---|---|---|
| Python | 3.11+ | 运行环境 |
| FastAPI | 0.100+ | Web 框架 |
| SQLAlchemy | 2.0+ | ORM |
| Alembic | 最新 | 数据库迁移 |
| Pydantic | 2.0+ | 数据校验 |
| Playwright | 最新 | 浏览器自动化（抖音数据采集） |
| curl_cffi | 最新 | HTTP 请求（反反爬） |
| ffmpeg | 系统安装 | 视频帧提取 / 图片处理 |
| uvicorn | 最新 | ASGI 服务器 |
| uv | 最新 | Python 包管理 |

### 2.3 数据库

| 环境 | 数据库 | 说明 |
|---|---|---|
| 开发 | SQLite | 零配置，开箱即用 |
| 生产 | PostgreSQL | 通过 SQLAlchemy 切换，仅改连接字符串 |

### 2.4 其他

| 技术 | 用途 |
|---|---|
| Docker + Docker Compose | 容器化部署 |
| SSE (Server-Sent Events) | 任务进度实时推送 |
| asyncio | 异步任务队列（第一版，后续可切 Celery） |

---

## 三、项目目录结构

```
<project_root>/
├── docs/                               # 开发文档
│   ├── 00-global-dev-guide.md          # 全局开发文档（本文）
│   ├── 01-part1-backend.md             # Part1 后端开发文档
│   ├── 02-part1-frontend.md            # Part1 前端开发文档
│   ├── 03-part2-backend.md             # Part2 后端开发文档
│   └── 04-part2-frontend.md            # Part2 前端开发文档
│
├── frontend/                           # 前端项目 (React + Vite + TS)
│   ├── public/
│   ├── src/
│   │   ├── assets/                     # 静态资源
│   │   ├── components/                 # 公共组件
│   │   │   ├── Layout/                 # 布局组件
│   │   │   └── common/                 # 通用组件（Loading, ErrorBoundary 等）
│   │   ├── pages/                      # 页面组件
│   │   │   ├── Dashboard/              # 首页/工作台
│   │   │   ├── TaskProgress/           # 任务进度页
│   │   │   ├── ProfileReport/          # 画像报告页
│   │   │   ├── TagSelection/           # 标签筛选页
│   │   │   └── FragranceRecommend/     # 香调推荐页（Part2）
│   │   ├── services/                   # API 调用封装
│   │   │   ├── api.ts                  # Axios 实例
│   │   │   ├── analysisService.ts      # Part1 分析相关 API
│   │   │   ├── fragranceService.ts     # Part2 推荐相关 API
│   │   │   └── cookieService.ts        # Cookie 管理 API
│   │   ├── stores/                     # Zustand 状态管理
│   │   ├── types/                      # TypeScript 类型定义
│   │   │   ├── analysis.ts             # Part1 相关类型
│   │   │   ├── fragrance.ts            # Part2 相关类型
│   │   │   └── common.ts              # 公共类型
│   │   ├── hooks/                      # 自定义 Hooks
│   │   ├── utils/                      # 工具函数
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── router.tsx                  # 路由配置
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/                            # 后端项目 (FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI 入口
│   │   ├── config.py                   # 配置管理
│   │   ├── database.py                 # 数据库连接
│   │   │
│   │   ├── api/                        # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py           # v1 总路由
│   │   │   │   ├── analysis.py         # Part1: 分析任务 API
│   │   │   │   ├── fragrance.py        # Part2: 香调推荐 API
│   │   │   │   ├── cookies.py          # Cookie 管理 API
│   │   │   │   └── tasks.py            # 任务状态 API
│   │   │   └── deps.py                 # 依赖注入
│   │   │
│   │   ├── models/                     # SQLAlchemy 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py             # 分析任务模型
│   │   │   ├── blogger.py              # 博主数据模型
│   │   │   ├── profile.py              # 画像标签模型
│   │   │   ├── fragrance.py            # 香调推荐模型
│   │   │   └── cookie.py               # Cookie 模型
│   │   │
│   │   ├── schemas/                    # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py
│   │   │   ├── fragrance.py
│   │   │   ├── cookie.py
│   │   │   └── common.py
│   │   │
│   │   ├── services/                   # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── analysis_service.py     # 分析流程编排
│   │   │   ├── fragrance_service.py    # 香调推荐服务
│   │   │   └── cookie_service.py       # Cookie 管理服务
│   │   │
│   │   ├── core/                       # 核心模块
│   │   │   ├── __init__.py
│   │   │   ├── task_manager.py         # 异步任务管理器
│   │   │   ├── sse.py                  # SSE 事件推送
│   │   │   └── exceptions.py           # 自定义异常
│   │   │
│   │   ├── platforms/                  # 平台采集器（可扩展）
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # 平台基类（抽象接口）
│   │   │   ├── douyin/                 # 抖音采集器
│   │   │   │   ├── __init__.py
│   │   │   │   ├── collector.py        # 数据采集
│   │   │   │   ├── parser.py           # 数据解析
│   │   │   │   └── config.py           # 抖音特定配置
│   │   │   └── xiaohongshu/            # 小红书采集器（预留）
│   │   │       └── __init__.py
│   │   │
│   │   ├── analyzers/                  # 分析器（可插拔）
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # 分析器基类
│   │   │   ├── visual_analyzer.py      # 视觉分析（图片/视频帧）
│   │   │   ├── comment_analyzer.py     # 评论语义分析
│   │   │   ├── profile_aggregator.py   # 画像标签汇总
│   │   │   └── media_processor.py      # 图片/视频预处理
│   │   │
│   │   ├── ai/                         # AI 模型接入层（可插拔）
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # AI 提供者基类
│   │   │   ├── provider_glm.py         # 智谱 GLM
│   │   │   ├── provider_openai.py      # OpenAI
│   │   │   ├── provider_deepseek.py    # DeepSeek
│   │   │   └── registry.py             # 模型注册表
│   │   │
│   │   ├── fragrance/                  # 香调推荐引擎（Part2）
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # 推荐引擎基类
│   │   │   ├── iceberg_model.py        # 冰山理论模型（先 mock）
│   │   │   ├── prompt_templates.py     # Prompt 模板
│   │   │   └── chat.py                 # 对话管理
│   │   │
│   │   └── storage/                    # 文件存储层（可切换）
│   │       ├── __init__.py
│   │       ├── base.py                 # 存储基类
│   │       ├── local.py                # 本地文件存储
│   │       └── cloud.py                # 云存储（预留）
│   │
│   ├── alembic/                        # 数据库迁移
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── pyproject.toml                  # 项目配置
│   └── data/                           # 运行时数据目录
│       ├── db/                         # SQLite 数据库
│       ├── media/                      # 采集的媒体文件
│       │   └── {task_id}/              # 按任务 ID 分目录
│       │       ├── covers/
│       │       ├── videos/
│       │       ├── frames/
│       │       ├── fan_covers/
│       │       └── fan_grids/
│       └── cookies/                    # Cookie 文件
│
├── docker-compose.yml                  # Docker Compose 配置
├── others/                             # 历史实验代码（参考）
│   └── tx_agent/
└── .gitignore
```

---

## 四、API 规范

### 10.1 设计语言

- **主题**: 自然、匠人、带有高端调香实验室的温润质感 (Natural Artisan Ledger)
- **主色调**: 浅冷石灰/陶瓷背景 + 深苔藓绿/炭灰文字 + 琥珀色点缀
- **字体**: 使用 Google Fonts 的 Inter（英文）与优雅的衬线体（标题/强调），中文回退系统黑体/宋体
- **卡片**: 摒弃传统的厚重卡片与发光阴影，采用极细的实线边框 (1px) 和大面积留白，模拟纸质配方账本
- **动画**: 极简、克制，避免发光特效和复杂微动效，状态切换自然干脆
- **无 Emoji 规范**: 界面中**严禁使用自带的系统 Emoji**，以保证高度的专业感和高端杂志感。所有图标如果必须使用，仅采用极简的单色矢量图（如 Lucide-react）。
- **布局架构**: 高度定制化工作流场景。特别是在 Part 2 香调调配室，采用**沉浸式三栏布局**（参考资料坞 + 配方画布 + AI 助手），避免页面间的反复跳转和割裂感。

### 4.1 总体规范

- **基础路径**: `/api/v1/`
- **数据格式**: JSON
- **字符编码**: UTF-8
- **时间格式**: ISO 8601 (`2026-06-13T09:00:00+08:00`)
- **分页**: `?page=1&page_size=20`
- **错误响应**: 统一格式

**统一响应格式**:

```json
// 成功
{
  "code": 0,
  "message": "success",
  "data": { ... }
}

// 错误
{
  "code": 40001,
  "message": "Cookie 已过期，请重新上传",
  "data": null
}
```

**错误码规范**:

| 范围 | 类别 | 示例 |
|---|---|---|
| 40000-40099 | 参数错误 | 40001 参数缺失, 40002 格式错误 |
| 40100-40199 | 认证错误 | 40101 Cookie 无效 |
| 40400-40499 | 资源不存在 | 40401 任务不存在 |
| 50000-50099 | 服务端错误 | 50001 采集失败, 50002 AI 调用失败 |

### 4.2 API 端点总览

#### Part1: 用户画像分析

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/v1/analysis/create` | 创建分析任务 |
| `GET` | `/api/v1/analysis/{task_id}` | 获取分析任务详情 |
| `GET` | `/api/v1/analysis/{task_id}/progress` | SSE 进度推送 |
| `GET` | `/api/v1/analysis/{task_id}/report` | 获取画像报告 |
| `GET` | `/api/v1/analysis/{task_id}/tags` | 获取标签数据（含比例） |
| `GET` | `/api/v1/analysis/list` | 获取分析任务列表（历史记录） |
| `DELETE` | `/api/v1/analysis/{task_id}` | 删除分析任务 |

#### Part2: 香调推荐

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/v1/fragrance/generate` | 提交标签生成推荐方案 |
| `GET` | `/api/v1/fragrance/{session_id}` | 获取推荐结果 |
| `POST` | `/api/v1/fragrance/{session_id}/chat` | 追问对话（采用 SSE 流式输出） |
| `POST` | `/api/v1/fragrance/{session_id}/regenerate` | 重新生成方案 |
| `GET` | `/api/v1/fragrance/{session_id}/history` | 获取对话历史 |

#### Cookie 管理

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/v1/cookies/upload` | 上传 Cookie 文件 |
| `GET` | `/api/v1/cookies/status` | 查询 Cookie 有效性 |
| `DELETE` | `/api/v1/cookies/{platform}` | 删除指定平台 Cookie |

#### 系统配置

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/config/analysis-levels` | 获取分析等级配置 |
| `GET` | `/api/v1/config/ai-providers` | 获取可用 AI 模型列表 |
| `PUT` | `/api/v1/config/ai-providers` | 更新 AI 模型配置 |

---

## 五、数据模型

### 5.1 核心实体关系

```
AnalysisTask (分析任务)
├── 1:1 → BloggerProfile (博主资料)
├── 1:N → BloggerPost (博主帖子)
├── 1:N → Comment (评论)
├── 1:N → CommenterProfile (评论者资料)
├── 1:1 → ProfileReport (画像报告 - 四维度标签)
└── 1:N → FragranceSession (香调推荐会话)
       └── 1:N → ChatMessage (对话消息)
```

### 5.2 AnalysisTask (分析任务)

```python
class AnalysisTask:
    id: str                     # UUID
    user_id: str | None         # 预留用户 ID（第一版 NULL）
    platform: str               # 平台: "douyin" | "xiaohongshu" | "weibo"
    blogger_url: str            # 博主链接
    analysis_level: str         # 分析等级: "quick" | "standard" | "deep" | "custom"
    custom_config: dict | None  # 高级自定义配置（JSON）
    status: str                 # "pending" | "collecting" | "analyzing" | "completed" | "failed"
    progress: int               # 进度百分比 0-100
    current_step: str           # 当前步骤描述
    error_message: str | None   # 错误信息
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
```

### 5.3 BloggerProfile (博主资料)

```python
class BloggerProfile:
    id: str                     # UUID
    task_id: str                # 关联 AnalysisTask
    platform_uid: str           # 平台用户 ID（如 sec_uid）
    nickname: str
    gender: str | None
    age: str | None
    province: str | None
    city: str | None
    signature: str | None
    follower_count: int | None
    following_count: int | None
    total_favorited: int | None
    aweme_count: int | None
    avatar_url: str | None
    raw_data: dict              # 原始 API 返回数据
```

### 5.4 ProfileReport (画像报告)

```python
class ProfileReport:
    id: str                     # UUID
    task_id: str                # 关联 AnalysisTask
    
    # 四维度标签数据（JSON）
    climate_consumption: dict   # 气候-消费带
    # 结构: {
    #   "climate_zone": {"湿热南方": 42, "干燥北方": 28, "四季分明": 30},
    #   "city_tier": {"一线/新一线": 35, "二线": 40, "三线及以下": 25},
    #   "culture_circle": {...},
    #   "concentration": "全国分散型",
    #   "summary": "..."
    # }
    
    fragrance_consumption: dict # 香氛消费推断
    # 结构: {
    #   "price_tier": {"日常平价": 31, "轻奢入门": 31, ...},
    #   "purchase_motivation": {...},
    #   "decision_path": {...},
    #   "consumption_frequency": {...},
    #   "summary": "..."
    # }
    
    fashion_fragrance_map: dict # 穿搭风格-香调映射
    # 结构: {
    #   "fashion_style": {"甜美系": 35, "古典系": 25, ...},
    #   "fashion_scene": {...},
    #   "color_preference": {...},
    #   "fashion_completeness": {...},
    #   "summary": "..."
    # }
    
    lifestyle_scenario: dict    # 生活方式-用香场景
    # 结构: {
    #   "core_interest": {"亚文化穿搭": 23, "日常自拍": 28, ...},
    #   "social_activity": {...},
    #   "aesthetic_personality": {...},
    #   "fragrance_timing": {...},
    #   "content_consumption": {...},
    #   "summary": "..."
    # }
    
    overall_summary: str        # 综合画像总结（3-5句话）
    full_report_markdown: str   # 完整文字报告（Markdown）
    
    created_at: datetime
```

### 5.5 FragranceSession (香调推荐会话)

```python
class FragranceSession:
    id: str                     # UUID
    task_id: str                # 关联 AnalysisTask
    user_id: str | None         # 预留
    selected_tags: dict         # 调香师筛选后的标签
    
    # 推荐结果
    recommendations: list[dict] # 多套推荐方案
    # 结构: [
    #   {
    #     "plan_id": "plan_1",
    #     "name": "花果调",
    #     "category": "花果香",
    #     "top_notes": [{"name": "佛手柑", "reason": "..."}, ...],
    #     "middle_notes": [{"name": "鸢尾花", "reason": "..."}, ...],
    #     "base_notes": [{"name": "白檀", "reason": "..."}, ...],
    #     "recommendation_reason": "详细推荐原因...",
    #     "fragrance_story": "创作灵感故事...",
    #     "iceberg_analysis": {
    #       "surface": "显性行为层分析...",
    #       "middle": "情感/价值层分析...",
    #       "deep": "潜意识/内在需求分析..."
    #     }
    #   },
    #   ...
    # ]
    
    status: str                 # "generating" | "completed" | "error"
    created_at: datetime
    updated_at: datetime


class ChatMessage:
    id: str                     # UUID
    session_id: str             # 关联 FragranceSession
    role: str                   # "user" | "assistant"
    content: str                # 消息内容
    updated_plans: list[dict] | None  # 如果 AI 回复修改了方案，包含更新后的方案
    created_at: datetime
```

### 5.6 PlatformCookie (平台 Cookie)

```python
class PlatformCookie:
    id: str                     # UUID
    platform: str               # "douyin" | "xiaohongshu" | "taobao"
    cookie_data: dict           # Cookie JSON 数据
    is_valid: bool              # 是否有效
    last_checked_at: datetime | None
    uploaded_at: datetime
    expires_at: datetime | None
```

---

## 六、分析配置系统

### 6.1 预设等级

```python
ANALYSIS_LEVELS = {
    "quick": {
        "name": "快速分析",
        "description": "快速了解博主及粉丝大致画像",
        "estimated_time": "3-5分钟",
        "config": {
            "post_selection": {
                "top_count": 3,
                "recent_count": 0,
                "sort_by": "likes"
            },
            "comment": {
                "per_post_count": 10,
                "sort_by": "hot"
            },
            "commenter_analysis": {
                "enabled": True,
                "max_count": 30,
                "analyze_posts": False,
                "posts_per_commenter": 0,
                "analyze_post_content": False,
                "analyze_video": False
            },
            "sub_comment": {
                "enabled": False,
                "count": 0
            },
            "visual_analysis": {
                "cover_analysis": True,
                "video_frame_analysis": False,
                "fan_cover_mode": "skip",  # skip | grid | individual
                "grid_size": 10
            }
        }
    },
    "standard": {
        "name": "标准分析",
        "description": "全面分析博主及粉丝画像",
        "estimated_time": "8-15分钟",
        "config": {
            "post_selection": {
                "top_count": 3,
                "recent_count": 3,
                "sort_by": "likes"
            },
            "comment": {
                "per_post_count": 20,
                "sort_by": "hot"
            },
            "commenter_analysis": {
                "enabled": True,
                "max_count": 0,  # 0 = 全部
                "analyze_posts": True,
                "posts_per_commenter": 3,
                "analyze_post_content": False,
                "analyze_video": False
            },
            "sub_comment": {
                "enabled": False,
                "count": 0
            },
            "visual_analysis": {
                "cover_analysis": True,
                "video_frame_analysis": True,
                "frames_per_video": 5,
                "analyze_frames_count": 3,
                "fan_cover_mode": "grid",
                "grid_size": 10
            }
        }
    },
    "deep": {
        "name": "深度分析",
        "description": "最详细的画像分析，逐一精细分析",
        "estimated_time": "20-40分钟",
        "config": {
            "post_selection": {
                "top_count": 5,
                "recent_count": 5,
                "sort_by": "likes"
            },
            "comment": {
                "per_post_count": 50,
                "sort_by": "hot"
            },
            "commenter_analysis": {
                "enabled": True,
                "max_count": 0,
                "analyze_posts": True,
                "posts_per_commenter": 5,
                "analyze_post_content": True,
                "analyze_video": True
            },
            "sub_comment": {
                "enabled": True,
                "count": 10
            },
            "visual_analysis": {
                "cover_analysis": True,
                "video_frame_analysis": True,
                "frames_per_video": 5,
                "analyze_frames_count": 5,
                "fan_cover_mode": "individual",
                "grid_size": 10
            }
        }
    }
}
```

### 6.2 配置参数说明

> [!NOTE]
> **v1 版本已确认：仅提供“快速/标准/深度”三个固定的预设等级**，前端不开放复杂的高级自定义表单，按预设参数跑即可。
> 后续版本若需要高级模式，可参考下表的参数结构进行扩展。

| 类别 | 参数 | 说明 | 待讨论 |
|---|---|---|---|
| **帖子选择** | `top_count` | 按热度选取的帖子数量 | |
| | `recent_count` | 按时间选取的最近帖子数量 | |
| | `sort_by` | 排序方式：likes / comments / shares | |
| **评论采集** | `per_post_count` | 每个帖子采集的评论数量 | |
| | `sort_by` | 评论排序：hot / time | |
| **评论者分析** | `max_count` | 最多分析多少个评论者（0=全部） | |
| | `analyze_posts` | 是否采集评论者的帖子 | |
| | `posts_per_commenter` | 每个评论者采集的帖子数 | |
| | `analyze_post_content` | 是否详细分析评论者帖子内容 | |
| | `analyze_video` | 是否分析评论者的视频 | |
| **子评论** | `enabled` | 是否采集评论下的回复 | v1暂不采集（保留扩展字段） |
| | `count` | 每条评论采集多少条回复 | |
| **视觉分析** | `cover_analysis` | 是否分析封面图 | |
| | `video_frame_analysis` | 是否提取视频帧分析 | |
| | `frames_per_video` | 每个视频提取的帧数 | |
| | `analyze_frames_count` | 每个视频分析的帧数 | |
| | `fan_cover_mode` | 粉丝封面分析模式：skip/grid/individual | ⚠️ 组图精度问题 |
| | `grid_size` | 组图模式下每张组图包含的图片数 | |

---

## 七、AI 模型可插拔架构

### 7.1 模型槽位

系统中需要调用 AI 的环节及其独立配置：

| 槽位 ID | 用途 | 需要的能力 | 默认模型 |
|---|---|---|---|
| `visual_analysis` | 分析封面图/视频帧/组图 | 多模态（图片理解） | GLM-4V |
| `comment_analysis` | 评论语义分析（情感、关键词） | 纯文本 | GLM-4 |
| `tag_aggregation` | 汇总多维度分析结果→生成标签报告 | 纯文本（长上下文） | GLM-4 |
| `fragrance_reasoning` | 标签→香调推荐+推荐原因+故事 | 纯文本（创意生成） | GLM-4 |
| `fragrance_chat` | 对话追问/微调方案 | 纯文本（对话） | GLM-4 |

### 7.2 Provider 接口

```python
class AIProvider(ABC):
    """AI 模型提供者基类"""
    
    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """文本对话"""
        ...
    
    @abstractmethod
    async def vision(self, image_paths: list[str], prompt: str, **kwargs) -> str:
        """图片理解"""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        ...
    
    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """是否支持视觉能力"""
        ...
```

### 7.3 配置方式

通过环境变量或配置文件设置：

```python
# .env 或 config.yaml
AI_PROVIDERS = {
    "glm": {
        "api_key": "xxx",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "models": {
            "chat": "glm-4",
            "vision": "glm-4v"
        }
    },
    "openai": {
        "api_key": "xxx",
        "base_url": "https://api.openai.com/v1/",
        "models": {
            "chat": "gpt-4o",
            "vision": "gpt-4o"
        }
    }
}

# 槽位绑定
AI_SLOT_BINDINGS = {
    "visual_analysis": {"provider": "glm", "model": "vision"},
    "comment_analysis": {"provider": "glm", "model": "chat"},
    "tag_aggregation": {"provider": "glm", "model": "chat"},
    "fragrance_reasoning": {"provider": "glm", "model": "chat"},
    "fragrance_chat": {"provider": "glm", "model": "chat"}
}
```

---

## 八、SSE 进度推送协议

### 8.1 事件格式

```
event: progress
data: {
  "task_id": "xxx",
  "status": "collecting",
  "progress": 25,
  "current_step": "正在采集博主帖子列表",
  "sub_steps": [
    {"name": "博主资料", "status": "completed"},
    {"name": "帖子列表", "status": "running"},
    {"name": "封面图下载", "status": "pending"},
    {"name": "评论采集", "status": "pending"},
    {"name": "评论者分析", "status": "pending"},
    {"name": "视觉分析", "status": "pending"},
    {"name": "标签生成", "status": "pending"}
  ]
}
```

### 8.2 事件类型

| 事件名 | 触发时机 | data 内容 |
|---|---|---|
| `progress` | 每个步骤状态变更 | 任务状态 + 进度 + 步骤详情 |
| `step_complete` | 某个子步骤完成 | 步骤名 + 步骤结果摘要 |
| `error` | 出错 | 错误信息 |
| `complete` | 全部完成 | 报告 ID |

---

## 九、文件存储规范

### 9.1 存储接口

```python
class StorageProvider(ABC):
    """文件存储提供者基类"""
    
    @abstractmethod
    async def save(self, file_path: str, data: bytes) -> str:
        """保存文件，返回可访问的 URL 或路径"""
        ...
    
    @abstractmethod
    async def get(self, file_path: str) -> bytes:
        """获取文件内容"""
        ...
    
    @abstractmethod
    async def delete(self, file_path: str) -> None:
        """删除文件"""
        ...
    
    @abstractmethod
    def get_url(self, file_path: str) -> str:
        """获取文件的可访问 URL"""
        ...
```

### 9.2 本地存储路径规范

```
backend/data/media/{task_id}/
├── blogger/
│   ├── covers/              # 博主帖子封面图
│   │   ├── post_1.jpg
│   │   └── post_1_processed.jpg
│   ├── videos/              # 博主帖子视频
│   │   └── post_1.mp4
│   └── frames/              # 视频关键帧
│       ├── post_1_frame_01.jpg
│       └── post_1_frame_02.jpg
├── fans/
│   ├── covers/              # 粉丝封面图
│   │   ├── user_xxx_1.jpg
│   │   └── user_xxx_1_processed.jpg
│   └── grids/               # 组图
│       ├── grid_01.jpg
│       └── grid_02.jpg
└── analysis/
    ├── blogger_profile.json  # 博主原始数据
    ├── posts.json            # 帖子列表
    ├── comments.json         # 评论数据
    ├── commenter_profiles.json  # 评论者数据
    ├── visual_analysis.json  # 视觉分析结果
    ├── comment_analysis.json # 评论分析结果
    └── report.json           # 最终报告数据
```

---

## 十、平台采集器可扩展架构

### 10.1 采集器接口

```python
class PlatformCollector(ABC):
    """平台数据采集器基类"""
    
    @abstractmethod
    async def get_blogger_profile(self, url: str) -> dict:
        """获取博主资料"""
        ...
    
    @abstractmethod
    async def get_blogger_posts(self, uid: str, count: int) -> list[dict]:
        """获取博主帖子列表"""
        ...
    
    @abstractmethod
    async def get_post_comments(self, post_id: str, count: int) -> list[dict]:
        """获取帖子评论"""
        ...
    
    @abstractmethod
    async def get_user_profile(self, uid: str) -> dict:
        """获取用户资料（评论者）"""
        ...
    
    @abstractmethod
    async def download_media(self, url: str, save_path: str) -> bool:
        """下载媒体文件（图片/视频）"""
        ...
    
    @abstractmethod
    def parse_url(self, url: str) -> dict:
        """解析平台 URL，提取用户 ID 等信息"""
        ...
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        ...
```

### 10.2 平台注册

```python
# platforms/__init__.py
PLATFORM_REGISTRY = {
    "douyin": DouyinCollector,
    # "xiaohongshu": XiaohongshuCollector,  # 后续扩展
    # "weibo": WeiboCollector,              # 后续扩展
}

def get_collector(platform: str) -> PlatformCollector:
    if platform not in PLATFORM_REGISTRY:
        raise ValueError(f"不支持的平台: {platform}")
    return PLATFORM_REGISTRY[platform]()
```

---

## 十一、环境变量与配置

### 11.1 `.env` 文件

```bash
# ===== 基础配置 =====
APP_NAME=AromotionAI
APP_ENV=development  # development | production
DEBUG=true
SECRET_KEY=your-secret-key

# ===== 数据库 =====
DATABASE_URL=sqlite:///./data/db/aromotion.db
# 生产环境: DATABASE_URL=postgresql://user:pass@localhost:5432/aromotion

# ===== 文件存储 =====
STORAGE_TYPE=local  # local | s3 | oss
STORAGE_LOCAL_PATH=./data/media

# ===== AI 模型 =====
GLM_API_KEY=your-glm-api-key
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# ===== 跨域 =====
CORS_ORIGINS=http://localhost:5173

# ===== Cookie 文件路径（后端配置通道）=====
DOUYIN_COOKIE_PATH=./data/cookies/douyin.json
TAOBAO_COOKIE_PATH=./data/cookies/taobao.json
```

---

## 十二、部署方案

### 12.1 本地开发

```bash
# 后端
cd backend
uv venv
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev  # → http://localhost:5173
```

### 12.2 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:///./data/db/aromotion.db

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - VITE_API_BASE_URL=http://backend:8000

  # 生产环境加 PostgreSQL
  # db:
  #   image: postgres:15
  #   environment:
  #     POSTGRES_DB: aromotion
  #     POSTGRES_USER: aromotion
  #     POSTGRES_PASSWORD: secret
  #   volumes:
  #     - pgdata:/var/lib/postgresql/data
```

---

## 十三、开发规范

### 13.1 Git 规范

**分支策略**:
- `main` — 稳定版本
- `develop` — 开发分支
- `feature/xxx` — 功能分支
- `fix/xxx` — 修复分支

**Commit 格式**:
```
feat(part1): 完成博主帖子采集功能
fix(part2): 修复对话上下文丢失问题
docs: 更新 API 文档
```

### 13.2 后端编码规范

- 使用 `ruff` 进行代码格式化和 lint
- 函数/方法命名使用 `snake_case`
- 类命名使用 `PascalCase`
- 所有 API 函数需要添加 docstring
- 异步函数统一使用 `async/await`

### 13.3 前端编码规范

- 使用 ESLint + Prettier
- 组件使用函数式组件 + Hooks
- 组件文件使用 `PascalCase`
- 工具函数文件使用 `camelCase`
- 类型定义使用 `interface` 优先
- 每个组件目录包含 `index.tsx` + `style.css`（如需要）

---

## 十四、待进一步讨论的问题

> [!WARNING]
> 以下问题需要在开发过程中逐步细化和确认。

| # | 问题 | 所在文档 | 优先级/状态 |
|---|---|---|---|
| - | ~~分析配置的高级自定义参数~~ | 全局 | ✅已确认：v1 仅使用预设等级 |
| - | ~~子评论 API 可行性~~ | Part1 | ✅已确认：v1 不抓子评论，仅预留字段 |
| - | ~~Part2 对话流式输出~~ | Part2 | ✅已确认：采用 SSE 流式输出 |
| 2 | 组图分析 vs 单图分析的精度对比与策略 | Part1 后端 | 中 |
| 4 | 冰山理论的具体分层映射规则 | Part2 后端 | 低（先 mock） |
| 5 | 冰山理论的探索方向建议 | Part2 后端 | 低 |
| 7 | 多博主对比功能的数据结构设计 | 全局 | 低（预留） |
| 8 | 是否需要支持调香师自定义标签（不在预设体系内） | Part1 前端 | 中 |
