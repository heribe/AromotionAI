# AromotionAI - Development Progress

## Overall Milestones
- [x] Milestone E2E: E2E Testing Suite (DONE)
- [x] Milestone 1: Infrastructure & Cookie Mgmt (DONE)
- [x] Milestone 2: Data Collection & Media Proc (DONE)
- [x] Milestone 3: AI Analyzers & Profile Agg (DONE)
  - [x] M3.1: AI Registry (DONE, tests passed)
  - [x] M3.2: Visual & Comment Analyzers (DONE, tests passed)
  - [x] M3.3: Profile Aggregator (DONE, tests passed)
  - [x] M3.4: Tests & Integration (DONE, 由 test_analyzers.py 覆盖)
- [x] Milestone 4: Task Manager & SSE API (DONE)
  - [x] M4.1: TaskManager (Memory-based) (DONE, tests passed)
  - [x] M4.2: AnalysisService (Pipeline Orchestration) (DONE)
  - [x] M4.3: Analysis REST + SSE API (DONE, 23 tests passed)
  - [x] M4.4: Report/Tags/Delete endpoints (DONE)
- [x] Milestone 5: Fragrance Recommend Engine (DONE)
  - [x] M5.1: FragranceEngine ABC + PromptFragranceEngine (DONE, 20 service tests passed)
  - [x] M5.2: FragranceService 业务编排 (DONE)
  - [x] M5.3: Fragrance REST API 5 端点 (DONE, 15 API tests passed)
- [x] Milestone 6: Integration & Final Gate (DONE)
  - [x] M6.1: e2e 基础设施改造（stub→真实 app，httpx 兼容性修复）(DONE)
  - [x] M6.2: F1 Cookies e2e 改造 (DONE, 9 用例全绿)
  - [x] M6.3: F2/F3 Analysis e2e 改造 (DONE, 20 用例全绿)
  - [x] M6.4: F4 Reports/Tags/Delete e2e 改造 (DONE, 10 用例全绿)
  - [x] M6.5: F5/F6 Fragrance e2e 改造 (DONE, 19 用例全绿)
  - [x] M6.6: Tier3/Tier4 复杂场景 e2e 改造 + F7 skip (DONE, 7 用例全绿 + 10 skip)
  - [x] M6.7: 对抗性测试加固 M5 边界 (DONE, 新增 9 用例)

## Detailed Status
### Milestone 5: Fragrance Recommend Engine
- **M5.1: FragranceEngine ABC + PromptFragranceEngine**
  - **实现**: `backend/app/engines/` 中的 `base.py`（FragranceEngine ABC）、`prompt_engine.py`（基于 Prompt 工程的第一版引擎，冰山三层分析 + 香调推荐 + 对话微调）、`__init__.py`（引擎注册表与工厂）。内联常量 `PROMPT_VERSION="v1"`、温度（generate 0.8 / chat 0.6）、`MAX_HISTORY_MESSAGES=20`。
  - **后续接入**: Dify / LocalAgent 的接入路径见 `docs/03-part2-backend.md` §6.1 与设计文档 §7。
  - **状态**: 已完成。
- **M5.2: FragranceService 业务编排**
  - **实现**: `backend/app/services/fragrance_service.py`。封装 generate / chat / regenerate / get_session / get_history 五个业务方法。含权重归一化、互斥组标签校验、JSON 解析重试（1 次）、聊天历史滑窗、updated_plans 按 plan_id 合并。
  - **异常类**: SessionNotFoundError (404) / SessionStateError (400) / TaskNotCompletedError (400) / TagsValidationError (422) / FragranceEngineError (502)。
  - **状态**: 已完成。
- **M5.3: Fragrance REST API**
  - **实现**: `backend/app/api/v1/fragrance.py` 实现 §2.1-2.5 全部接口：POST /generate、POST /{session_id}/chat、POST /{session_id}/regenerate、GET /{session_id}、GET /{session_id}/history。配套 `schemas/fragrance.py`。
  - **测试**: `backend/tests/test_fragrance_service.py`（20 用例）+ `backend/tests/test_fragrance_api.py`（15 用例），共 35 用例全部通过。
  - **状态**: 已完成。
### Milestone 3: AI Analyzers & Profile Agg
- **M3.1: AI Registry**
  - **实现**: `backend/app/ai/` 中的基类、GLM、OpenAI、DeepSeek 适配器以及注册表与槽位绑定。
  - **测试**: `backend/tests/test_ai_providers.py`，全部 9 个用例通过。
  - **状态**: 已完成。
