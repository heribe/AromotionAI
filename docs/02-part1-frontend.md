# Part1 前端开发文档 — 用户画像分析

> **文档版本**: v1.0  
> **创建时间**: 2026-06-13  
> **依赖文档**: `00-global-dev-guide.md`, `01-part1-backend.md`

---

## 一、页面概览

Part1 前端包含以下页面/视图:

| 页面 | 路由 | 功能 |
|---|---|---|
| 首页/工作台 | `/` | 新建分析 + 进行中任务 + 历史记录 |
| 任务进度页 | `/task/:taskId` | SSE 实时进度展示 |
| 画像报告页 | `/report/:taskId` | 四维度标签可视化 + 文字报告 |
| 标签筛选页 | `/tags/:taskId` | 标签选择/调整 → 提交到 Part2 |

---

## 二、首页/工作台 (`/`)

### 2.1 页面结构

```
┌──────────────────────────────────────────────────────────┐
│  🧪 AromotionAI                           [Cookie管理]   │  ← 顶部导航栏
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─ 新建分析 ─────────────────────────────────────────┐  │
│  │                                                     │  │
│  │  🔗 请输入博主链接                          [▼ 抖音] │  │
│  │  ┌─────────────────────────────────┐               │  │
│  │  │ https://www.douyin.com/user/... │  [开始分析]   │  │
│  │  └─────────────────────────────────┘               │  │
│  │                                                     │  │
│  │  分析等级: ○ 快速(3-5min)  ● 标准(8-15min)         │  │
│  │           ○ 深度(20-40min) ○ 高级自定义 [展开▾]     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 进行中的任务 ──────────────────────────────────────┐  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ 🔵 xxx的分析 | 标准 | 正在分析视频帧 ████░ 60% │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 历史记录 ──────────────────────────────────────────┐  │
│  │  筛选: [全部▾]  排序: [最新▾]                        │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ ✅ 博主A | 标准 | 06-12 10:00 | [报告] [推荐] │ │  │
│  │  │ ✅ 博主B | 深度 | 06-11 14:00 | [报告] [推荐] │ │  │
│  │  │ ❌ 博主C | 快速 | 06-10 09:00 | Cookie过期     │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │  [1] [2] [3] ... [分页]                             │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 2.2 新建分析区域

**交互流程**:

1. 用户输入博主链接
2. 选择平台（第一版默认抖音，后续支持下拉选择）
3. 选择分析等级（Radio 单选）
   - 如果选"高级自定义"，展开详细配置面板
4. 点击"开始分析"
   - 校验链接格式
   - 校验 Cookie 有效性（如果无效，提示跳转 Cookie 管理）
   - 调用 `POST /api/v1/analysis/create`
   - 创建成功后跳转到任务进度页

**链接格式校验**:
```typescript
// 支持的抖音链接格式
const DOUYIN_URL_PATTERNS = [
  /^https?:\/\/(www\.)?douyin\.com\/user\/.+/,  // 标准用户页
  /^https?:\/\/v\.douyin\.com\/.+/,              // 短链接
];
```

**高级自定义面板** (折叠/展开):

```
┌─ 高级自定义配置 ────────────────────────────────────────┐
│                                                         │
│  📋 帖子选择                                             │
│  热门帖子数量: [3] ▲▼    最近帖子数量: [3] ▲▼           │
│  排序方式: ○ 按点赞  ● 按评论  ○ 按分享                  │
│                                                         │
│  💬 评论采集                                             │
│  每帖评论数: [20] ▲▼     排序: ○ 热门  ○ 最新           │
│  子评论: □ 启用   每条回复数: [5] ▲▼                     │
│                                                         │
│  👥 评论者分析                                           │
│  最多分析: [不限] ▲▼    □ 分析评论者帖子                 │
│  每人帖子数: [3] ▲▼    □ 分析帖子内容  □ 分析视频       │
│                                                         │
│  🖼️ 视觉分析                                            │
│  □ 封面图分析  □ 视频帧分析                              │
│  每视频提取帧: [5] ▲▼   每视频分析帧: [3] ▲▼            │
│  粉丝封面分析: ○ 跳过  ● 组图模式  ○ 逐张分析           │
│  组图大小: [10] ▲▼                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.3 进行中任务列表

- 自动轮询 `GET /api/v1/analysis/list?status=pending,collecting,analyzing`
- 每条显示：博主昵称/头像、分析等级、当前步骤、进度条
- 点击跳转任务进度页
- 轮询间隔：10 秒

