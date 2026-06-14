# Part2 后端开发文档 — 香调推荐引擎

> **文档版本**: v1.0  
> **创建时间**: 2026-06-13  
> **依赖文档**: `00-global-dev-guide.md`

---

## 一、模块概述

Part2 接收 Part1 产生的用户画像标签（经调香师筛选），通过冰山理论模型推理，生成多套香调推荐方案，并支持对话式微调。

### 1.1 处理流程

```
输入: 调香师筛选后的标签集合
    ↓
Step 1: 冰山理论分析
    ├── 显性层（Surface）: 从标签中提取显性行为特征
    ├── 情感层（Middle）: 推导情感需求和价值取向
    └── 深层（Deep）: 挖掘潜意识和内在诉求
    ↓
Step 2: 香调推荐生成
    → 基于冰山分析 → 多套香调方案
    → 每套方案: 大类 + 前中后调具体香材 + 推荐原因 + 创作灵感故事
    ↓
Step 3: 对话微调（可选）
    → 调香师追问 → AI 分析意图 → 修改方案 → 返回更新
    ↓
输出: FragranceSession (多套推荐方案 + 对话历史)
```

### 1.2 第一版实现策略

> [!IMPORTANT]
> 冰山理论模型在第一版中使用 **AI Prompt Engineering** 方式实现（将冰山理论的分层逻辑编入 Prompt），不做独立的机器学习模型。后续可替换为专门训练的模型或接入 Dify 工作流。

---

## 二、API 详细设计

### 2.1 生成香调推荐

**`POST /api/v1/fragrance/generate`**

请求体:
```json
{
  "task_id": "a1b2c3d4-...",
  "selected_tags": {
    "climate_consumption": {
      "climate_zone": ["湿热南方"],
      "city_tier": ["一线/新一线", "二线"],
      "culture_circle": ["内陆文化圈"],
      "concentration": ["全国分散型"]
    },
    "fragrance_consumption": {
      "price_tier": ["轻奢入门", "品质消费"],
      "purchase_motivation": ["情绪需求", "社交需求"],
      "decision_path": ["种草型"],
      "consumption_frequency": ["场合驱动"]
    },
    "fashion_fragrance_map": {
      "fashion_style": ["甜美系", "古典系"],
      "fashion_scene": ["拍照出片", "约会社交"],
      "color_preference": ["粉色系", "蓝紫系"],
      "fashion_completeness": ["精致"]
    },
    "lifestyle_scenario": {
      "core_interest": ["亚文化穿搭", "日常自拍"],
      "social_activity": ["圈层社交"],
      "aesthetic_personality": ["冒险型"],
      "fragrance_timing": ["全天"],
      "content_consumption": ["种草转化型"]
    }
  },
  "plan_count": 3
}
```

