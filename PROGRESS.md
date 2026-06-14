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
- [/] Milestone 6: Integration & Final Gate (IN_PROGRESS)
  - [x] M6.1: e2e 基础设施改造（stub→真实 app，httpx 兼容性修复）(DONE)
  - [x] M6.2: F1 Cookies e2e 改造 (DONE, 9 用例全绿)
  - [ ] M6.3: F2/F3 Analysis e2e 改造 (IN_PROGRESS)
  - [ ] M6.4: F4 Reports/Tags/Delete e2e 改造 (PLANNED)
  - [ ] M6.5: F5/F6 Fragrance e2e 改造 (PLANNED)
  - [ ] M6.6: Tier3/Tier4 复杂场景 e2e 改造 (PLANNED)
  - [ ] M6.7: 对抗性测试加固 + 收尾 (PLANNED)

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

### 删除/降级用例清单（M6 过程中逐步记录）
- `tests/e2e/test_f1_cookies.py::test_f1_expired_cookie_detection` —— 删除
  （依赖 stub 内部状态 + 不存在的 `/cookies/validate/{platform}` 端点；校验逻辑已由
  `tests/test_cookie_service.py` 覆盖）

## Known Pre-existing Test Failures
> 单元测试整体结果：**155 passed, 1 skipped, 0 failed**（M5 收尾基线）。

### ⚠️ 待人工测试（已标记 @pytest.mark.skip）
- `tests/test_douyin_collector.py::test_collect_comments`
  - **原因**：Playwright mock 链路与实际 collector 代码已漂移，fallback 到 curl_cffi 时会发起**真实抖音 API 请求**。
  - **如何验证**：(1) 重写 mock 以匹配当前 `collect_comments` 的实际调用链；或 (2) 在拥有有效抖音 Cookie + 网络访问的环境下手动运行。
  - **优先级**：M5/M6 阶段统一处理真实网络集成测试时一并修复。