### 2.4 历史记录列表

- 调用 `GET /api/v1/analysis/list?page=1&page_size=20`
- 支持按状态筛选（全部/已完成/失败）
- 每条显示：博主昵称/头像、分析等级、完成时间、操作按钮
- 操作按钮：
  - **[报告]** → 跳转画像报告页
  - **[推荐]** → 跳转标签筛选页（如已有推荐结果，直接跳推荐结果页）
  - **[删除]** → 确认弹窗后删除

### 2.5 组件列表

| 组件 | 文件 | 说明 |
|---|---|---|
| `DashboardPage` | `pages/Dashboard/index.tsx` | 页面容器 |
| `NewAnalysisCard` | `pages/Dashboard/NewAnalysisCard.tsx` | 新建分析卡片 |
| `AnalysisLevelSelector` | `pages/Dashboard/AnalysisLevelSelector.tsx` | 分析等级选择器 |
| `CustomConfigPanel` | `pages/Dashboard/CustomConfigPanel.tsx` | 高级自定义面板 |
| `RunningTaskList` | `pages/Dashboard/RunningTaskList.tsx` | 进行中任务列表 |
| `HistoryList` | `pages/Dashboard/HistoryList.tsx` | 历史记录列表 |
| `HistoryItem` | `pages/Dashboard/HistoryItem.tsx` | 历史记录单条 |

---

## 三、任务进度页 (`/task/:taskId`)

### 3.1 页面结构

```
┌──────────────────────────────────────────────────────────┐
│  ← 返回工作台              任务进度                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─ 博主信息 ──────────────────────────────────────────┐  │
│  │  [头像] xxx | 抖音 | 粉丝 12.3万 | 标准分析         │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 总体进度 ──────────────────────────────────────────┐  │
│  │  ████████████████████░░░░░░░░  60%                  │  │
│  │  正在分析视频帧...                                   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 步骤详情 ──────────────────────────────────────────┐  │
│  │  ✅ 1. 博主资料采集      采集成功: xxx, 粉丝12345   │  │
│  │  ✅ 2. 帖子列表采集      共42条帖子, 选取6条分析     │  │
│  │  ✅ 3. 媒体下载          6张封面图 + 6个视频         │  │
│  │  ✅ 4. 评论采集          120条评论, 87个独立评论者   │  │
│  │  🔄 5. 内容分析          正在分析第3/6个视频帧...     │  │
│  │  ⏳ 6. 评论者分析        等待中                      │  │
│  │  ⏳ 7. 标签生成          等待中                      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 实时日志 (可折叠) ─────────────────────────────────┐  │
│  │  [10:05:23] 开始采集博主资料...                      │  │
│  │  [10:05:25] 博主资料采集完成: xxx                    │  │
│  │  [10:05:26] 开始采集帖子列表...                      │  │
│  │  ...                                                │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 3.2 SSE 连接

```typescript
// hooks/useTaskProgress.ts
import { useEffect, useState, useCallback } from 'react';

interface TaskProgress {
  taskId: string;
  status: 'pending' | 'collecting' | 'analyzing' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  subSteps: SubStep[];
  logs: LogEntry[];
}

interface SubStep {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  summary?: string;
}