- **M3.2: Visual & Comment Analyzers**
  - **实现**: `backend/app/analyzers/` 中的 `base.py`, `visual_analyzer.py`, `comment_analyzer.py` 以及其导入包配置。
  - **测试**: `backend/tests/test_analyzers.py` 中的 `TestBaseAnalyzer`, `TestVisualAnalyzer`, `TestCommentAnalyzer`，全部通过。
  - **状态**: 已完成。
- **M3.3: Profile Aggregator**
  - **实现**: `backend/app/analyzers/profile_aggregator.py` 粉丝画像多维度规则与 AI 聚合生成。
  - **测试**: `backend/tests/test_analyzers.py` 中的 `TestProfileAggregator`，包含正常生成、降级与容错、兼容性测试，全部通过。
  - **状态**: 已完成。

### Milestone 4: Task Manager & SSE API
- **M4.1: TaskManager (Memory-based)**
  - **实现**: `backend/app/core/task_manager.py` (TaskManager 以及全局单例 task_manager) 和 `backend/app/api/deps.py` 依赖注入。
  - **测试**: `backend/tests/test_task_manager.py`，包含基础发布订阅、任务取消安全、多订阅者并发、对称清理校验、异常状态等。
  - **状态**: 已完成，测试通过。
- **M4.2: AnalysisService (Pipeline Orchestration)**
  - **实现**: `backend/app/services/analysis_service.py` 核心管道编排，注入与导出。
  - **测试**: `backend/tests/test_analysis_service.py`，包含全链路 Mock 管道运行断言，以及步骤异常回滚断言。
  - **状态**: 已完成，全部 9 个测试 (test_task_manager + test_analysis_service) 通过。
- **M4.3: Analysis REST + SSE API**
  - **实现**: `backend/app/api/v1/analysis.py` 实现 §2.1-2.7 全部接口：POST /create、GET /{task_id}、GET /list、GET /{task_id}/progress (SSE)、POST /{task_id}/cancel、GET /{task_id}/report、GET /{task_id}/tags、DELETE /{task_id}。配套 `schemas/analysis.py` 与 `services/task_service.py`。
  - **测试**: `backend/tests/test_analysis_api.py`，覆盖创建/详情/列表/取消/报告/标签/删除/SSE 流共 23 用例。
  - **状态**: 已完成。
- **M4.4: Report/Tags/Delete endpoints**
  - **实现**: 与 M4.3 一并交付；DELETE 任务时清理 covers/avatars/grids 媒体；tags 端点按 §9.2 处理互斥标签组。
  - **状态**: 已完成。

## M6 e2e 改造决策记录（2026-06-14）

### 背景
原 `tests/e2e/conftest.py` 是一个 930 行的**独立 stub FastAPI app**（内存字典模拟全部端点），
82 个 e2e 用例验证的是"stub 是否符合契约"，**完全不接触真实 `app/` 包**。M6 将其改造为真实
app 集成测试。

### 改造策略
- `client` fixture 改用 `httpx.ASGITransport(app=app)` 挂载真实 `app.main:app`（同时修复
  httpx 兼容性问题：旧版 `httpx.AsyncClient(app=app)` 已废弃）
- `AROMOTION_TEST_MODE=mock` 让 collector/media/analyzer/AI 全走离线分支，
  真实 `AnalysisService.run_analysis` 可在测试环境离线跑完到 completed
- 通过 `dependency_overrides` 注入 `MockFragranceEngine`，业务逻辑照常跑
- helper（`_seed_completed_task_with_report` / `MockFragranceEngine` / `_parse_sse_events` 等）
  统一提炼到 `tests/e2e/conftest.py`

### 范围决策
1. **F7 config 端点族（11 用例）从 M6 剥离**：真实 app 无 `/api/v1/config/*` 路由模块，
   标记为待实现，暂跳过。
2. **删除语义不成立的用例**（与真实架构设计冲突）：
   - 运行中删 cookie/task 期望触发失败（真实禁止删运行中任务、pipeline 不中途检查 cookie）
   - chat SSE 流式（真实无此能力）
3. **文案断言对齐真实实现**（不改 production 代码）

### 删除/降级用例清单（M6 完成汇总）
共删除 6 个用例（语义与真实架构冲突）、skip 10 个（config 端点族待实现）：
- `test_f1_expired_cookie_detection` —— 删除（依赖 stub 状态 + 不存在的 validate 端点）
- `test_f6_chat_streaming_response` —— 删除（真实 chat 无 SSE 流式分支）
- `test_t3_cookie_deletion_mid_task` —— 删除（真实 pipeline 不中途检查 cookie）
- `test_t3_task_deletion_impact_on_sse` —— 删除（真实禁止删运行中任务）
- `test_t3_ai_config_updates_modifying_model_targets` —— 删除（config 端点缺失 + 读 stub 状态）
- `test_scenario_2_cookie_lifecycle` —— 删除（运行中删 cookie 假设不成立）
- `test_scenario_5_admin_model_swapping` —— 删除（config 端点缺失 + 读 stub 状态）
- `test_f7_config.py` 全 10 用例 —— pytestmark skip（待实现 config 模块）