响应:
```json
{
  "code": 0,
  "data": {
    "session_id": "s1s2s3s4-...",
    "status": "completed",
    "recommendations": [
      {
        "plan_id": "plan_1",
        "name": "粉色之梦 — 花果甜香",
        "category": "花果香调",
        "top_notes": [
          {
            "name": "佛手柑",
            "description": "明亮清新的开场",
            "reason": "呼应粉色系审美中的活力感"
          },
          {
            "name": "粉红胡椒",
            "description": "微辣的甜蜜点缀",
            "reason": "匹配甜美系风格中的俏皮元素"
          }
        ],
        "middle_notes": [
          {
            "name": "鸢尾花",
            "description": "粉质的优雅花香",
            "reason": "连接古典系审美与蓝紫色偏好"
          },
          {
            "name": "玫瑰",
            "description": "经典的浪漫花香",
            "reason": "呼应约会社交场景的浪漫需求"
          }
        ],
        "base_notes": [
          {
            "name": "白檀",
            "description": "温柔的木质收尾",
            "reason": "提供内陆文化圈熟悉的东方感"
          },
          {
            "name": "香草",
            "description": "甜蜜的温暖基调",
            "reason": "满足情绪需求中的安全感和愉悦"
          }
        ],
        "recommendation_reason": "这个方案直接呼应了目标群体的甜美系穿搭偏好和粉色系色彩倾向。前调的佛手柑和粉红胡椒创造了活泼甜蜜的第一印象，适合种草型消费者的「第一嗅」冲击。中调的鸢尾花和玫瑰兼顾了古典系的优雅和约会场景的浪漫氛围。后调的白檀和香草提供了温暖的收尾，呼应了内陆文化圈对东方香调的天然亲近感，同时满足了情绪需求中对「被温柔包裹」的深层渴望。",
        "fragrance_story": "她在镜子前最后确认了蝴蝶结的位置。今天是同好会的茶会，她选了那条粉色的洛丽塔裙。出门前，她在手腕上按下最后一个仪式——喷雾升起，先是一阵清亮的柑橘，像推开花园门的那一刻。然后是粉质的花香缓缓展开，像那些她反复截图收藏的少女漫画场景。等到傍晚，只剩下贴着皮肤的温暖甜香，是她给自己的、属于今天的奖励。",
        "iceberg_analysis": {
          "surface": "显性行为层：甜美系穿搭、粉色系偏好、圈层社交（同好会/茶会）、种草型消费路径，这些指向了一个高度视觉化、注重外在形象表达的用户群体。",
          "middle": "情感价值层：情绪需求驱动的消费动机，拍照出片和约会社交的场景需求，反映了这个群体通过「穿搭-拍照-分享」的闭环来获得自我认同和社交认可。香水在这里是「完整look的最后一笔」。",
          "deep": "深层需求：在亚文化穿搭的表象下，是对「理想化自我」的持续构建。她们通过精致的外在包装来回应内心对美好、浪漫、被重视的渴望。香水不仅是装饰，更是一种「穿上另一个自己」的仪式感。"
        }
      },
      {
        "plan_id": "plan_2",
        "name": "紫色回廊 — 东方花香",
        "category": "东方花香调",
        "top_notes": [...],
        "middle_notes": [...],
        "base_notes": [...],
        "recommendation_reason": "...",
        "fragrance_story": "...",
        "iceberg_analysis": {...}
      },
      {
        "plan_id": "plan_3",
        "name": "...",
        "category": "...",
        ...
      }
    ]
  }
}
```

**业务逻辑**:
1. 验证 `task_id` 存在且分析已完成
2. 构建冰山理论 Prompt（标签 → 冰山三层分析 → 香调推荐）
3. 调用 AI 生成推荐方案
4. 解析 AI 返回的结构化数据
5. 创建 `FragranceSession` + 初始 `ChatMessage`（assistant 角色）
6. 返回推荐结果

---

### 2.2 追问对话

**`POST /api/v1/fragrance/{session_id}/chat`**

请求体:
```json
{
  "message": "方案一的后调能不能换成沉香和乌木？我觉得需要更深沉一些"
}
```

响应:
```json
{
  "code": 0,
  "data": {
    "reply": "好的，我理解你希望增加方案一的深度和层次感。将后调从白檀+香草替换为沉香+乌木是一个很好的方向——这会让整体从「甜美少女」转向「甜美中带暗黑」的风格，恰好也能呼应粉丝群体中15%的哥特系偏好...",
    "updated_plans": [
      {
        "plan_id": "plan_1",
        "name": "暗夜玫瑰 — 花香木质",
        "category": "花香木质调",
        "top_notes": [
          {"name": "佛手柑", "description": "明亮清新的开场", "reason": "保持原有的活力开场"},
          {"name": "粉红胡椒", "description": "微辣的甜蜜点缀", "reason": "保持原有的俏皮元素"}
        ],
        "middle_notes": [
          {"name": "鸢尾花", "description": "粉质的优雅花香", "reason": "保持优雅过渡"},
          {"name": "玫瑰", "description": "经典的浪漫花香", "reason": "浪漫主线不变"}
        ],
        "base_notes": [
          {"name": "沉香", "description": "深沉的东方木质", "reason": "增加神秘感和深度，呼应哥特系偏好", "changed": true},
          {"name": "乌木", "description": "烟熏的暗色木质", "reason": "与粉色系形成「甜美×暗黑」的反差张力", "changed": true}
        ],
        "recommendation_reason": "修改后的方案保留了花果甜美的前中调，但通过沉香和乌木的后调创造了一个戏剧性的反转...",
        "fragrance_story": "...(更新后的故事)...",
        "iceberg_analysis": {...}
      }
    ],
    "message_id": "msg_xxx"
  }
}
```

