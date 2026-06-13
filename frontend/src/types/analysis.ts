/**
 * Part 1: 用户画像分析 — 全局类型定义
 * 严格对齐 docs/02-part1-frontend.md 的 API 数据结构
 */

// ========== 任务相关 ==========
export type TaskStatus = 'pending' | 'collecting' | 'analyzing' | 'waiting_tags' | 'processing' | 'completed' | 'failed';

export interface AnalysisTask {
  taskId: string;
  bloggerName: string;
  bloggerAvatar?: string;
  platform: string;
  analysisLevel: '快速' | '标准' | '深度' | '高级自定义';
  status: TaskStatus;
  progress: number;            // 0-100
  currentStep?: string;
  createdAt: string;
  completedAt?: string;
  errorMessage?: string;
}

// ========== 画像报告相关 ==========

/** 单个子维度的图表数据项 */
export interface ChartDataItem {
  name: string;
  value: number;     // 百分比 (0-100) 或计数
  color?: string;    // 可选的自定义颜色
}

/** 子维度 */
export interface SubDimension {
  subId: string;
  subName: string;
  chartType: 'pie' | 'bar' | 'radar' | 'text';
  data: ChartDataItem[];
  summary?: string;           // 子维度的文字小结
}

/** 主维度 */
export interface Dimension {
  dimensionId: string;
  dimensionName: string;
  icon: string;               // emoji 或 icon key
  subDimensions: SubDimension[];
  overallSummary: string;     // 维度总结文字
}

/** 完整画像报告 */
export interface ProfileReport {
  taskId: string;
  bloggerName: string;
  bloggerAvatar?: string;
  platform: string;
  followerCount: string;      // "12.3万"
  analysisLevel: string;
  analysisTime: string;       // "2026-06-13 10:00"
  overallSummary: string;     // 综合画像总结
  dimensions: Dimension[];
  fullReportMarkdown: string; // 完整的 Markdown 文字报告
}

// ========== 标签筛选相关 ==========

export interface Tag {
  name: string;
  percentage: number;         // 0-100
  isDefaultSelected: boolean;
}

export interface TagSubDimension {
  subId: string;
  subName: string;
  tags: Tag[];
  isMutuallyExclusive: boolean;
  maxSelect: number | null;   // null = 无限制
}

export interface TagDimension {
  dimensionId: string;
  dimensionName: string;
  icon: string;
  subDimensions: TagSubDimension[];
}

// ========== 创建分析请求 ==========
export interface CreateAnalysisRequest {
  bloggerUrl: string;
  platform: string;
  analysisLevel: string;
  customConfig?: {
    hotPostCount?: number;
    recentPostCount?: number;
    sortBy?: string;
    commentsPerPost?: number;
    commentSort?: string;
    enableSubComments?: boolean;
    subCommentsPerComment?: number;
    maxCommenterAnalysis?: number;
    analyzeCommenterPosts?: boolean;
    commenterPostCount?: number;
    analyzeCoverImages?: boolean;
    analyzeVideoFrames?: boolean;
    framesPerVideo?: number;
    analyzedFramesPerVideo?: number;
    fanCoverAnalysis?: string;
    collageSize?: number;
  };
}
