# M5 香调推荐引擎 — 设计文档

- **状态**: 已批准（2026-06-14）
- **作者**: AI 助手 + 用户协作
- **关联文档**: `docs/03-part2-backend.md`（SSOT），本文档为其补充实现细节
- **范围**: M5 第一版（v1），覆盖 §2.1-2.5 五个 API、PromptFragranceEngine 引擎、冰山三层分析、对话微调

---

## 1. 背景与决策摘要

M5 实现"调香师输入标签 → AI 输出香调推荐方案 → 对话微调"的完整闭环。
基于 `docs/03-part2-backend.md` 第八章的 6 个未决问题，本次规划阶段已逐一对齐：

| 未决问题 | 决策 |
|---|---|
| 1. 对话流式输出 | **非流式 JSON**（v1）；`TODO(streaming)` 标记后续切换 |
| 2. 温度参数 | `/generate` 用 0.8，`/chat` 用 0.6；硬编码于 `constants/fragrance.py` |
| 3. 差异化策略 | **显式权重参数** `blogger_weight` / `audience_weight`（默认 0.5/0.5），可调 |
| 4. Prompt 版本管理 | v1 硬编码常量，文件头标 `PROMPT_VERSION`，不引入枚举/DB 表 |
| 5. 最大轮次 | 滑动窗口 20（`MAX_HISTORY_MESSAGES`），不限制总轮次 |
| 6. 冰山可视化 | 后端只返回结构化 `iceberg_analysis`，渲染属前端范畴 |

引擎抽象范围：**仅实现 `PromptFragranceEngine`**。`DifyFragranceEngine` / `LocalAgentFragranceEngine` 不写占位类（YAGNI），接入路径已在 `docs/03-part2-backend.md` §6.1 注明。

---

## 2. 架构与模块布局

```
backend/app/
├── api/v1/fragrance.py            # 5 个端点
├── schemas/fragrance.py           # Pydantic 请求/响应模型
├── services/fragrance_service.py  # 业务编排：调用引擎、读写 DB、聊天历史滑窗
├── engines/
│   ├── __init__.py                # ENGINE_REGISTRY + get_engine()
│   ├── base.py                    # FragranceEngine ABC
│   └── prompt_engine.py           # PromptFragranceEngine
└── constants/fragrance.py         # ICEBERG_ANALYSIS_PROMPT / CHAT_SYSTEM_PROMPT / 温度 / MAX_HISTORY
```

**关键约束**：
- `FragranceEngine` ABC 定义两个方法：`generate(profile, tags, weights) -> dict` 与 `chat(history, current_plans, user_message) -> tuple[str, list|None]`
- `FragranceService` 通过构造函数注入 engine（默认 `PromptFragranceEngine`），便于测试 mock
- 复用 M4 的 `get_db` 依赖注入模式，不引入新 DI 容器
- **只读** AnalysisTask + ProfileReport（验证 task 已 completed），不触碰 task_manager / SSE
- AIRegistry 槽位已就绪：`fragrance_reasoning`、`fragrance_chat`（均绑定 glm/glm-4）

**路径约束（CLAUDE.md §1）**：所有路径用 `pathlib` 动态获取，绝不硬编码根目录名。

---

## 3. 数据流

### 3.1 `/generate`（生成推荐方案）

```
Client POST /generate
  { task_id, selected_tags, blogger_weight?, audience_weight?, plan_count? }
    │
    ▼
FragranceService.generate()
  1. 校验 task 存在且 status="completed"（复用 TaskService.get_task）
  2. 校验 selected_tags 维度合法性（互斥组、max_select）
  3. 取 ProfileReport → 提取博主画像 + 粉丝画像
  4. 按 blogger_weight/audience_weight 融合画像文本
  5. engine.generate(fused_profile, selected_tags, plan_count)
       └─ 拼装 ICEBERG_ANALYSIS_PROMPT
       └─ registry.chat(slot="fragrance_reasoning", temperature=0.8)
       └─ parse_json_safely 解析 → 冰山三层 + recommendations[]
  6. 创建 FragranceSession（status="completed"），持久化 recommendations + selected_tags
  7. 返回 { session_id, recommendations, iceberg_analysis }
```

**对称性**：`generating` 中间态用于 AI 超时容错；失败时回写 `status="error"` 并保留 session 记录（不删除，便于排障）。

### 3.2 `/chat`（对话微调）

```
Client POST /{session_id}/chat
  { message }
    │
    ▼
FragranceService.chat()
  1. 取 session（404 if not found；400 if status="error"）
  2. 取最近 MAX_HISTORY_MESSAGES=20 条 ChatMessage（按 created_at 升序）
  3. 追加当前 user message → 写 DB（先持久化 user 消息）
  4. engine.chat(history, current_plans, message)
       └─ 拼装 CHAT_SYSTEM_PROMPT + 历史 + 方案上下文
       └─ registry.chat(slot="fragrance_chat", temperature=0.6)
       └─ 解析 → (reply_text, updated_plans | None)
  5. 写 assistant ChatMessage（content=reply_text, updated_plans=...）
  6. 若 updated_plans 非空 → 更新 session.recommendations
  7. 返回 { reply, updated_plans? }
```

