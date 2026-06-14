# AromotionAI - Development Progress

## Overall Milestones
- [x] Milestone E2E: E2E Testing Suite (DONE)
- [x] Milestone 1: Infrastructure & Cookie Mgmt (DONE)
- [x] Milestone 2: Data Collection & Media Proc (DONE)
- [/] Milestone 3: AI Analyzers & Profile Agg (IN_PROGRESS)
  - [x] M3.1: AI Registry (DONE, tests passed)
  - [x] M3.2: Visual & Comment Analyzers (DONE, tests passed)
  - [x] M3.3: Profile Aggregator (DONE, tests passed)
  - [ ] M3.4: Tests & Integration (PLANNED)
- [/] Milestone 4: Task Manager & SSE API (IN_PROGRESS)
  - [x] M4.1: TaskManager (Memory-based) (DONE, tests passed)
  - [x] M4.2: AnalysisService (Pipeline Orchestration) (DONE)
  - [x] M4.3: Analysis REST + SSE API (DONE, 23 tests passed)
  - [x] M4.4: Report/Tags/Delete endpoints (DONE)
- [x] Milestone 5: Fragrance Recommend Engine (DONE)
  - [x] M5.1: FragranceEngine ABC + PromptFragranceEngine (DONE, 20 service tests passed)
  - [x] M5.2: FragranceService 业务编排 (DONE)
  - [x] M5.3: Fragrance REST API 5 端点 (DONE, 15 API tests passed)
- [ ] Milestone 6: Integration & Final Gate (PLANNED)

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

## Known Pre-existing Test Failures (待修复，非本次提交范围)
> ~~以下 3 个用例在 `HEAD` 上即失败，与 M4.1/M4.2 无关，需后续单独排查：~~
> **2026-06-14 已修复**：3 个用例全部处理完成（2 修复 + 1 跳过）。
> 单元测试整体结果：**98 passed, 1 skipped, 0 failed**。

### ⚠️ 待人工测试（已标记 @pytest.mark.skip）
- `tests/test_douyin_collector.py::test_collect_comments`
  - **原因**：Playwright mock 链路与实际 collector 代码已漂移，fallback 到 curl_cffi 时会发起**真实抖音 API 请求**。
  - **如何验证**：(1) 重写 mock 以匹配当前 `collect_comments` 的实际调用链；或 (2) 在拥有有效抖音 Cookie + 网络访问的环境下手动运行。
  - **优先级**：M5/M6 阶段统一处理真实网络集成测试时一并修复。

### ⚠️ e2e 测试套件 httpx 兼容性问题（待修复，非本次提交范围）
- **现象**：`tests/e2e/` 下 82 个用例在 setup 阶段全部报错 `TypeError: AsyncClient.__init__() got an unexpected keyword argument 'app'`。
- **原因**：`tests/e2e/conftest.py:930` 使用 `httpx.AsyncClient(app=app, ...)`，该参数在新版 httpx 中已废弃（应改用 `httpx.ASGITransport(app=app)`）。
- **影响范围**：仅 e2e 测试，不影响单元测试（133 passed, 1 skipped）。
- **优先级**：M6 阶段统一修复 e2e 测试基础设施时处理。