**关键设计**:
- `updated_plans` 只包含**被修改的方案**，未修改的不返回
- 被修改的香材标注 `"changed": true`，方便前端高亮显示变更
- 如果对话不涉及方案修改（纯咨询），`updated_plans` 为 null

---

### 2.3 重新生成

**`POST /api/v1/fragrance/{session_id}/regenerate`**

请求体:
```json
{
  "selected_tags": { ... },
  "plan_count": 3
}
```

- 清空当前会话的所有对话历史
- 用新的标签重新生成推荐方案
- 响应格式与 `generate` 相同

---

### 2.4 获取推荐结果

**`GET /api/v1/fragrance/{session_id}`**

用于页面刷新或从历史记录进入时恢复数据。

响应:
```json
{
  "code": 0,
  "data": {
    "session_id": "s1s2s3s4-...",
    "task_id": "a1b2c3d4-...",
    "selected_tags": { ... },
    "recommendations": [ ... ],
    "status": "completed",
    "created_at": "2026-06-13T11:00:00+08:00"
  }
}
```

---

### 2.5 获取对话历史

**`GET /api/v1/fragrance/{session_id}/history`**

响应:
```json
{
  "code": 0,
  "data": {
    "messages": [
      {
        "id": "msg_1",
        "role": "assistant",
        "content": "根据您选择的标签，我为您生成了3套香调方案...",
        "updated_plans": null,
        "created_at": "2026-06-13T11:00:00+08:00"
      },
      {
        "id": "msg_2",
        "role": "user",
        "content": "方案一的后调能不能换成沉香和乌木？",
        "created_at": "2026-06-13T11:02:00+08:00"
      },
      {
        "id": "msg_3",
        "role": "assistant",
        "content": "好的，我理解你希望...",
        "updated_plans": [{ "plan_id": "plan_1", ... }],
        "created_at": "2026-06-13T11:02:05+08:00"
      }
    ]
  }
}
```

---

## 三、冰山理论模型

### 3.1 理论框架

冰山理论（Iceberg Model）将用户需求分为三层：

```
        ┌─────────────┐
        │   显性行为   │  ← 水面之上（可直接观察）
        │  Surface     │     穿搭风格、消费行为、地域
        ├─────────────┤  ← 水面线
        │   情感价值   │  ← 水面之下（需要推理）
        │  Middle      │     情感需求、社交需求、审美价值
        ├─────────────┤
        │   深层需求   │  ← 最深层（潜意识）
        │  Deep        │     身份认同、安全感、自我实现
        └─────────────┘
```

### 3.2 从标签到冰山层的映射

| 标签类别 | 冰山层 | 推导方向 |
|---|---|---|
| 气候带、城市线级 | Surface | 环境对香调偏好的直接影响 |
| 穿搭风格、色彩偏好 | Surface → Middle | 从外在风格推导内在审美取向 |
| 消费动机 | Middle | 直接反映情感和价值需求 |
| 决策路径 | Middle | 反映信息获取和决策习惯 |
| 审美性格 | Middle → Deep | 从审美偏好推导深层性格 |
| 核心兴趣 | Middle | 生活方式反映价值取向 |
| 社交活跃度 | Middle → Deep | 社交行为反映归属需求 |
| 穿搭完整度 | Middle → Deep | 精致程度反映自我要求 |
| 消费频次、用香时段 | Surface → Middle | 使用习惯反映生活态度 |

