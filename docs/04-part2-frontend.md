# Part2 前端开发文档 — 香调推荐页

> **文档版本**: v1.0  
> **创建时间**: 2026-06-13  
> **依赖文档**: `00-global-dev-guide.md`, `03-part2-backend.md`

---

## 一、页面概览

Part2 前端只有一个核心页面：**香调推荐页**，采用双栏布局。

| 页面 | 路由 | 功能 |
|---|---|---|
| 香调推荐页 | `/recommend/:sessionId` | 左侧方案卡片（实时更新）+ 右侧对话区 |

---

## 二、香调推荐页 (`/recommend/:sessionId`)

### 2.1 页面结构（双栏布局 — 方案B）

```
┌──────────────────────────────────────────────────────────────┐
│  ← 返回标签筛选           香调推荐           [重新生成 ⟳]     │
├───────────────────────────┬──────────────────────────────────┤
│                           │                                  │
│  📋 方案一                │  💬 对话                          │
│  ┌───────────────────┐   │                                  │
│  │ 🌸 粉色之梦        │   │  🤖 根据您选择的标签，           │
│  │ 花果甜香            │   │     我为您生成了3套方案...       │
│  │                     │   │                                  │
│  │ 🔝 前调             │   │  🧑 方案一的后调能不能换         │
│  │ · 佛手柑 → ...     │   │     成沉香和乌木？               │
│  │ · 粉红胡椒 → ...   │   │                                  │
│  │                     │   │  🤖 好的，我理解你希望           │
│  │ 💫 中调             │   │     增加深度和层次感...           │
│  │ · 鸢尾花 → ...     │   │     [方案一已更新 ✨]             │
│  │ · 玫瑰 → ...       │   │                                  │
│  │                     │   │                                  │
│  │ 🌿 后调             │   │                                  │
│  │ · 沉香 → ... ✨     │   │                                  │
│  │ · 乌木 → ... ✨     │   │                                  │
│  │                     │   │                                  │
│  │ 📝 推荐原因         │   │                                  │
│  │ [展开/收起]         │   │                                  │
│  │                     │   │                                  │
│  │ 📖 创作灵感         │   │                                  │
│  │ [展开/收起]         │   │                                  │
│  └───────────────────┘   │                                  │
│                           │                                  │
│  📋 方案二                │                                  │
│  ┌───────────────────┐   │                                  │
│  │ 💜 紫色回廊        │   │                                  │
│  │ 东方花香            │   │                                  │
│  │ ...                │   │                                  │
│  └───────────────────┘   │                                  │
│                           │                                  │
│  📋 方案三                │                                  │
│  ┌───────────────────┐   │                                  │
│  │ ...                │   │                                  │
│  └───────────────────┘   ├──────────────────────────────────┤
│                           │ [💬 输入你的想法...]       [发送] │
├───────────────────────────┴──────────────────────────────────┤
│  [🔙 返回报告]    [🏷️ 返回标签筛选]    [📋 查看冰山分析]     │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 左侧：方案展示区

#### 方案卡片设计

每个方案卡片包含以下可折叠区域：

```
┌─ 方案卡片 ────────────────────────────────────────────┐
│                                                        │
│  🌸 粉色之梦 — 花果甜香                        [Plan 1] │
│                                                        │
│  ── 前调 ──────────────────────────────────────────    │
│  🍊 佛手柑                                             │
│     明亮清新的开场                                      │
│     ↳ 推荐理由: 呼应粉色系审美中的活力感               │
│                                                        │
│  🌶️ 粉红胡椒                                          │
│     微辣的甜蜜点缀                                      │
│     ↳ 推荐理由: 匹配甜美系风格中的俏皮元素             │
│                                                        │
│  ── 中调 ──────────────────────────────────────────    │
│  🌺 鸢尾花                                             │
│     粉质的优雅花香                                      │
│     ↳ 推荐理由: 连接古典系审美与蓝紫色偏好             │
│                                                        │
│  💐 玫瑰                                               │
│     经典的浪漫花香                                      │
│     ↳ 推荐理由: 呼应约会社交场景的浪漫需求             │
│                                                        │
│  ── 后调 ──────────────────────────────────────────    │
│  🪵 沉香  ✨ NEW                                       │
│     深沉的东方木质                                      │
│     ↳ 推荐理由: 增加神秘感和深度                       │
│                                                        │
│  🌑 乌木  ✨ NEW                                       │
│     烟熏的暗色木质                                      │
│     ↳ 推荐理由: 与粉色系形成反差张力                   │
│                                                        │
│  ── 推荐原因 ──────────────────── [展开 ▾] ──────     │
│  ── 创作灵感 ──────────────────── [展开 ▾] ──────     │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**关键交互**:

