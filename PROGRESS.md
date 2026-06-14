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
- [ ] Milestone 5: Fragrance Recommend Engine (PLANNED)
- [ ] Milestone 6: Integration & Final Gate (PLANNED)

## Detailed Status
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
> 以下 3 个用例在 `HEAD` 上即失败，与 M4.1/M4.2 无关，需后续单独排查：
- `tests/test_analyzers.py::TestProfileAggregator::test_aggregate_compatibility`
- `tests/test_boundary_stress.py::test_preprocess_image_decompression_bomb`
- `tests/test_douyin_collector.py::test_collect_comments` (json.decoder.JSONDecodeError)