### 3.3 第一版 Prompt 实现

```python
# fragrance/prompt_templates.py

ICEBERG_ANALYSIS_PROMPT = """
你是一位资深的香水行业顾问，擅长通过用户画像分析来推荐香调方案。
你需要运用"冰山理论"来深度理解目标用户群体。

## 冰山理论分析框架

**第一层 - 显性行为（水面之上）**
分析用户标签中直接可见的行为特征：
- 穿搭风格和场景（他们穿什么、在什么场合穿）
- 消费能力和频次（花多少钱、多久买一次）
- 地域和文化背景（在哪里、受什么文化影响）
- 社交习惯（线上还是线下、高频还是低频）

**第二层 - 情感价值（水面之下）**
从显性行为推导出的情感和价值需求：
- 他们通过穿搭想要表达什么？（自我认同、群体归属、独特性）
- 他们的消费是为了什么情感满足？（悦己、社交认可、仪式感）
- 他们的审美偏好反映了什么价值取向？（传统vs前卫、保守vs冒险）

**第三层 - 深层需求（冰山底部）**
最内在的心理需求：
- 他们真正渴望什么？（被重视、安全感、自我实现、逃离日常）
- 香水在他们的生活中扮演什么角色？（装饰、武器、护盾、仪式）
- 他们选择一款香水时，真正在选择什么？（一种身份、一段记忆、一个理想中的自己）

## 用户标签

{selected_tags_formatted}

## 任务

请基于以上标签，完成以下分析并生成 {plan_count} 套香调推荐方案：

1. 先进行冰山三层分析
2. 基于分析结果，生成推荐方案
3. 每套方案必须包含：
   - 方案名称（有诗意的名字）
   - 香调大类
   - 前调 2-3 个香材（附带推荐理由）
   - 中调 2-3 个香材（附带推荐理由）
   - 后调 2-3 个香材（附带推荐理由）
   - 详细的推荐原因（解释每个香材选择背后的逻辑，与标签的关联）
   - 创作灵感故事（面向调香师的灵感文字，描绘一个使用这款香水的场景故事，帮助调香师感受这款香的灵魂）

4. 不同方案之间要有明显差异化（不同香调方向）

请以 JSON 格式返回，格式如下：
```json
{
  "iceberg_analysis": {
    "surface": "显性行为层分析文字...",
    "middle": "情感价值层分析文字...",
    "deep": "深层需求分析文字..."
  },
  "recommendations": [
    {
      "plan_id": "plan_1",
      "name": "方案名称",
      "category": "香调大类",
      "top_notes": [
        {"name": "香材名", "description": "简短描述", "reason": "推荐理由"}
      ],
      "middle_notes": [...],
      "base_notes": [...],
      "recommendation_reason": "详细推荐原因...",
      "fragrance_story": "创作灵感故事..."
    }
  ]
}
```
"""

CHAT_SYSTEM_PROMPT = """
你是一位资深的香水行业顾问，正在与一位调香师讨论香调方案。

当前的用户画像标签：
{selected_tags_formatted}

当前的推荐方案：
{current_plans_formatted}

请基于调香师的反馈来调整方案。
- 如果调香师要求修改某个方案，请返回修改后的完整方案
- 如果调香师只是咨询，不需要修改方案
- 保持专业但友好的语气
- 每次修改都要说明修改原因

如果需要修改方案，请在回复中包含 JSON 块：
```json
{"updated_plans": [{完整的修改后方案}]}
```
如果不需要修改，直接用文字回答即可。
"""
```

### 3.4 冰山理论探索方向