1. **香材项**：每个香材显示名称、描述、推荐理由
2. **变更高亮**：被对话修改的香材标注 ✨ NEW，并用高亮颜色/动画标注
3. **展开/收起**：推荐原因和创作灵感默认收起，点击展开
4. **创作灵感**：展开后以引用块样式展示，用斜体排版，营造故事氛围

#### 方案卡片变更动画

当右侧对话区 AI 返回了 `updated_plans` 时：

1. 找到被修改的方案卡片
2. 卡片整体闪烁一次高亮边框（如玫瑰金色光晕）
3. 被修改的香材项：
   - 旧值淡出（200ms）
   - 新值淡入（300ms）+ ✨ 标记
   - 保持高亮 3 秒后恢复正常
4. 推荐原因和故事如果也被修改，自动展开并高亮

```typescript
// 变更动画控制
interface NoteChangeAnimation {
  planId: string;
  changedNotes: string[];  // 被修改的香材名
  timestamp: number;       // 变更时间戳
}

// 3秒后移除高亮
useEffect(() => {
  if (changeAnimation) {
    const timer = setTimeout(() => {
      setChangeAnimation(null);
    }, 3000);
    return () => clearTimeout(timer);
  }
}, [changeAnimation]);
```

### 2.3 右侧：对话区

#### 对话区结构

```
┌─ 对话区 ──────────────────────────────────────────────┐
│                                                        │
│  ┌─ 对话消息列表（可滚动）─────────────────────────┐   │
│  │                                                  │   │
│  │  🤖 助手                                        │   │
│  │  根据您选择的标签，我为您生成了3套香调方案。     │   │
│  │  [10:00]                                        │   │
│  │                                                  │   │
│  │  🧑 你                                          │   │
│  │  方案一的后调能不能换成沉香和乌木？             │   │
│  │  [10:02]                                        │   │
│  │                                                  │   │
│  │  🤖 助手                                        │   │
│  │  好的，我理解你希望增加方案一的深度...           │   │
│  │  [方案一已更新 ✨ 点击查看变更]                  │   │
│  │  [10:02]                                        │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ 输入区 ─────────────────────────────────────────┐  │
│  │ 💬 对这个方案有什么想法...              [发送 →] │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

#### 对话消息类型

```typescript
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  updatedPlans: PlanUpdate[] | null;
  createdAt: string;
}