export function useTaskProgress(taskId: string) {
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(
      `${API_BASE_URL}/api/v1/analysis/${taskId}/progress`
    );

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setProgress(prev => ({
        ...prev,
        ...data,
        logs: prev?.logs || []
      }));
    });

    eventSource.addEventListener('step_complete', (e) => {
      const data = JSON.parse(e.data);
      setProgress(prev => prev ? {
        ...prev,
        logs: [...prev.logs, {
          timestamp: new Date().toISOString(),
          message: `${data.step}: ${data.summary}`
        }]
      } : null);
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      setProgress(prev => prev ? {
        ...prev,
        status: 'completed',
        progress: 100,
      } : null);
      eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
      // EventSource 会自动重连
      // 如果是服务端发送的 error 事件:
      if (e instanceof MessageEvent) {
        setError(JSON.parse(e.data).message);
        eventSource.close();
      }
    });

    return () => eventSource.close();
  }, [taskId]);

  return { progress, error };
}
```

### 3.3 完成后行为

当任务状态变为 `completed` 时：
- 显示"分析完成 ✅"动画
- 2 秒后自动显示"查看报告"按钮
- 点击跳转到画像报告页

当任务状态变为 `failed` 时：
- 显示错误信息
- 如果是 Cookie 过期，显示"前往上传 Cookie"按钮
- 显示"重新分析"按钮

### 3.4 组件列表

| 组件 | 文件 | 说明 |
|---|---|---|
| `TaskProgressPage` | `pages/TaskProgress/index.tsx` | 页面容器 |
| `BloggerInfoCard` | `pages/TaskProgress/BloggerInfoCard.tsx` | 博主信息卡片 |
| `ProgressBar` | `pages/TaskProgress/ProgressBar.tsx` | 总体进度条 |
| `StepList` | `pages/TaskProgress/StepList.tsx` | 步骤详情列表 |
| `StepItem` | `pages/TaskProgress/StepItem.tsx` | 单个步骤 |
| `LogPanel` | `pages/TaskProgress/LogPanel.tsx` | 实时日志面板 |

---

## 四、画像报告页 (`/report/:taskId`)

### 4.1 页面结构

```
┌──────────────────────────────────────────────────────────┐
│  ← 返回     画像报告     [查看文字报告] [前往标签筛选 →]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─ 博主信息 ──────────────────────────────────────────┐  │
│  │  [头像] xxx | 抖音 | 粉丝 12.3万                    │  │
│  │  分析时间: 2026-06-13 10:00 | 等级: 标准             │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 综合画像总结 ──────────────────────────────────────┐  │
│  │  该博主的粉丝群体以年轻女性为主，偏好甜美系和         │  │
│  │  古典系穿搭，消费水平集中在轻奢入门...               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ Tab: [气候消费] [香氛消费] [穿搭香调] [生活场景] ──┐  │
│  │                                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │  🌡️ 气候带    │  │  🏙️ 城市线级  │                │  │
│  │  │  [饼图/环图]  │  │  [饼图/环图]  │                │  │
│  │  │  湿热南方 42% │  │  二线 40%    │                │  │
│  │  │  四季分明 30% │  │  一线 35%    │                │  │
│  │  │  干燥北方 28% │  │  三线 25%    │                │  │
│  │  └──────────────┘  └──────────────┘                │  │
│  │                                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │  🎭 文化圈    │  │  📍 集中度    │                │  │
│  │  │  [饼图/环图]  │  │  全国分散型   │                │  │
│  │  └──────────────┘  └──────────────┘                │  │
│  │                                                     │  │
│  │  💬 总体判断: 粉丝分布全国，以内陆文化圈为主...      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 操作按钮 ──────────────────────────────────────────┐  │
│  │  [前往标签筛选 →]                                    │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 4.2 四维度 Tab 内容

每个 Tab 展示该维度下的所有子维度图表:

**气候-消费带 Tab**:
- 气候带分布（饼图/环图）
- 城市线级分布（饼图/环图）
- 文化圈分布（饼图/环图）
- 地域集中度（文字描述 + 标签）
- 维度总结文字

**香氛消费推断 Tab**:
- 价格带匹配（横向柱状图）
- 消费动机（雷达图）
- 决策路径（饼图）
- 消费频次（饼图）
- 维度总结文字

**穿搭风格-香调映射 Tab**:
- 穿搭风格分布（横向柱状图 — 标签多）
- 穿搭场景（饼图）
- 色彩偏好（带颜色的柱状图）
- 穿搭完整度（饼图）
- 维度总结文字

**生活方式-用香场景 Tab**:
- 核心兴趣（横向柱状图）
- 社交活跃度（饼图）
- 审美性格（雷达图）
- 用香时段（饼图）
- 内容消费特征（饼图）
- 维度总结文字

### 4.3 文字报告弹窗

点击"查看文字报告"按钮后弹出全屏/抽屉式面板：