> [!NOTE]
> 以下是后续深入研究冰山理论模型的几个方向，供参考。

#### 方向一：知识图谱 + Prompt

构建一个「标签 → 心理需求 → 香调」的知识图谱：
- 从心理学文献、香水行业报告中提取映射关系
- 将知识图谱注入 Prompt 作为参考知识
- 优点：可解释性强，可以精确控制映射规则

#### 方向二：Fine-tuning

用调香师的实际推荐案例进行微调：
- 收集「用户画像 → 调香师推荐方案」的配对数据
- 微调开源 LLM（如 Qwen、GLM）
- 优点：推荐质量高，能学到行业隐性知识

#### 方向三：RAG (检索增强生成)

建立香水知识库 + 检索增强：
- 收集大量香水资料（成分、风格、适合人群、故事）
- 用户标签 → 检索相关香水案例 → 参考生成
- 优点：推荐有据可依，可以引用实际产品

#### 方向四：Dify 工作流

使用 Dify 构建可视化的推理工作流：
- 拖拽式编排冰山分析 → 香调推荐的流程
- 可以方便地调整流程节点和 Prompt
- 优点：非开发人员也能调整推荐逻辑

---

## 四、香调推荐服务

### 4.1 FragranceService

```python
class FragranceService:
    """香调推荐服务"""
    
    def __init__(
        self,
        ai_registry: AIRegistry,
        session_repo: FragranceSessionRepository,
        message_repo: ChatMessageRepository,
    ):
        self.ai = ai_registry
        self.session_repo = session_repo
        self.message_repo = message_repo
    
    async def generate(
        self, 
        task_id: str, 
        selected_tags: dict, 
        plan_count: int = 3
    ) -> FragranceSession:
        """
        生成香调推荐方案
        
        1. 格式化标签为 Prompt 输入
        2. 调用 AI（fragrance_reasoning 槽位）
        3. 解析返回的 JSON
        4. 创建 Session 和初始消息
        """
        # 格式化标签
        tags_formatted = self._format_tags(selected_tags)
        
        # 构建 Prompt
        prompt = ICEBERG_ANALYSIS_PROMPT.format(
            selected_tags_formatted=tags_formatted,
            plan_count=plan_count
        )
        
        # 调用 AI
        ai_provider = self.ai.get_provider_for_slot("fragrance_reasoning")
        response = await ai_provider.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # 创意生成用较高温度
            max_tokens=4096
        )
        
        # 解析 JSON
        result = self._parse_response(response)
        
        # 保存
        session = await self.session_repo.create(
            task_id=task_id,
            selected_tags=selected_tags,
            recommendations=result["recommendations"],
            iceberg_analysis=result["iceberg_analysis"]
        )
        
        # 保存初始 assistant 消息
        await self.message_repo.create(
            session_id=session.id,
            role="assistant",
            content=f"根据您选择的标签，我为您生成了 {plan_count} 套香调方案。",
            updated_plans=None
        )
        
        return session
    
    async def chat(
        self, 
        session_id: str, 
        user_message: str
    ) -> dict:
        """
        对话微调
        
        1. 获取对话历史
        2. 构建带上下文的 Prompt
        3. 调用 AI（fragrance_chat 槽位）
        4. 解析是否包含方案修改
        5. 如果有修改，更新 Session 中的方案
        6. 保存消息
        """
        session = await self.session_repo.get(session_id)
        history = await self.message_repo.get_by_session(session_id)
        
        # 构建消息列表
        messages = [
            {
                "role": "system",
                "content": CHAT_SYSTEM_PROMPT.format(
                    selected_tags_formatted=self._format_tags(session.selected_tags),
                    current_plans_formatted=self._format_plans(session.recommendations)
                )
            }
        ]
        
        # 添加历史对话
        for msg in history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # 添加新消息
        messages.append({"role": "user", "content": user_message})
        
        # 保存用户消息
        await self.message_repo.create(
            session_id=session_id,
            role="user",
            content=user_message
        )
        
        # 调用 AI
        ai_provider = self.ai.get_provider_for_slot("fragrance_chat")
        response = await ai_provider.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=3000
        )
        
        # 解析是否有方案修改
        reply_text, updated_plans = self._parse_chat_response(response)
        
        # 如果有修改，更新 Session 中的方案
        if updated_plans:
            await self._update_session_plans(session, updated_plans)
        
        # 保存 AI 回复
        await self.message_repo.create(
            session_id=session_id,
            role="assistant",
            content=reply_text,
            updated_plans=updated_plans
        )
        
        return {
            "reply": reply_text,
            "updated_plans": updated_plans
        }
    
    async def regenerate(
        self, 
        session_id: str, 
        selected_tags: dict,
        plan_count: int = 3
    ) -> FragranceSession:
        """
        重新生成方案
        
        1. 清空对话历史
        2. 用新标签重新生成
        """
        # 清空历史消息
        await self.message_repo.delete_by_session(session_id)
        
        # 获取 session
        session = await self.session_repo.get(session_id)
        
        # 重新生成
        tags_formatted = self._format_tags(selected_tags)
        prompt = ICEBERG_ANALYSIS_PROMPT.format(
            selected_tags_formatted=tags_formatted,
            plan_count=plan_count
        )
        
        ai_provider = self.ai.get_provider_for_slot("fragrance_reasoning")
        response = await ai_provider.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=4096
        )
        
        result = self._parse_response(response)
        
        # 更新 session
        session = await self.session_repo.update(
            session_id=session_id,
            selected_tags=selected_tags,
            recommendations=result["recommendations"],
            iceberg_analysis=result["iceberg_analysis"]
        )
        
        return session
```