interface PlanUpdate {
  planId: string;
  name: string;
  // ... 完整方案数据
}
```

**消息渲染规则**:
- **用户消息**: 右对齐，深色背景气泡
- **助手消息**: 左对齐，浅色背景气泡
- **方案更新通知**: 如果 `updatedPlans` 不为空，在消息底部显示一个可点击的标签："方案 X 已更新 ✨"
  - 点击后左侧滚动到对应方案并高亮

#### 输入区交互

```typescript
// 发送消息流程
const handleSend = async () => {
  if (!inputValue.trim() || isSending) return;
  
  // 1. 立即添加用户消息到列表
  addMessage({
    role: 'user',
    content: inputValue,
    createdAt: new Date().toISOString()
  });
  
  // 2. 清空输入框
  setInputValue('');
  setIsSending(true);
  
  // 3. 显示 "AI 正在思考..." 占位
  addTypingIndicator();
  
  try {
    // 4. 调用 API
    const result = await fragranceService.chat(sessionId, inputValue);
    
    // 5. 移除占位，添加 AI 回复
    removeTypingIndicator();
    addMessage({
      role: 'assistant',
      content: result.reply,
      updatedPlans: result.updated_plans,
      createdAt: new Date().toISOString()
    });
    
    // 6. 如果有方案更新，触发左侧更新动画
    if (result.updated_plans) {
      updatePlans(result.updated_plans);
      triggerChangeAnimation(result.updated_plans);
    }
    
  } catch (error) {
    removeTypingIndicator();
    message.error('发送失败，请重试');
  } finally {
    setIsSending(false);
  }
};
```

#### 快捷操作建议

在对话区输入框上方，提供一些快捷操作按钮：

```
[换一种风格] [更浓郁] [更清淡] [适合夏天] [适合约会] [解释选择理由]
```

```typescript
const QUICK_ACTIONS = [
  { label: '换一种风格', message: '能给我换一种完全不同风格的方案吗？' },
  { label: '更浓郁', message: '我觉得整体偏淡，能不能做得更浓郁一些？' },
  { label: '更清淡', message: '有没有更清淡日常的方案？' },
  { label: '适合夏天', message: '如果是夏天使用，需要怎么调整？' },
  { label: '适合约会', message: '如果主要用于约会场景，你会怎么调整？' },
  { label: '解释选择', message: '能详细解释一下每个香材的选择理由吗？' },
];
```

### 2.4 顶部工具栏

```
┌──────────────────────────────────────────────────────────────┐
│  ← 返回标签筛选           香调推荐           [重新生成 ⟳]     │
└──────────────────────────────────────────────────────────────┘
```

- **← 返回标签筛选**: 回到标签筛选页，可以调整标签后重新生成
- **重新生成 ⟳**: 用当前标签重新生成全新方案（确认弹窗："重新生成将清空当前对话历史，确定吗？"）

### 2.5 底部工具栏

```
┌──────────────────────────────────────────────────────────────┐
│  [🔙 返回报告]    [🏷️ 返回标签筛选]    [📋 查看冰山分析]     │
└──────────────────────────────────────────────────────────────┘
```

- **返回报告**: 回到画像报告页
- **返回标签筛选**: 回到标签筛选页
- **查看冰山分析**: 弹出抽屉/弹窗，显示冰山三层分析文字

### 2.6 冰山分析抽屉

```
┌─ 冰山理论分析 ────────────────────────────────────── [×] ──┐
│                                                             │
│  ┌─ 🏔️ 显性行为层（水面之上）────────────────────────────┐  │
│  │                                                       │  │
│  │  甜美系穿搭、粉色系偏好、圈层社交（同好会/茶会）、    │  │
│  │  种草型消费路径，这些指向了一个高度视觉化、注重        │  │
│  │  外在形象表达的用户群体。                              │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ 💭 情感价值层（水面之下）────────────────────────────┐  │
│  │                                                       │  │
│  │  情绪需求驱动的消费动机，拍照出片和约会社交的场景     │  │
│  │  需求，反映了这个群体通过「穿搭-拍照-分享」的闭环     │  │
│  │  来获得自我认同和社交认可...                           │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ 🌊 深层需求（冰山底部）──────────────────────────────┐  │
│  │                                                       │  │
│  │  在亚文化穿搭的表象下，是对「理想化自我」的持续       │  │
│  │  构建。她们通过精致的外在包装来回应内心对美好、       │  │
│  │  浪漫、被重视的渴望...                                │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

使用 Ant Design 的 `Drawer` 组件，从右侧滑出。

---

## 三、数据流

### 3.1 页面初始化

