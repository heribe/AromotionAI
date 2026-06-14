/**
 * Mock 数据层 — 所有 Mock 数据集中管理
 * 
 * ★ 切换到后端的方式：
 *   将每个 export 函数中的 setTimeout 逻辑替换为真实的 axios 调用即可。
 *   数据结构完全对齐后端 API，无需修改组件代码。
 */

import type {
  AnalysisTask,
  ProfileReport,
  TagDimension,
  CreateAnalysisRequest,
} from '../types/analysis';

// ========== 延迟模拟 ==========
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ========== 任务列表 Mock ==========
const MOCK_TASKS: AnalysisTask[] = [
  {
    taskId: 'task-001',
    bloggerName: '花间调香师',
    platform: '抖音',
    analysisLevel: '标准',
    status: 'completed',
    progress: 100,
    createdAt: '2026-06-12 10:00',
    completedAt: '2026-06-12 10:12',
  },
  {
    taskId: 'task-002',
    bloggerName: '木质香调实验室',
    platform: '抖音',
    analysisLevel: '深度',
    status: 'waiting_tags',
    progress: 50,
    currentStep: '待筛选标签',
    createdAt: '2026-06-13 09:30',
  },
  {
    taskId: 'task-003',
    bloggerName: '柑橘控的日常',
    platform: '抖音',
    analysisLevel: '快速',
    status: 'pending',
    progress: 0,
    currentStep: '排队中',
    createdAt: '2026-06-14 08:00',
  },
  {
    taskId: 'task-004',
    bloggerName: '沙龙香入坑指南',
    platform: '抖音',
    analysisLevel: '标准',
    status: 'completed',
    progress: 100,
    createdAt: '2026-06-11 14:20',
    completedAt: '2026-06-11 14:35',
  },
  {
    taskId: 'task-005',
    bloggerName: '东方香调鉴赏',
    platform: '抖音',
    analysisLevel: '深度',
    status: 'failed',
    progress: 45,
    currentStep: 'Cookie 已过期',
    errorMessage: '抖音 Cookie 已过期，请重新上传',
    createdAt: '2026-06-10 16:00',
  },
];