### 4.2 标签格式化

```python
def _format_tags(self, selected_tags: dict) -> str:
    """将标签字典格式化为 Prompt 友好的文本"""
    
    DIMENSION_NAMES = {
        "climate_consumption": "气候-消费带",
        "fragrance_consumption": "香氛消费推断",
        "fashion_fragrance_map": "穿搭风格-香调映射",
        "lifestyle_scenario": "生活方式-用香场景"
    }
    
    SUB_DIMENSION_NAMES = {
        "climate_zone": "气候带",
        "city_tier": "城市线级",
        "culture_circle": "文化圈",
        "concentration": "地域集中度",
        "price_tier": "价格带",
        "purchase_motivation": "消费动机",
        "decision_path": "决策路径",
        "consumption_frequency": "消费频次",
        "fashion_style": "穿搭风格",
        "fashion_scene": "穿搭场景",
        "color_preference": "色彩偏好",
        "fashion_completeness": "穿搭完整度",
        "core_interest": "核心兴趣",
        "social_activity": "社交活跃度",
        "aesthetic_personality": "审美性格",
        "fragrance_timing": "用香时段",
        "content_consumption": "内容消费特征"
    }
    
    lines = []
    for dim_id, sub_dims in selected_tags.items():
        lines.append(f"\n### {DIMENSION_NAMES.get(dim_id, dim_id)}")
        for sub_id, tags in sub_dims.items():
            tag_str = "、".join(tags) if isinstance(tags, list) else tags
            lines.append(f"- {SUB_DIMENSION_NAMES.get(sub_id, sub_id)}: {tag_str}")
    
    return "\n".join(lines)
```

### 4.3 AI 响应解析