```
进入页面 (带 sessionId 参数)
    ↓
调用 GET /api/v1/fragrance/{sessionId}
    → 获取推荐方案 + 标签
    ↓
调用 GET /api/v1/fragrance/{sessionId}/history
    → 获取对话历史
    ↓
渲染左侧方案 + 右侧对话
```

### 3.2 从标签筛选页跳转

```
标签筛选页点击 "生成香调推荐"
    ↓
调用 POST /api/v1/fragrance/generate
    → 返回 sessionId + 推荐方案
    ↓
跳转到 /recommend/{sessionId}
    → 渲染方案 + 初始对话消息
```

### 3.3 对话修改方案

```
用户输入消息 → 点击发送
    ↓
调用 POST /api/v1/fragrance/{sessionId}/chat
    → 返回 { reply, updated_plans }
    ↓
添加 AI 回复到对话列表
    ↓
如果 updated_plans 不为空:
    → 更新左侧方案状态
    → 触发变更动画
    → 在消息中显示 "方案X已更新" 标签
```

---

## 四、状态管理

### 4.1 Zustand Store

```typescript
// stores/fragranceStore.ts
import { create } from 'zustand';

interface FragranceState {
  // Session 数据
  sessionId: string | null;
  selectedTags: Record<string, Record<string, string[]>> | null;
  
  // 推荐方案
  plans: FragrancePlan[];
  icebergAnalysis: IcebergAnalysis | null;
  
  // 对话
  messages: ChatMessage[];
  isSending: boolean;
  
  // 变更动画
  changeAnimation: NoteChangeAnimation | null;
  
  // Actions
  setSession: (sessionId: string, data: FragranceSessionData) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  updatePlans: (updatedPlans: FragrancePlan[]) => void;
  setIsSending: (isSending: boolean) => void;
  triggerChangeAnimation: (updatedPlans: FragrancePlan[]) => void;
  clearChangeAnimation: () => void;
}

export const useFragranceStore = create<FragranceState>((set, get) => ({
  sessionId: null,
  selectedTags: null,
  plans: [],
  icebergAnalysis: null,
  messages: [],
  isSending: false,
  changeAnimation: null,
  
  setSession: (sessionId, data) => set({
    sessionId,
    selectedTags: data.selectedTags,
    plans: data.recommendations,
    icebergAnalysis: data.icebergAnalysis,
  }),
  
  setMessages: (messages) => set({ messages }),
  
  addMessage: (message) => set(state => ({
    messages: [...state.messages, message]
  })),
  
  updatePlans: (updatedPlans) => set(state => {
    const newPlans = [...state.plans];
    for (const updated of updatedPlans) {
      const idx = newPlans.findIndex(p => p.planId === updated.planId);
      if (idx !== -1) {
        newPlans[idx] = updated;
      }
    }
    return { plans: newPlans };
  }),
  
  setIsSending: (isSending) => set({ isSending }),
  
  triggerChangeAnimation: (updatedPlans) => {
    const changedNoteNames: string[] = [];
    for (const plan of updatedPlans) {
      for (const section of ['topNotes', 'middleNotes', 'baseNotes']) {
        for (const note of (plan as any)[section] || []) {
          if (note.changed) {
            changedNoteNames.push(note.name);
          }
        }
      }
    }
    set({
      changeAnimation: {
        planId: updatedPlans[0]?.planId || '',
        changedNotes: changedNoteNames,
        timestamp: Date.now()
      }
    });
    // 3秒后清除
    setTimeout(() => set({ changeAnimation: null }), 3000);
  },
  
  clearChangeAnimation: () => set({ changeAnimation: null }),
}));
```

---

## 五、TypeScript 类型定义