文案断言对齐真实实现（不删除用例，仅改断言）：
- `test_f6_regenerate_session` / `test_t3_chat_history_updates_on_recalculations`：
  "重新选择" → "生成"（真实 INITIAL_ASSISTANT_MESSAGE 文案）
- `test_f4_report_markdown_generation`：放宽为 ## 开头 + seed 内容
- `test_f5_generate_empty_tags`：400 → 422（真实 TagsValidationError）
- `test_f6_chat_empty_message`：传空串期望 422（真实 Pydantic min_length）

## 测试基线（M6 收尾）
- **整体结果：229 passed, 11 skipped, 0 failed**
- 单元测试：164 passed（含 M5 对抗新增 9 个）+ 1 skipped（douyin collector 待人工）
- e2e 测试：65 passed + 10 skipped（F7 config 待实现）
- e2e 已真正打真实 `app/`（不再依赖 stub），通过 `AROMOTION_TEST_MODE=mock` +
  `dependency_overrides` 注入 MockFragranceEngine 隔离外部依赖

## Known Pre-existing Test Failures

### ⚠️ 待人工测试（已标记 @pytest.mark.skip）
- `tests/test_douyin_collector.py::test_collect_comments`
  - **原因**：Playwright mock 链路与实际 collector 代码已漂移，fallback 到 curl_cffi 时会发起**真实抖音 API 请求**。
  - **如何验证**：(1) 重写 mock 以匹配当前 `collect_comments` 的实际调用链；或 (2) 在拥有有效抖音 Cookie + 网络访问的环境下手动运行。
  - **优先级**：M5/M6 阶段统一处理真实网络集成测试时一并修复。

### 🔲 未来规划：config 系统配置模块（10 用例 skip）

> 产品规划详见 `docs/00-global-dev-guide.md` §十四 规划项 #9。

- `tests/e2e/test_f7_config.py` 全部 10 用例已 `pytestmark skip`
- **本质**：文档 §4.2 规划的 3 个端点（`GET /config/analysis-levels`、`GET/PUT /config/ai-providers`）从未实现，目的是把硬编码的分析等级预设（`DEFAULT_CONFIGS`）和 AI 槽位绑定（`AI_SLOT_BINDINGS`）提升为运行时可查询/可修改的 HTTP 接口
- **触发条件**：需要管理后台 / A/B 测试不同模型 / 运行时调整档位（任一满足）
- **如何解除 skip**：新建 `app/api/v1/config.py` 实现 3 个端点并注册到 router，删除 `test_f7_config.py` 顶部的 `pytestmark` 行

## L1/L3 端到端验证（2026-06-14，独立于 M6）

在 M6 e2e 改造之外，额外对后端做了分层端到端验证（L1 骨架 + L3 含 AI 主流程），发现并修复了
**6 个单测盲区问题**——单测与 e2e 全绿，但真实 AI 链路一跑就炸。

### 验证结果
- **L1 骨架**：服务启动 / 自动建表(9 表) / 17 路由注册 / `/health` / `/docs` /
  `cookies/status` / `analysis/list` 全部 200，零报错。
- **L3 含 AI 主流程**：`FragranceService.generate` 真实调用 GLM（Coding Plan, glm-5.2），
  成功生成 2 套香调推荐方案（冰山三层分析 + 前/中/后调香材 + 推荐理由 + 创作故事），
  session 与初始 assistant 消息持久化，`STATUS=completed`。

### 发现并修复的问题（均为单测盲区）
| # | 现象 | 根因 | 修复 | 文件 |
|---|------|------|------|------|
| 1 | provider 读不到 key | config 未把 `.env` 注入 `os.environ` | 加 `load_dotenv(_ENV_FILE)` | app/config.py |
| 2 | 429（套餐不匹配） | 默认 `/paas/v4`+glm-4，实际为 Coding Plan | `.env` 设 `ZHIPUAI_BASE_URL`；registry 默认改 glm-5.2 | .env / app/ai/registry.py |
| 3 | `NameError: os` | registry 改读 env 后漏 import | 补 `import os` | app/ai/registry.py |
| 4 | `KeyError`（prompt 构造炸） | ICEBERG 模板内 JSON 花括号被 `.format()` 误解析为占位符 | 改用 `str.replace` 插值 | app/engines/prompt_engine.py |
| 5 | 429（model 错） | engine 未把 slot model 传给 `provider.chat`，默认 glm-4 被 coding 拒 | engine 传 `model=` 给 provider.chat | app/engines/prompt_engine.py |
| 6 | `ReadTimeout` | 非流式 + timeout 60s，thinking 长生成超时 | provider 改流式 `_stream_completion`（`stream=True` 累积 content） | app/ai/provider_glm.py |