```python
def _parse_response(self, response: str) -> dict:
    """解析 AI 返回的 JSON（可能被包裹在 markdown code block 中）"""
    import re
    import json
    
    # 尝试提取 JSON 块
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 尝试直接解析整个响应
        json_str = response
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 如果解析失败，用 AI 再处理一次
        raise AIResponseParseError(f"无法解析 AI 响应: {response[:200]}...")


def _parse_chat_response(self, response: str) -> tuple[str, list[dict] | None]:
    """
    解析对话响应
    返回: (纯文字回复, 更新的方案列表或None)
    """
    import re
    import json
    
    # 尝试提取 JSON 块
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    
    if json_match:
        # 有 JSON 块 → 有方案修改
        json_str = json_match.group(1)
        data = json.loads(json_str)
        updated_plans = data.get("updated_plans", [])
        
        # 提取纯文字部分（去掉 JSON 块）
        text = re.sub(r'```json\s*.*?\s*```', '', response, flags=re.DOTALL).strip()
        
        return text, updated_plans
    else:
        # 无 JSON 块 → 纯文字回复
        return response, None
```

---

## 五、对话上下文管理

### 5.1 上下文窗口

AI 对话的上下文包含：
1. **System Prompt**: 包含当前标签和当前方案的完整信息
2. **对话历史**: 所有历史消息

为了防止上下文过长，需要控制历史消息数量：

```python
MAX_HISTORY_MESSAGES = 20  # 最多保留最近 20 条消息

def _build_messages(self, session, history, user_message):
    messages = [{"role": "system", "content": self._build_system_prompt(session)}]
    
    # 截取最近的历史消息
    recent_history = history[-MAX_HISTORY_MESSAGES:] if len(history) > MAX_HISTORY_MESSAGES else history
    
    for msg in recent_history:
        messages.append({"role": msg.role, "content": msg.content})
    
    messages.append({"role": "user", "content": user_message})
    
    return messages
```

### 5.2 方案版本管理

每次对话修改方案时，Session 中的 `recommendations` 会被更新为最新版本。历史版本通过 `ChatMessage.updated_plans` 追溯。

```python
async def _update_session_plans(self, session, updated_plans):
    """更新 session 中的方案"""
    current_plans = session.recommendations.copy()
    
    for updated in updated_plans:
        for i, plan in enumerate(current_plans):
            if plan["plan_id"] == updated["plan_id"]:
                current_plans[i] = updated
                break
    
    await self.session_repo.update(
        session_id=session.id,
        recommendations=current_plans
    )
```

---

## 六、后端接入层抽象

### 6.1 推荐引擎接口

为了支持后续切换到 Dify/本地 Agent/其他实现，定义统一接口。
**M5 第一版只实现 `PromptFragranceEngine`**；`DifyFragranceEngine` 与 `LocalAgentFragranceEngine`
不写代码占位类（YAGNI），其接入路径见下方"后续接入说明"。

```python
class FragranceEngine(ABC):
    """香调推荐引擎基类"""
    
    @abstractmethod
    async def generate(
        self, 
        selected_tags: dict, 
        plan_count: int = 3
    ) -> dict:
        """生成推荐方案"""
        ...
    
    @abstractmethod
    async def chat(
        self, 
        history: list[dict],
        current_plans: list[dict],
        user_message: str
    ) -> tuple[str, list[dict] | None]:
        """对话微调，返回 (回复文字, 更新的方案列表或None)"""
        ...


class PromptFragranceEngine(FragranceEngine):
    """基于 Prompt 的推荐引擎（第一版，M5 实现此类的全部逻辑）"""
    ...
```

> **后续接入 Dify 的步骤（不在 M5 范围）**：
> 1. 在 `app/engines/` 新建 `dify_engine.py`，实现 `DifyFragranceEngine(FragranceEngine)`。
>    其 `generate` / `chat` 方法内部改为调用 Dify Workflow HTTP API
>    （如 `POST /v1/workflows/run`），把 `selected_tags` / `history` 作为输入变量传入。
> 2. 在 `app/engines/__init__.py` 的 `ENGINE_REGISTRY` 注册 `"dify": DifyFragranceEngine`。
> 3. 在 `app/config.py` 增加 Dify 相关配置（API key、workflow_id）。
> 4. 通过 `FRAGRANCE_ENGINE` 环境变量切换引擎，无需改动 `FragranceService` 与 API 层。
>
> 同理，`LocalAgentFragranceEngine` 接入时只需新增一个 `FragranceEngine` 子类并注册。