```
┌──────────────────────────────────────────────────────────┐
│  文字报告                                        [关闭 ×]│
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ## 博主 xxx 粉丝画像                                     │
│                                                          │
│  ### 一、气候-消费带                                      │
│  气候带: 湿热南方 42% | 干燥北方 28% | 四季分明 30%       │
│  城市线级: ...                                            │
│  ...                                                     │
│  **总体判断**: ...                                        │
│                                                          │
│  ### 二、香氛消费推断                                     │
│  ...                                                     │
│                                                          │
│  (Markdown 渲染)                                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

使用 Ant Design 的 `Drawer` 组件，配合 `react-markdown` 渲染 Markdown 内容。

### 4.4 图表配置

推荐使用 `@ant-design/charts` 的以下图表类型：

| 图表类型 | 组件 | 适用场景 |
|---|---|---|
| 环形图 | `Pie` (innerRadius) | 标签数量 ≤5，如气候带、城市线级 |
| 横向柱状图 | `Bar` | 标签数量 >5，如穿搭风格 |
| 雷达图 | `Radar` | 多维度对比，如消费动机、审美性格 |
| 进度条 | `Progress` | 单一占比展示 |

**配色方案**:
使用与香水/调香相关的优雅色系：

```typescript
const CHART_COLORS = [
  '#B76E79',  // 玫瑰金
  '#C9A96E',  // 琥珀金
  '#7B8B6F',  // 苔藓绿
  '#9B8EC4',  // 薰衣草紫
  '#E8A87C',  // 蜜桃橘
  '#D4A5A5',  // 粉玫瑰
  '#6C5B7B',  // 鸢尾紫
  '#355C7D',  // 海洋蓝
  '#F67280',  // 珊瑚红
  '#C06C84',  // 梅红
];
```

### 4.5 组件列表

| 组件 | 文件 | 说明 |
|---|---|---|
| `ProfileReportPage` | `pages/ProfileReport/index.tsx` | 页面容器 |
| `BloggerSummaryCard` | `pages/ProfileReport/BloggerSummaryCard.tsx` | 博主信息 + 综合总结 |
| `DimensionTabs` | `pages/ProfileReport/DimensionTabs.tsx` | 四维度 Tab 容器 |
| `ClimateTab` | `pages/ProfileReport/tabs/ClimateTab.tsx` | 气候消费 Tab |
| `ConsumptionTab` | `pages/ProfileReport/tabs/ConsumptionTab.tsx` | 香氛消费 Tab |
| `FashionTab` | `pages/ProfileReport/tabs/FashionTab.tsx` | 穿搭香调 Tab |
| `LifestyleTab` | `pages/ProfileReport/tabs/LifestyleTab.tsx` | 生活场景 Tab |
| `TagPieChart` | `pages/ProfileReport/charts/TagPieChart.tsx` | 标签饼图通用组件 |
| `TagBarChart` | `pages/ProfileReport/charts/TagBarChart.tsx` | 标签柱状图通用组件 |
| `TagRadarChart` | `pages/ProfileReport/charts/TagRadarChart.tsx` | 标签雷达图通用组件 |
| `FullReportDrawer` | `pages/ProfileReport/FullReportDrawer.tsx` | 文字报告抽屉 |

---

## 五、标签筛选页 (`/tags/:taskId`)

### 5.1 页面结构

```
┌──────────────────────────────────────────────────────────┐
│  ← 返回报告             标签筛选             [生成推荐 →] │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  💡 系统已根据分析结果预选了每个维度的主要标签，          │
│     你可以根据实际需求调整选择。                          │
│                                                          │
│  ┌─ 🌡️ 气候-消费带 ────────────────────────────────────┐  │
│  │                                                     │  │
│  │  气候带 (单选):                                     │  │
│  │  ● 湿热南方 42%  ○ 干燥北方 28%  ○ 四季分明 30%    │  │
│  │                                                     │  │
│  │  城市线级 (可多选):                                  │  │
│  │  ☑ 一线/新一线 35%  ☑ 二线 40%  ☐ 三线及以下 25%   │  │
│  │                                                     │  │
│  │  文化圈暗示 (可多选):                               │  │
│  │  ☐ 日韩影响圈 27%  ☑ 内陆文化圈 45%  ☐ 港台风 28% │  │
│  │                                                     │  │
│  │  地域集中度 (单选):                                  │  │
│  │  ● 全国分散型  ○ 本地型  ○ 核心+辐射               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 💰 香氛消费推断 ───────────────────────────────────┐  │
│  │  ...（同上结构）                                    │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 👗 穿搭风格-香调映射 ──────────────────────────────┐  │
│  │  ...                                                │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 🎯 生活方式-用香场景 ──────────────────────────────┐  │
│  │  ...                                                │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 已选标签预览 ──────────────────────────────────────┐  │
│  │  [湿热南方] [一线/新一线] [二线] [内陆文化圈]        │  │
│  │  [轻奢入门] [情绪需求] [种草型] ...                  │  │
│  │                                                     │  │
│  │  [生成香调推荐 →]                                    │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 5.2 交互规则