```typescript
// types/fragrance.ts

export interface FragrancePlan {
  planId: string;
  name: string;
  category: string;
  topNotes: FragranceNote[];
  middleNotes: FragranceNote[];
  baseNotes: FragranceNote[];
  recommendationReason: string;
  fragranceStory: string;
  icebergAnalysis?: IcebergAnalysis;
}

export interface FragranceNote {
  name: string;
  description: string;
  reason: string;
  changed?: boolean;  // 是否被对话修改
}

export interface IcebergAnalysis {
  surface: string;   // 显性行为层
  middle: string;    // 情感价值层
  deep: string;      // 深层需求
}

export interface FragranceSessionData {
  sessionId: string;
  taskId: string;
  selectedTags: Record<string, Record<string, string[]>>;
  recommendations: FragrancePlan[];
  icebergAnalysis: IcebergAnalysis;
  status: string;
  createdAt: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  updatedPlans: FragrancePlan[] | null;
  createdAt: string;
}

export interface ChatResponse {
  reply: string;
  updatedPlans: FragrancePlan[] | null;
  messageId: string;
}

export interface NoteChangeAnimation {
  planId: string;
  changedNotes: string[];
  timestamp: number;
}
```

---

## 六、组件列表

| 组件 | 文件 | 说明 |
|---|---|---|
| `FragranceRecommendPage` | `pages/FragranceRecommend/index.tsx` | 页面容器（双栏布局） |
| **左侧方案区** | | |
| `PlanList` | `pages/FragranceRecommend/PlanList.tsx` | 方案列表容器 |
| `PlanCard` | `pages/FragranceRecommend/PlanCard.tsx` | 单个方案卡片 |
| `NoteSection` | `pages/FragranceRecommend/NoteSection.tsx` | 前/中/后调区块 |
| `NoteItem` | `pages/FragranceRecommend/NoteItem.tsx` | 单个香材项 |
| `ReasonCollapse` | `pages/FragranceRecommend/ReasonCollapse.tsx` | 推荐原因折叠区 |
| `StoryCollapse` | `pages/FragranceRecommend/StoryCollapse.tsx` | 创作灵感折叠区 |
| **右侧对话区** | | |
| `ChatPanel` | `pages/FragranceRecommend/ChatPanel.tsx` | 对话区容器 |
| `MessageList` | `pages/FragranceRecommend/MessageList.tsx` | 消息列表 |
| `MessageBubble` | `pages/FragranceRecommend/MessageBubble.tsx` | 单条消息气泡 |
| `PlanUpdateTag` | `pages/FragranceRecommend/PlanUpdateTag.tsx` | "方案已更新"标签 |
| `ChatInput` | `pages/FragranceRecommend/ChatInput.tsx` | 输入框 |
| `QuickActions` | `pages/FragranceRecommend/QuickActions.tsx` | 快捷操作按钮 |
| `TypingIndicator` | `pages/FragranceRecommend/TypingIndicator.tsx` | AI 正在思考指示器 |
| **弹窗/抽屉** | | |
| `IcebergDrawer` | `pages/FragranceRecommend/IcebergDrawer.tsx` | 冰山分析抽屉 |
| `RegenerateConfirm` | `pages/FragranceRecommend/RegenerateConfirm.tsx` | 重新生成确认弹窗 |

---

## 七、样式设计要点

### 7.1 双栏布局

```css
/* FragranceRecommendPage 布局 */
.recommend-page {
  display: flex;
  height: calc(100vh - 64px - 48px); /* 减去顶栏和底栏 */
}

.plan-panel {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.chat-panel {
  width: 420px;
  min-width: 360px;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.chat-input-area {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px 16px;
}
```

### 7.2 方案卡片样式

```css
.plan-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  transition: border-color 0.3s ease;
}

.plan-card.highlighted {
  border-color: #B76E79;  /* 玫瑰金高亮 */
  box-shadow: 0 0 20px rgba(183, 110, 121, 0.2);
  animation: pulse-border 1s ease-in-out;
}

@keyframes pulse-border {
  0%, 100% { box-shadow: 0 0 20px rgba(183, 110, 121, 0.2); }
  50% { box-shadow: 0 0 30px rgba(183, 110, 121, 0.4); }
}

.plan-card .plan-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.plan-card .plan-category {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 20px;
}
```

### 7.3 香材变更动画