### 6.2 引擎注册与切换

```python
# config.py
FRAGRANCE_ENGINE = "prompt"  # "prompt" | "dify"（M5 v1 仅 "prompt" 可用）

# engines/__init__.py
ENGINE_REGISTRY = {
    "prompt": PromptFragranceEngine,
    # "dify": DifyFragranceEngine,       # M5 之后接入
    # "local_agent": LocalAgentFragranceEngine,  # 未来扩展
}

def get_engine() -> FragranceEngine:
    engine_type = config.FRAGRANCE_ENGINE
    return ENGINE_REGISTRY[engine_type]()
```

---

## 七、错误处理

| 错误场景 | 处理策略 |
|---|---|
| AI 返回 JSON 解析失败 | 重试一次（重新调用 AI），仍失败则返回错误提示 |
| AI 返回方案格式不完整 | 补全缺失字段为默认值，返回警告 |
| 对话中 AI 误解意图 | 前端提示"AI 可能未正确理解，请尝试更具体地描述" |
| AI API 限流 | 自动重试（指数退避），提示用户稍后再试 |
| Session 不存在 | 返回 404 |

---

## 八、待进一步讨论的问题

> [!NOTE]
> 以下问题已在 M5 规划阶段（2026-06-14）逐一对齐并定稿。决策结果直接进入实现，
> 不再作为开放问题。如需调整，须同步更新本节及 `docs/superpowers/specs/` 下的设计文档。

1. **对话是否需要流式输出** — **决策（M5 v1）：非流式 JSON 响应。**
   `/chat` 一次性返回 AI 完整响应。后续若需"打字机效果"，需（a）在 AIRegistry 暴露 `chat_stream` 接口、
   （b）各 provider 适配器实现 `stream=True`、（c）端点改用 SSE 响应。
   实现代码中保留 `TODO(streaming)` 标记以便后续切换。
2. **方案生成的温度参数** — **决策：按场景区分，硬编码。**
   `/generate` 用 `temperature=0.8`（鼓励创意），`/chat` 用 `temperature=0.6`（逻辑连贯）。
   第一版不暴露给调香师可调；常量定义于 `app/constants/fragrance.py`，后续可改为请求参数。
3. **方案的差异化策略** — **决策：显式权重参数。**
   通过 `blogger_weight` / `audience_weight`（请求体可选，默认 0.5/0.5）控制博主画像与粉丝画像在
   prompt 中的融合权重。`FragranceService` 在拼接 `ICEBERG_ANALYSIS_PROMPT` 时按权重填充两侧内容。
   此为**可调参数**，调香师可在前端调整以观察不同侧重下的推荐变化。
4. **Prompt 版本管理** — **决策：v1 硬编码。**
   模板作为字符串常量置于 `app/constants/fragrance.py`，文件头标注版本号（如 `PROMPT_VERSION = "v1"`）。
   不引入 `PromptVersion` 枚举或 DB 表；迭代时在常量文件追加新版本注释与 `git diff` 追溯。
5. **对话的最大轮次** — **决策：滑动窗口 20。**
   采用文档既定的 `MAX_HISTORY_MESSAGES=20`。`FragranceService` 在拼装 chat prompt 时保留最近 20 条
   消息；不额外限制总轮次，调香师可无限对话（超出部分旧消息不进入上下文）。
6. **冰山分析的可视化** — **决策：后端只返回结构化数据。**
   `/generate` 响应体携带 `iceberg_analysis`（含三层：表层/中层/深层），后端不关心前端如何渲染。
   前端是否展示三层文字属前端范畴，后端契约只保证字段存在且 schema 稳定。