1. **数据加载**: 调用 `GET /api/v1/analysis/{taskId}/tags` 获取标签数据
2. **默认选中**: 系统自动选中每个子维度中 `is_default_selected: true` 的标签
3. **互斥标签**: `is_mutually_exclusive: true` 的子维度使用 Radio 单选
4. **非互斥标签**: 使用 Checkbox 多选，受 `max_select` 限制
5. **标签高亮**: 选中的标签高亮显示，显示比例值
6. **已选预览**: 底部实时显示所有已选标签
7. **提交**: 点击"生成香调推荐"调用 `POST /api/v1/fragrance/generate`

### 5.3 标签选择状态管理

```typescript
// types/analysis.ts
interface TagDimension {
  dimensionId: string;
  dimensionName: string;
  subDimensions: TagSubDimension[];
}

interface TagSubDimension {
  subId: string;
  subName: string;
  tags: Tag[];
  isMutuallyExclusive: boolean;
  maxSelect: number | null;
}

interface Tag {
  name: string;
  percentage: number;
  isDefaultSelected: boolean;
}

// stores/tagSelectionStore.ts
interface TagSelectionState {
  dimensions: TagDimension[];
  selections: Record<string, string[]>;  // subId → 选中的标签名列表
  
  setDimensions: (dimensions: TagDimension[]) => void;
  toggleTag: (subId: string, tagName: string) => void;
  getSelectedTags: () => Record<string, string[]>;
  resetToDefault: () => void;
}
```

### 5.4 互斥标签处理

```typescript
// 当用户点击一个互斥组内的标签
const handleTagClick = (subId: string, tagName: string) => {
  const subDimension = getSubDimension(subId);
  
  if (subDimension.isMutuallyExclusive) {
    // 互斥：替换选择
    setSelection(subId, [tagName]);
  } else if (subDimension.maxSelect) {
    // 有数量限制
    const current = selections[subId] || [];
    if (current.includes(tagName)) {
      setSelection(subId, current.filter(t => t !== tagName));
    } else if (current.length < subDimension.maxSelect) {
      setSelection(subId, [...current, tagName]);
    } else {
      message.warning(`最多只能选择 ${subDimension.maxSelect} 个`);
    }
  } else {
    // 无限制：自由勾选
    const current = selections[subId] || [];
    if (current.includes(tagName)) {
      setSelection(subId, current.filter(t => t !== tagName));
    } else {
      setSelection(subId, [...current, tagName]);
    }
  }
};
```

### 5.5 组件列表

| 组件 | 文件 | 说明 |
|---|---|---|
| `TagSelectionPage` | `pages/TagSelection/index.tsx` | 页面容器 |
| `DimensionSection` | `pages/TagSelection/DimensionSection.tsx` | 单个维度区块 |
| `SubDimensionGroup` | `pages/TagSelection/SubDimensionGroup.tsx` | 子维度标签组 |
| `TagRadioGroup` | `pages/TagSelection/TagRadioGroup.tsx` | 互斥标签（Radio） |
| `TagCheckboxGroup` | `pages/TagSelection/TagCheckboxGroup.tsx` | 非互斥标签（Checkbox） |
| `SelectedTagsPreview` | `pages/TagSelection/SelectedTagsPreview.tsx` | 已选标签预览 |

---

## 六、公共组件

### 6.1 布局组件

```typescript
// components/Layout/AppLayout.tsx
// 整体布局: 顶部导航 + 内容区
// 使用 Ant Design 的 Layout 组件

interface AppLayoutProps {
  children: React.ReactNode;
}
```

**顶部导航栏**:
- Logo + 产品名 "AromotionAI"
- 右侧: Cookie 管理按钮（带状态指示灯 🟢/🔴）

### 6.2 Cookie 管理组件

使用 Ant Design 的 `Modal` 弹窗，不是独立页面：