```css
.note-item {
  transition: all 0.3s ease;
}

.note-item.changed {
  background: rgba(183, 110, 121, 0.1);
  border-left: 3px solid #B76E79;
  padding-left: 12px;
  animation: note-fade-in 0.5s ease;
}

.note-item .changed-badge {
  display: inline-block;
  background: linear-gradient(135deg, #B76E79, #C9A96E);
  color: white;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
  animation: badge-pop 0.3s ease;
}

@keyframes note-fade-in {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes badge-pop {
  0% { transform: scale(0); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
```

### 7.4 创作灵感故事样式

```css
.story-content {
  font-style: italic;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.7);
  padding: 16px 20px;
  background: rgba(183, 110, 121, 0.05);
  border-left: 3px solid rgba(183, 110, 121, 0.3);
  border-radius: 0 8px 8px 0;
  font-family: 'Georgia', 'Times New Roman', serif;
}
```

### 7.5 对话气泡样式

```css
.message-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 12px;
  margin-bottom: 12px;
  line-height: 1.6;
}

.message-bubble.user {
  background: linear-gradient(135deg, #B76E79, #9B6B73);
  color: white;
  margin-left: auto;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-bottom-left-radius: 4px;
}

.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 12px 16px;
}

.typing-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  animation: typing-bounce 1.4s infinite ease-in-out;
}

.typing-indicator .dot:nth-child(1) { animation-delay: 0s; }
.typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-8px); }
}
```

---

## 八、API 调用封装

```typescript
// services/fragranceService.ts

export const fragranceService = {
  generate: (data: GenerateRequest): Promise<FragranceSessionData> =>
    api.post('/api/v1/fragrance/generate', data),
  
  getSession: (sessionId: string): Promise<FragranceSessionData> =>
    api.get(`/api/v1/fragrance/${sessionId}`),
  
  chat: (sessionId: string, message: string): Promise<ChatResponse> =>
    api.post(`/api/v1/fragrance/${sessionId}/chat`, { message }),
  
  regenerate: (sessionId: string, data: RegenerateRequest): Promise<FragranceSessionData> =>
    api.post(`/api/v1/fragrance/${sessionId}/regenerate`, data),
  
  getHistory: (sessionId: string): Promise<{ messages: ChatMessage[] }> =>
    api.get(`/api/v1/fragrance/${sessionId}/history`),
};
```

---

## 九、历史记录中的 Part2 展示

从首页历史记录列表点击 [推荐] 按钮时：
- 如果已有 FragranceSession → 直接跳转到 `/recommend/{sessionId}`
- 如果没有 FragranceSession → 跳转到 `/tags/{taskId}` 标签筛选页

历史记录列表中需要显示 Part2 相关状态：

```typescript
interface HistoryItem {
  taskId: string;
  bloggerInfo: { nickname: string; avatarUrl: string };
  analysisLevel: string;
  status: 'completed' | 'failed';
  createdAt: string;
  completedAt: string;
  
  // Part2 关联信息
  hasFragranceSession: boolean;
  fragranceSessionId?: string;
  fragranceSessionCreatedAt?: string;
}
```

---

## 十、待进一步讨论的问题

> [!WARNING]
> 以下问题需要在开发过程中逐步细化。

1. **对话流式输出** — 如果 AI 响应时间较长（>3秒），是否需要实现流式输出（AI 回复逐字显示）？这需要后端配合 SSE 改造
2. **方案导出** — 是否需要支持导出方案（PDF/图片）？预留扩展
3. **方案收藏** — 是否需要收藏/标记某个特别满意的方案？
4. **对话的快捷操作** — 快捷操作按钮的文案是否需要根据当前方案动态生成？
5. **移动端适配** — 双栏布局在移动端需要改为 Tab 切换（方案 Tab / 对话 Tab），具体切换断点待确认
6. **冰山分析可视化** — 除了文字展示，是否需要做一个冰山形状的可视化图表？