// ========== 画像报告 Mock ==========
const MOCK_REPORT: ProfileReport = {
  taskId: 'task-001',
  bloggerName: '花间调香师',
  bloggerAvatar: '',
  platform: '抖音',
  followerCount: '12.3万',
  analysisLevel: '标准',
  analysisTime: '2026-06-12 10:12',
  overallSummary: '该博主的粉丝群体以 22-30 岁的年轻女性为主，集中在一线和新一线城市，偏好甜美清新的花果调，消费水平集中在轻奢入门(300-600 元)，决策路径以社交种草为主。穿搭风格偏向法式优雅和日系文艺。',
  dimensions: [
    {
      dimensionId: 'climate',
      dimensionName: '气候-消费带',
      icon: '🌡️',
      subDimensions: [
        {
          subId: 'climate-zone',
          subName: '气候带',
          chartType: 'pie',
          data: [
            { name: '湿热南方', value: 42 },
            { name: '四季分明', value: 30 },
            { name: '干燥北方', value: 28 },
          ],
        },
        {
          subId: 'city-tier',
          subName: '城市线级',
          chartType: 'pie',
          data: [
            { name: '一线/新一线', value: 35 },
            { name: '二线', value: 40 },
            { name: '三线及以下', value: 25 },
          ],
        },
        {
          subId: 'culture-zone',
          subName: '文化圈',
          chartType: 'pie',
          data: [
            { name: '内陆文化圈', value: 45 },
            { name: '港台风', value: 28 },
            { name: '日韩影响圈', value: 27 },
          ],
        },
        {
          subId: 'concentration',
          subName: '地域集中度',
          chartType: 'text',
          data: [
            { name: '全国分散型', value: 100 },
          ],
          summary: '粉丝分布全国各地，无明显地域聚集，属于典型的全国分散型分布。',
        },
      ],
      overallSummary: '粉丝分布全国各地，以内陆文化圈为主（45%），偏好四季分明到湿热南方的气候区域。城市分布以二线城市为主力（40%），一线城市紧随其后。整体来看，该博主的受众具有较强的跨地域影响力。',
    },
    {
      dimensionId: 'consumption',
      dimensionName: '香氛消费推断',
      icon: '💰',
      subDimensions: [
        {
          subId: 'price-range',
          subName: '价格带匹配',
          chartType: 'bar',
          data: [
            { name: '入门平价 (100以下)', value: 15 },
            { name: '大众消费 (100-300)', value: 25 },
            { name: '轻奢入门 (300-600)', value: 35 },
            { name: '中高端 (600-1200)', value: 18 },
            { name: '奢侈品 (1200+)', value: 7 },
          ],
        },
        {
          subId: 'motivation',
          subName: '消费动机',
          chartType: 'radar',
          data: [
            { name: '情绪需求', value: 85 },
            { name: '社交需求', value: 72 },
            { name: '品质追求', value: 68 },
            { name: '身份认同', value: 45 },
            { name: '功能性需求', value: 30 },
          ],
        },
        {
          subId: 'decision-path',
          subName: '决策路径',
          chartType: 'pie',
          data: [
            { name: '种草型', value: 42 },
            { name: '冲动型', value: 25 },
            { name: '研究型', value: 20 },
            { name: '忠诚型', value: 13 },
          ],
        },
        {
          subId: 'frequency',
          subName: '消费频次',
          chartType: 'pie',
          data: [
            { name: '月均1-2次', value: 38 },
            { name: '季度性', value: 32 },
            { name: '偶尔尝鲜', value: 20 },
            { name: '高频复购', value: 10 },
          ],
        },
      ],
      overallSummary: '消费水平集中在轻奢入门段（300-600元，占比35%），消费动机以情绪需求和社交需求为主导。决策路径以种草型为主（42%），说明 KOL 推荐对该群体有极强影响力。',
    },
    {
      dimensionId: 'fashion',
      dimensionName: '穿搭风格-香调映射',
      icon: '👗',
      subDimensions: [
        {
          subId: 'fashion-style',
          subName: '穿搭风格',
          chartType: 'bar',
          data: [
            { name: '法式优雅', value: 28 },
            { name: '日系文艺', value: 22 },
            { name: '韩系简约', value: 18 },
            { name: '都市通勤', value: 15 },
            { name: '甜酷混搭', value: 10 },
            { name: '古典中式', value: 7 },
          ],
        },
        {
          subId: 'fashion-scene',
          subName: '穿搭场景',
          chartType: 'pie',
          data: [
            { name: '日常休闲', value: 40 },
            { name: '办公通勤', value: 30 },
            { name: '约会社交', value: 20 },
            { name: '户外运动', value: 10 },
          ],
        },
        {
          subId: 'color-preference',
          subName: '色彩偏好',
          chartType: 'bar',
          data: [
            { name: '莫兰迪色', value: 30, color: '#B8AFA6' },
            { name: '奶油白', value: 25, color: '#F5F0E8' },
            { name: '雾霾蓝', value: 18, color: '#8CA9BF' },
            { name: '烟玫瑰', value: 15, color: '#C9A0A0' },
            { name: '黑灰', value: 12, color: '#555555' },
          ],
        },
        {
          subId: 'fashion-completeness',
          subName: '穿搭完整度',
          chartType: 'pie',
          data: [
            { name: '精致完整型', value: 45 },
            { name: '基础搭配型', value: 35 },
            { name: '随性自然型', value: 20 },
          ],
        },
      ],
      overallSummary: '穿搭以法式优雅（28%）和日系文艺（22%）为主导，色彩偏好莫兰迪色系和奶油白，整体审美倾向温柔、知性。在香调映射上，建议偏向花香调、粉香调以及清新的绿叶调。',
    },
    {
      dimensionId: 'lifestyle',
      dimensionName: '生活方式-用香场景',
      icon: '🎯',
      subDimensions: [
        {
          subId: 'core-interest',
          subName: '核心兴趣',
          chartType: 'bar',
          data: [
            { name: '美妆护肤', value: 85 },
            { name: '穿搭时尚', value: 72 },
            { name: '摄影探店', value: 55 },
            { name: '烘焙美食', value: 42 },
            { name: '阅读文艺', value: 38 },
            { name: '瑜伽健身', value: 25 },
          ],
        },
        {
          subId: 'social-activity',
          subName: '社交活跃度',
          chartType: 'pie',
          data: [
            { name: '社交达人', value: 35 },
            { name: '圈层社交', value: 40 },
            { name: '安静内向', value: 25 },
          ],
        },
        {
          subId: 'aesthetic-personality',
          subName: '审美性格',
          chartType: 'radar',
          data: [
            { name: '浪漫感性', value: 88 },
            { name: '独立自信', value: 72 },
            { name: '细腻敏锐', value: 80 },
            { name: '冒险尝鲜', value: 45 },
            { name: '极简克制', value: 35 },
          ],
        },
        {
          subId: 'fragrance-timing',
          subName: '用香时段',
          chartType: 'pie',
          data: [
            { name: '日间通勤', value: 40 },
            { name: '晚间社交', value: 30 },
            { name: '居家放松', value: 20 },
            { name: '特殊场合', value: 10 },
          ],
        },
        {
          subId: 'content-consumption',
          subName: '内容消费特征',
          chartType: 'pie',
          data: [
            { name: '视觉导向', value: 45 },
            { name: '故事导向', value: 30 },
            { name: '知识导向', value: 15 },
            { name: '互动导向', value: 10 },
          ],
        },
      ],
      overallSummary: '核心兴趣集中在美妆护肤和穿搭时尚，审美性格偏向浪漫感性和细腻敏锐。社交模式以圈层社交为主（40%），用香时段集中在日间通勤。内容消费以视觉导向为主，说明香水的包装设计和视觉呈现对该群体有重要影响。',
    },
  ],
  fullReportMarkdown: `# 博主「花间调香师」粉丝画像分析报告

## 一、气候-消费带

### 气候带分布
- 湿热南方: 42%
- 四季分明: 30%
- 干燥北方: 28%

### 城市线级
- 一线/新一线: 35%
- 二线城市: 40%
- 三线及以下: 25%

**总体判断**: 粉丝分布全国各地，以内陆文化圈为主（45%），城市分布以二线城市为主力。

## 二、香氛消费推断

### 价格带
消费水平集中在轻奢入门段（300-600元），占比35%。

### 消费动机
情绪需求（85%）和社交需求（72%）是最主要的消费驱动力。

### 决策路径
种草型决策占42%，说明 KOL 推荐对该群体影响力极强。

## 三、穿搭风格-香调映射

穿搭以法式优雅（28%）和日系文艺（22%）为主导。色彩偏好以莫兰迪色系和奶油白为主，审美整体偏向温柔知性。

**香调建议**: 花香调、粉香调、清新绿叶调

## 四、生活方式-用香场景

核心兴趣集中在美妆护肤和穿搭时尚。审美性格偏向浪漫感性（88%）和细腻敏锐（80%）。用香时段以日间通勤为主（40%），内容消费以视觉导向为主。
`,
};