```
┌─ Cookie 管理 ──────────────────────────────────────────┐
│                                                         │
│  平台         状态          操作                         │
│  ─────────────────────────────────────────              │
│  抖音         🟢 有效       [重新上传] [删除]            │
│               上传于: 06-12  检测于: 06-13 09:00        │
│  ─────────────────────────────────────────              │
│  淘宝         🔴 过期       [上传]                       │
│  ─────────────────────────────────────────              │
│  小红书       ⚪ 未上传      [上传]                      │
│                                                         │
│  上传说明: 请使用浏览器扩展导出 Cookie JSON 文件          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 6.3 通用组件

| 组件 | 用途 |
|---|---|
| `LoadingSpinner` | 全局加载动画 |
| `ErrorBoundary` | 错误边界 |
| `EmptyState` | 空状态提示 |
| `ConfirmModal` | 确认弹窗 |

---

## 七、路由配置

```typescript
// router.tsx
import { createBrowserRouter } from 'react-router-dom';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'task/:taskId', element: <TaskProgressPage /> },
      { path: 'report/:taskId', element: <ProfileReportPage /> },
      { path: 'tags/:taskId', element: <TagSelectionPage /> },
      { path: 'recommend/:sessionId', element: <FragranceRecommendPage /> },  // Part2
    ]
  }
]);
```

---

## 八、状态管理

```typescript
// stores/analysisStore.ts (Zustand)
import { create } from 'zustand';

interface AnalysisStore {
  // 当前任务
  currentTask: AnalysisTask | null;
  setCurrentTask: (task: AnalysisTask) => void;
  
  // 任务列表
  taskList: AnalysisTask[];
  fetchTaskList: (page?: number) => Promise<void>;
  
  // 报告数据
  currentReport: ProfileReport | null;
  fetchReport: (taskId: string) => Promise<void>;
  
  // Cookie 状态
  cookieStatus: CookieStatus[];
  fetchCookieStatus: () => Promise<void>;
}
```

---

## 九、API 调用封装

```typescript
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 统一响应处理
api.interceptors.response.use(
  (response) => {
    const { code, message, data } = response.data;
    if (code !== 0) {
      // 业务错误
      throw new ApiError(code, message);
    }
    return data;
  },
  (error) => {
    // 网络错误
    throw new NetworkError(error.message);
  }
);

// services/analysisService.ts
export const analysisService = {
  create: (data: CreateAnalysisRequest) => api.post('/api/v1/analysis/create', data),
  getDetail: (taskId: string) => api.get(`/api/v1/analysis/${taskId}`),
  getReport: (taskId: string) => api.get(`/api/v1/analysis/${taskId}/report`),
  getTags: (taskId: string) => api.get(`/api/v1/analysis/${taskId}/tags`),
  getList: (params: ListParams) => api.get('/api/v1/analysis/list', { params }),
  delete: (taskId: string) => api.delete(`/api/v1/analysis/${taskId}`),
};
```

---

## 十、样式设计要点

### 10.1 设计语言

- **主题**: 自然、匠人、带有高端调香实验室的温润质感 (Natural Artisan Ledger)
- **主色调**: 浅冷石灰/陶瓷背景 + 深苔藓绿/炭灰文字 + 琥珀色点缀
- **字体**: 使用 Google Fonts 的 Inter（英文）与优雅的衬线体（标题/强调），中文回退系统黑体/宋体
- **卡片**: 摒弃传统的厚重卡片与发光阴影，采用极细的实线边框 (1px) 和大面积留白，模拟纸质配方账本
- **动画**: 极简、克制，避免发光特效和复杂微动效，状态切换自然干脆

### 10.2 Ant Design 主题定制

```typescript
// App.tsx
import { ConfigProvider } from 'antd';

<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#8B6A47',      // 琥珀色 (Amber)
      colorSuccess: '#4A5D4E',      // 深苔藓绿 (Moss Green)
      colorWarning: '#B8860B',      // 暖金
      colorError: '#A0522D',        // 赤褐
      colorBgContainer: '#F9F9F9',  // 浅陶瓷灰/试香纸背景
      borderRadius: 4,              // 极小圆角，偏硬朗纸质感
      colorText: '#2F3330',         // 炭灰文字
      colorBorder: '#E0E0E0',       // 极细的浅色分割线
      fontFamily: "'Inter', 'Georgia', serif, -apple-system, sans-serif",
    },
  }}
>
```

### 10.3 响应式断点

```css
/* 适配不同屏幕 */
@media (max-width: 768px)  { /* 移动端 */ }
@media (max-width: 1024px) { /* 平板 */ }
@media (min-width: 1025px) { /* 桌面 */ }
```

---

## 十一、待进一步讨论的问题

1. **自定义标签输入** — 是否允许调香师在标签筛选页输入自定义标签（不在预设标签体系内的），如"特定品牌偏好"
2. **图表交互** — 图表是否需要点击交互（如点击某个标签显示详细信息）
3. **报告页的图片展示** — 是否在报告页展示采集到的封面图/视频帧（让调香师看到原始图片）
4. **暗色/亮色主题切换** — 是否需要支持切换