**核心教训**：M5 单测 mock 了 engine/provider，M6 e2e 虽打真实 app 但用 `MockFragranceEngine` +
`AROMOTION_TEST_MODE=mock` 隔离了真实 AI——两条测试链路都没触及真实 GLM 调用，故 #1/#4/#5/#6
（key 加载、prompt 构造、model 传参、网络超时）只能靠手工端到端验证才暴露。

### 附带配置变更
- `MAX_TOKENS_GENERATE` / `MAX_TOKENS_CHAT`：4096 → **65536**（给 thinking + 长输出留余量）。
- registry 模型默认值改为可配置：`GLM_MODEL` / `GLM_VISION_MODEL` 环境变量，未配置时默认 glm-5.2。
- 同步更新 `tests/test_ai_providers.py::test_default_slot_bindings` 的默认 model 断言为 glm-5.2。

### 遗留
- 前端可见的 SSE 流式输出：当前 provider 流式为内部累积（`chat` 仍返回完整 str），
  若需前端实时显示生成过程，需 provider 暴露 `chat_stream` + engine/service/API 全链路透传
  （`prompt_engine.py` 顶部注释已规划）。

## L4 端到端验证（2026-06-14~15，完整业务闭环）

在 L1/L3 基础上，对完整「采集→分析→聚合→推荐」业务闭环做了真实端到端验证
（真实抖音数据 + 真实 AI），又发现并修复了 4 个单测盲区问题。至此完整业务链路
第一次真实跑通。

### 验证结果（真实抖音博主，端到端）
- **采集**：curl_cffi 拿 profile（29.9 万粉）+ 23 posts；playwright 拿评论（含真实
  `ip_label` IP 属地）。
- **分析**：glm-4.6v 视觉（封面 + 评论者头像网格）+ glm-5.2 评论语义。
- **聚合**：ProfileReport 4 维度（地域基于真实 ip_label，不再 random）。
- **推荐**：fragrance generate 生成 2 套香调方案（冰山分析 + 前/中/后调 + 理由）。
- **完整闭环**：采集 → 分析 → 聚合 → 香调推荐，task 流转 `completed/100`。

### 发现并修复的问题（均为单测盲区，续编号 7-10）
| # | 现象 | 根因 | 修复 | 文件 |
|---|------|------|------|------|
| 7 | posts 永远空（0 条） | AnalysisService 给 `get_blogger_posts` 传了数字 uid，但该接口的抖音 API 要 sec_user_id | 从 profile 响应 `raw_data.user.sec_uid` 取 sec_user_id 传入 | app/services/analysis_service.py |
| 8 | task 永远卡 `collecting/5` | `run_analysis` 经 `task_manager.submit` 后台异步执行，却复用 create 请求级 session（请求结束 `get_db` 即 close） | `run_analysis` 开头创建独立 `SessionLocal` + `finally` 关闭 | app/services/analysis_service.py |
| 9 | 视觉段全空 fallback（误判"通过"） | glm-5.2 纯文本不支持 vision，被 `visual_analyzer` 的 `except→fallback` + parse 失败 fallback 双重掩盖；顺带 provider 流式错误处理调用不存在的 `_raise_for_status` | 视觉槽位改 glm-4.6v；provider 错误处理改为构造 `HTTPStatusError` | app/ai/registry.py / provider_glm.py |
| 10 | 粉丝地域是 random 假数据 | CommenterProfile 的 province/city/gender/age 用 random（抖音评论 API 不返回），而评论自带的 `ip_label` 没被利用 | province 用评论 `ip_label`（真实 IP 属地）；gender/age 留 None；`analyze_grid` prompt 动态描述行列与 `create_grid_image` 一致 | app/services/analysis_service.py / visual_analyzer.py |

### 附带
- 安装 playwright chromium 浏览器（评论采集主通道所需，~294MB）。
- cookie 灌 DB（`platform_cookies` 表），采集器走 DB 分支（完整业务链路必经）。
- `.gitignore` 加 `cookies.json`（保护敏感凭据）。
- 视觉槽位默认模型由 glm-5.2 更正为 **glm-4.6v**（覆盖 L1/L3 段 #2 的临时默认）。

### 结论
后端代码基本写完，且经此验证**真实可跑**。本次 session 累计修复 **10 个单测盲区问题**
（L1/L3 的 #1-6 + L4 的 #7-10），等于提前完成 M6 集成验证的主体工作。剩余 SSE 前端流式
为可选增强（见上节遗留）。