// ========== 标签筛选 Mock ==========
const MOCK_TAGS: TagDimension[] = [
  {
    dimensionId: 'climate',
    dimensionName: '气候-消费带',
    icon: '🌡️',
    subDimensions: [
      {
        subId: 'climate-zone',
        subName: '气候带',
        tags: [
          { name: '湿热南方', percentage: 42, isDefaultSelected: true },
          { name: '干燥北方', percentage: 28, isDefaultSelected: false },
          { name: '四季分明', percentage: 30, isDefaultSelected: false },
        ],
        isMutuallyExclusive: true,
        maxSelect: null,
      },
      {
        subId: 'city-tier',
        subName: '城市线级',
        tags: [
          { name: '一线/新一线', percentage: 35, isDefaultSelected: true },
          { name: '二线', percentage: 40, isDefaultSelected: true },
          { name: '三线及以下', percentage: 25, isDefaultSelected: false },
        ],
        isMutuallyExclusive: false,
        maxSelect: null,
      },
      {
        subId: 'culture-zone',
        subName: '文化圈暗示',
        tags: [
          { name: '日韩影响圈', percentage: 27, isDefaultSelected: false },
          { name: '内陆文化圈', percentage: 45, isDefaultSelected: true },
          { name: '港台风', percentage: 28, isDefaultSelected: false },
        ],
        isMutuallyExclusive: false,
        maxSelect: 2,
      },
      {
        subId: 'concentration',
        subName: '地域集中度',
        tags: [
          { name: '全国分散型', percentage: 100, isDefaultSelected: true },
          { name: '本地型', percentage: 0, isDefaultSelected: false },
          { name: '核心+辐射', percentage: 0, isDefaultSelected: false },
        ],
        isMutuallyExclusive: true,
        maxSelect: null,
      },
    ],
  },
  {
    dimensionId: 'consumption',
    dimensionName: '香氛消费推断',
    icon: '💰',
    subDimensions: [
      {
        subId: 'price-range',
        subName: '价格带匹配',
        tags: [
          { name: '入门平价', percentage: 15, isDefaultSelected: false },
          { name: '大众消费', percentage: 25, isDefaultSelected: false },
          { name: '轻奢入门', percentage: 35, isDefaultSelected: true },
          { name: '中高端', percentage: 18, isDefaultSelected: false },
          { name: '奢侈品', percentage: 7, isDefaultSelected: false },
        ],
        isMutuallyExclusive: true,
        maxSelect: null,
      },
      {
        subId: 'motivation',
        subName: '消费动机',
        tags: [
          { name: '情绪需求', percentage: 85, isDefaultSelected: true },
          { name: '社交需求', percentage: 72, isDefaultSelected: true },
          { name: '品质追求', percentage: 68, isDefaultSelected: false },
          { name: '身份认同', percentage: 45, isDefaultSelected: false },
          { name: '功能性需求', percentage: 30, isDefaultSelected: false },
        ],
        isMutuallyExclusive: false,
        maxSelect: 3,
      },
      {
        subId: 'decision-path',
        subName: '决策路径',
        tags: [
          { name: '种草型', percentage: 42, isDefaultSelected: true },
          { name: '冲动型', percentage: 25, isDefaultSelected: false },
          { name: '研究型', percentage: 20, isDefaultSelected: false },
          { name: '忠诚型', percentage: 13, isDefaultSelected: false },
        ],
        isMutuallyExclusive: true,
        maxSelect: null,
      },
    ],
  },
  {
    dimensionId: 'fashion',
    dimensionName: '穿搭风格-香调映射',
    icon: '👗',
    subDimensions: [
      {
        subId: 'fashion-style',
        subName: '穿搭风格',
        tags: [
          { name: '法式优雅', percentage: 28, isDefaultSelected: true },
          { name: '日系文艺', percentage: 22, isDefaultSelected: true },
          { name: '韩系简约', percentage: 18, isDefaultSelected: false },
          { name: '都市通勤', percentage: 15, isDefaultSelected: false },
          { name: '甜酷混搭', percentage: 10, isDefaultSelected: false },
          { name: '古典中式', percentage: 7, isDefaultSelected: false },
        ],
        isMutuallyExclusive: false,
        maxSelect: 3,
      },
      {
        subId: 'color-preference',
        subName: '色彩偏好',
        tags: [
          { name: '莫兰迪色', percentage: 30, isDefaultSelected: true },
          { name: '奶油白', percentage: 25, isDefaultSelected: true },
          { name: '雾霾蓝', percentage: 18, isDefaultSelected: false },
          { name: '烟玫瑰', percentage: 15, isDefaultSelected: false },
          { name: '黑灰', percentage: 12, isDefaultSelected: false },
        ],
        isMutuallyExclusive: false,
        maxSelect: 3,
      },
    ],
  },
  {
    dimensionId: 'lifestyle',
    dimensionName: '生活方式-用香场景',
    icon: '🎯',
    subDimensions: [
      {
        subId: 'core-interest',
        subName: '核心兴趣',
        tags: [
          { name: '美妆护肤', percentage: 85, isDefaultSelected: true },
          { name: '穿搭时尚', percentage: 72, isDefaultSelected: true },
          { name: '摄影探店', percentage: 55, isDefaultSelected: false },
          { name: '烘焙美食', percentage: 42, isDefaultSelected: false },
          { name: '阅读文艺', percentage: 38, isDefaultSelected: false },
          { name: '瑜伽健身', percentage: 25, isDefaultSelected: false },
        ],
        isMutuallyExclusive: false,
        maxSelect: 3,
      },
      {
        subId: 'fragrance-timing',
        subName: '用香时段',
        tags: [
          { name: '日间通勤', percentage: 40, isDefaultSelected: true },
          { name: '晚间社交', percentage: 30, isDefaultSelected: false },
          { name: '居家放松', percentage: 20, isDefaultSelected: false },
          { name: '特殊场合', percentage: 10, isDefaultSelected: false },
        ],
        isMutuallyExclusive: true,
        maxSelect: null,
      },
    ],
  },
];

// ========== API 服务函数 ==========
// ★ 切换到后端时，只需把这些函数体替换为 axios 调用

export const mockApi = {
  /** 获取任务列表 */
  async getTaskList(): Promise<AnalysisTask[]> {
    await delay(300);
    return MOCK_TASKS;
  },

  /** 获取画像报告 */
  async getReport(taskId: string): Promise<ProfileReport> {
    await delay(500);
    return { ...MOCK_REPORT, taskId };
  },

  /** 获取标签数据 */
  async getTags(taskId: string): Promise<TagDimension[]> {
    await delay(300);
    void taskId; // 未来会使用
    return MOCK_TAGS;
  },

  /** 创建分析任务 */
  async createTask(req: CreateAnalysisRequest): Promise<{ taskId: string }> {
    await delay(800);
    void req;
    return { taskId: 'task-new-' + Date.now() };
  },
};