**外部时序**：user 消息先落库（步骤 3），即使 AI 调用失败也保留对话痕迹；assistant 消息在 AI 成功后才写（步骤 5），避免半成品记录。

### 3.3 其他端点

- **POST /regenerate**：基于 session.selected_tags 重新调用 `engine.generate`（可换权重），**覆盖** session.recommendations 与冰山分析；旧 chat 历史清空（因为方案变了）。
- **GET /{session_id}**：返回 session 全量（recommendations + iceberg + selected_tags + status）。
- **GET /{session_id}/history**：返回该 session 的 ChatMessage 列表（role/content/updated_plans），按时间升序。

---

## 4. 错误处理与边界

| 场景 | 策略 | HTTP |
|---|---|---|
| AI 返回 JSON 解析失败 | `parse_json_safely` 落到 fallback → **重试一次**（重新调 AI，slot 不变）→ 仍失败则 session 标 `error`，返回 500 | 500 |
| AI 返回方案字段缺失 | 用默认值补全（空字符串 / 空数组），`warnings` 字段提示 | 200 |
| AI 调用超时/异常 | session 标 `error`，返回 502 | 502 |
| task 未 completed | 返回 400 "task not completed" | 400 |
| selected_tags 违反互斥组 | Pydantic 校验 + service 二次校验 → 422 | 422 |
| session 不存在 | 404 | 404 |
| session status=error 时调 chat | 400 "session in error state" | 400 |
| plan_count 超出 [1,5] | 422 | 422 |
| blogger_weight + audience_weight ≠ 1.0 | 自动归一化（不报错），warnings 提示 | 200 |

**重试边界**：JSON 解析重试**仅 1 次**（避免无限循环 + AI 成本）；重试时 prompt 追加"上次输出无法解析，请严格返回 JSON"。

---

## 5. 测试策略

### 单元测试 `tests/test_fragrance_service.py`
- mock `PromptFragranceEngine`（或直接 mock provider.chat），覆盖：
  - generate 正常路径（含权重融合）
  - generate JSON 解析失败 → 重试成功
  - generate 重试仍失败 → session error
  - chat 正常路径 + updated_plans 持久化
  - chat 历史滑窗（>20 条只取最近 20）
  - regenerate 覆盖 + 清空旧 chat
- 容错：task 未 completed、session 不存在、status=error

### API 集成测试 `tests/test_fragrance_api.py`
（用 `client` + dependency_overrides，复用 conftest）
- POST /generate 成功 → 返回 session_id + recommendations + iceberg
- POST /generate task 未 completed → 400
- POST /generate selected_tags 违反互斥组 → 422
- POST /{id}/chat 成功 → reply + updated_plans
- POST /{id}/chat session 不存在 → 404
- POST /{id}/regenerate 覆盖验证
- GET /{id} 与 /history 字段断言
- 权重归一化（传 0.3/0.4 自动归一，warnings 非空）

### 契约自检三问覆盖
1. **契约闭环**：每个端点测试断言 code/data/HTTP；互斥组、滑窗、重试都有用例
2. **对称性**：user 消息先写、assistant 后写；session error 不删记录；regenerate 清空旧 chat
3. **外部时序**：AI 调用失败时 session 状态机不卡在 generating；重试只 1 次

---

## 6. 模块依赖与前置条件

- **模型就绪**：`FragranceSession`、`ChatMessage`（`app/models/fragrance.py`）已存在
- **AIRegistry 槽位就绪**：`fragrance_reasoning`、`fragrance_chat`（glm/glm-4）
- **复用 M4**：`TaskService.get_task`、`get_db` 依赖、conftest 的 client/db fixture
- **ProfileReport**：M4 已实现，FragranceService 通过 `task_id` 关联读取
- **PromptFragranceEngine**：复用 `BaseAnalyzer.parse_json_safely`（M3 实现）

---

## 7. 后续接入 Dify 的路径（不在 M5 范围）

1. 在 `app/engines/` 新建 `dify_engine.py`，实现 `DifyFragranceEngine(FragranceEngine)`。
   其 `generate` / `chat` 方法内部改为调用 Dify Workflow HTTP API
   （如 `POST /v1/workflows/run`），把 `selected_tags` / `history` 作为输入变量传入。
2. 在 `app/engines/__init__.py` 的 `ENGINE_REGISTRY` 注册 `"dify": DifyFragranceEngine`。
3. 在 `app/config.py` 增加 Dify 相关配置（API key、workflow_id）。
4. 通过 `FRAGRANCE_ENGINE` 环境变量切换引擎，无需改动 `FragranceService` 与 API 层。

同理，`LocalAgentFragranceEngine` 接入时只需新增一个 `FragranceEngine` 子类并注册。

切换 chat 到 SSE 流式（后续）：
1. AIRegistry 暴露 `chat_stream` 接口
2. 各 provider 适配器实现 `stream=True`
3. `/chat` 端点改用 SSE 响应（复用 M4 的 SSE helper）
