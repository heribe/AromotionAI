/**
 * 适配层 — 后端响应（snake_case + 信封解包后的纯数据）↔ 前端 types（camelCase）
 *
 * 后端契约来源：backend/app/schemas/*.py（Pydantic 模型）。
 * 前端契约来源：frontend/src/types/*.ts。
 *
 * 设计原则：所有后端响应在 api.ts 调用后、进入 store 前，经此处转换为前端 types。
 * 反向（前端→后端请求体）的转换放在 api.ts 内就近处理。
 */
import type {
  AnalysisTask,
  TaskStatus,
  CreateAnalysisRequest,
  ProfileReport,
  Dimension,
  SubDimension,
  ChartDataItem,
  TagDimension,
} from '../types/analysis';
import type {
  FragranceNote,
  IcebergAnalysis,
  FragrancePlan,
  ChatMessage,
} from '../types/fragrance';

// =====================================================================
// 后端响应类型（与 Pydantic schema 字段对齐，仅声明用到的字段）
// =====================================================================

export interface BackendBloggerInfo {
  nickname: string | null;
  avatar_url: string | null;
  follower_count: number | null;
  platform: string | null;
}

export interface BackendAnalysisListItem {
  task_id: string;
  platform: string;
  blogger_info: BackendBloggerInfo | null;
  analysis_level: string;
  status: string;
  progress: number;
  created_at: string;
  completed_at: string | null;
  has_fragrance_session?: boolean;
  session_id?: string | null;
}

export interface BackendAnalysisTaskDetail extends BackendAnalysisListItem {
  blogger_url: string;
  current_step: string;
  blogger_info: BackendBloggerInfo | null;
  custom_config: Record<string, unknown> | null;
  updated_at: string;
  completed_at: string | null;
  error_message: string | null;
}

// =====================================================================
// 字段映射常量
// =====================================================================

/** 后端 analysis_level ↔ 前端中文标签 */
const LEVEL_TO_CN: Record<string, AnalysisTask['analysisLevel']> = {
  quick: '快速',
  standard: '标准',
  deep: '深度',
  custom: '高级自定义',
};
const CN_TO_LEVEL: Record<string, string> = Object.entries(LEVEL_TO_CN).reduce(
  (acc, [en, cn]) => {
    acc[cn] = en;
    return acc;
  },
  {} as Record<string, string>,
);

/** 后端 status（字符串）→ 前端 TaskStatus */
function normalizeStatus(s: string): TaskStatus {
  // 后端实际写入的：pending/collecting/analyzing/completed/failed/cancelled
  // 前端类型含 waiting_tags/processing（后端当前不写，但保留兼容）
  const known: TaskStatus[] = [
    'pending',
    'collecting',
    'analyzing',
    'waiting_tags',
    'processing',
    'completed',
    'failed',
    'cancelled',
  ];
  return (known.includes(s as TaskStatus) ? s : 'failed') as TaskStatus;
}

/** 后端 ISO 时间 → 前端展示格式 "2026-06-12 10:00"（兼容已是字符串的输入） */
function formatTime(iso: string | null | undefined): string | undefined {
  if (!iso) return undefined;
  // 后端返回形如 "2026-06-12T10:00:00+00:00" 或 naive "2026-06-12T10:00:00"
  // 前端 mock 用的是 "2026-06-12 10:00"，这里取前 16 位并把 T 换成空格
  const s = iso.replace('T', ' ');
  return s.slice(0, 16);
}

// =====================================================================
// 任务相关适配（后端 → 前端）
// =====================================================================

/** 后端任务列表项 → 前端 AnalysisTask */
export function toAnalysisTask(item: BackendAnalysisListItem): AnalysisTask {
  const blogger = item.blogger_info;
  return {
    taskId: item.task_id,
    bloggerName: blogger?.nickname ?? '未知博主',
    bloggerAvatar: blogger?.avatar_url ?? undefined,
    platform: mapPlatformLabel(blogger?.platform ?? item.platform),
    analysisLevel: LEVEL_TO_CN[item.analysis_level] ?? '标准',
    status: normalizeStatus(item.status),
    progress: item.progress ?? 0,
    createdAt: formatTime(item.created_at) ?? item.created_at,
    completedAt: formatTime(item.completed_at),
    sessionId: item.session_id ?? null,
  };
}

/** 后端任务详情 → 前端 AnalysisTask（含 currentStep / errorMessage） */
export function toAnalysisTaskDetail(d: BackendAnalysisTaskDetail): AnalysisTask {
  return {
    ...toAnalysisTask(d),
    currentStep: d.current_step ?? undefined,
    errorMessage: d.error_message ?? undefined,
  };
}

// =====================================================================
// 平台标签适配
// =====================================================================

const PLATFORM_LABEL: Record<string, string> = {
  douyin: '抖音',
  xiaohongshu: '小红书',
  taobao: '淘宝',
};

function mapPlatformLabel(p: string): string {
  return PLATFORM_LABEL[p] ?? p;
}

// =====================================================================
// 请求适配（前端 → 后端）
// =====================================================================

export interface BackendCreateAnalysisRequest {
  blogger_url: string;
  platform: string;
  analysis_level: string;
  custom_config: Record<string, unknown> | null;
}

/** 前端 CreateAnalysisRequest → 后端 body */
export function fromCreateAnalysisRequest(
  req: CreateAnalysisRequest,
): BackendCreateAnalysisRequest {
  return {
    blogger_url: req.bloggerUrl,
    platform: req.platform || 'auto',
    analysis_level: CN_TO_LEVEL[req.analysisLevel] ?? 'standard',
    custom_config: req.customConfig ?? null,
  };
}

// =====================================================================
// 画像报告适配（后端 → 前端）
// =====================================================================
//
// 后端 GET /analysis/{task_id}/report 返回 AnalysisReportData：
//   { task_id, blogger_info, report: <四维度 dict>, full_report_markdown }
//
// report 的每个维度是一个 dict，例如 climate_consumption：
//   {
//     climate_zone: {"湿热南方": 42.0, "干燥北方": 28.0, ...},  // {标签:百分比}
//     concentration: "全国分散型...",                            // 字符串 → text 类型
//     summary: "维度总结"                                        // 维度级 overallSummary
//   }
//
// 前端 ProfileReport.dimensions 期望 Dimension[]：
//   { dimensionId, dimensionName, icon, overallSummary,
//     subDimensions: [{ subId, subName, chartType, data:[{name,value}], summary? }] }

/** 后端报告响应（信封解包后） */
export interface BackendAnalysisReportData {
  task_id: string;
  blogger_info: BackendBloggerInfo | null;
  report: Record<string, unknown>;
  full_report_markdown: string;
}

/** 维度呈现顺序 + 维度元数据（id / 中文名 / icon） */
interface DimensionMeta {
  id: string;
  name: string;
  icon: string;
}

const DIMENSION_ORDER: DimensionMeta[] = [
  { id: 'climate', name: '气候-消费带', icon: '🌡️' },
  { id: 'consumption', name: '香氛消费推断', icon: '💰' },
  { id: 'fashion', name: '穿搭风格-香调映射', icon: '👗' },
  { id: 'lifestyle', name: '生活方式-用香场景', icon: '🎯' },
];

/** 后端维度 key → 前端维度 id */
const DIM_KEY_TO_ID: Record<string, string> = {
  climate_consumption: 'climate',
  fragrance_consumption: 'consumption',
  fashion_fragrance_map: 'fashion',
  lifestyle_scenario: 'lifestyle',
};

/**
 * 后端子维度字段（sub key）→ 呈现元数据：中文名 + chartType。
 * chartType 规则参考 mockData.ts 的对照：
 *   - 数量 ≤4 的百分比类 → pie
 *   - 数量 =5 的 → bar
 *   - 动机/性格类(多维度) → radar
 *   - 字符串型字段 → text
 */
interface SubMeta {
  subId: string;
  subName: string;
  chartType: 'pie' | 'bar' | 'radar' | 'text';
}

const SUB_META: Record<string, Record<string, SubMeta>> = {
  climate_consumption: {
    climate_zone: { subId: 'climate-zone', subName: '气候带', chartType: 'pie' },
    city_tier: { subId: 'city-tier', subName: '地域分布', chartType: 'bar' },
    culture_circle: { subId: 'culture-circle', subName: '文化圈', chartType: 'pie' },
    concentration: { subId: 'concentration', subName: '地域集中度', chartType: 'text' },
  },
  fragrance_consumption: {
    price_tier: { subId: 'price-range', subName: '价格带匹配', chartType: 'bar' },
    purchase_motivation: { subId: 'motivation', subName: '消费动机', chartType: 'radar' },
    decision_path: { subId: 'decision-path', subName: '决策路径', chartType: 'pie' },
    consumption_frequency: { subId: 'frequency', subName: '消费频次', chartType: 'pie' },
  },
  fashion_fragrance_map: {
    fashion_style: { subId: 'fashion-style', subName: '穿搭风格', chartType: 'bar' },
    fashion_scene: { subId: 'fashion-scene', subName: '穿搭场景', chartType: 'pie' },
    color_preference: { subId: 'color-preference', subName: '色彩偏好', chartType: 'bar' },
    fashion_completeness: { subId: 'fashion-completeness', subName: '穿搭完整度', chartType: 'pie' },
  },
  lifestyle_scenario: {
    core_interest: { subId: 'core-interest', subName: '核心兴趣', chartType: 'bar' },
    social_activity: { subId: 'social-activity', subName: '社交活跃度', chartType: 'pie' },
    aesthetic_personality: { subId: 'aesthetic-personality', subName: '审美性格', chartType: 'radar' },
    fragrance_timing: { subId: 'fragrance-timing', subName: '用香时段', chartType: 'pie' },
    content_consumption: { subId: 'content-consumption', subName: '内容消费特征', chartType: 'pie' },
  },
};

/** 不作为子维度展示的字段（维度级总结、集中度文本已在各自处理中） */
const NON_SUB_FIELDS = new Set(['summary', 'overall_summary']);

/** {标签:百分比} dict → ChartDataItem[]，按百分比降序 */
function dictToChartData(obj: Record<string, unknown>): ChartDataItem[] {
  return Object.entries(obj)
    .map(([name, val]) => ({ name, value: typeof val === 'number' ? val : Number(val) || 0 }))
    .sort((a, b) => b.value - a.value);
}

/** 单个维度 dict → Dimension（含 subDimensions） */
function buildDimension(dimKey: string, raw: Record<string, unknown>): Dimension | null {
  if (typeof raw !== 'object' || raw === null) return null;
  const dimId = DIM_KEY_TO_ID[dimKey] ?? dimKey;
  const meta = DIMENSION_ORDER.find(d => d.id === dimId);
  const subMetaMap = SUB_META[dimKey] ?? {};

  const subDimensions: SubDimension[] = [];
  for (const [subKey, val] of Object.entries(raw)) {
    if (NON_SUB_FIELDS.has(subKey)) continue;
    const subMeta = subMetaMap[subKey];
    const subName = subMeta?.subName ?? subKey;
    const subId = subMeta?.subId ?? subKey;
    const chartType = subMeta?.chartType ?? 'pie';

    if (typeof val === 'string') {
      // 字符串型字段（如 concentration）→ text 类型
      subDimensions.push({
        subId,
        subName,
        chartType: 'text',
        data: [{ name: val, value: 100 }],
      });
    } else if (val && typeof val === 'object') {
      subDimensions.push({
        subId,
        subName,
        chartType,
        data: dictToChartData(val as Record<string, unknown>),
      });
    }
  }

  return {
    dimensionId: dimId,
    dimensionName: meta?.name ?? dimKey,
    icon: meta?.icon ?? '📊',
    subDimensions,
    overallSummary: typeof raw.summary === 'string' ? raw.summary : '',
  };
}

/** 粉丝数数字 → 展示文案 */
function formatFollowerCount(n: number | null | undefined): string {
  if (n == null) return '—';
  if (n >= 10000) {
    const w = n / 10000;
    return `${w.toFixed(1).replace(/\.0$/, '')}万`;
  }
  return String(n);
}

/** 后端 AnalysisReportData → 前端 ProfileReport */
export function toProfileReport(data: BackendAnalysisReportData): ProfileReport {
  const report = (data.report ?? {}) as Record<string, unknown>;
  const blogger = data.blogger_info;

  const dimensions: Dimension[] = [];
  // 按固定维度顺序构建
  const orderedKeys = ['climate_consumption', 'fragrance_consumption', 'fashion_fragrance_map', 'lifestyle_scenario'];
  for (const dimKey of orderedKeys) {
    const dim = buildDimension(dimKey, report[dimKey] as Record<string, unknown>);
    if (dim) dimensions.push(dim);
  }

  return {
    taskId: data.task_id,
    bloggerName: blogger?.nickname ?? '未知博主',
    bloggerAvatar: blogger?.avatar_url ?? undefined,
    platform: mapPlatformLabel(blogger?.platform ?? ''),
    followerCount: formatFollowerCount(blogger?.follower_count),
    analysisLevel: '标准',
    analysisTime: '',
    overallSummary: typeof report.overall_summary === 'string' ? report.overall_summary : '',
    dimensions,
    fullReportMarkdown: data.full_report_markdown ?? '',
  };
}

// =====================================================================
// 标签筛选适配（后端 → 前端）
// =====================================================================
//
// 后端 GET /analysis/{task_id}/tags 返回 AnalysisTagsData：
//   { dimensions: [{ dimension_id, dimension_name, sub_dimensions: [...] }] }
//
// 关键：dimension_id / sub_id 必须保留后端原始 key（如 climate_consumption /
// climate_zone），因为提交 POST /fragrance/generate 时 selected_tags 的
// 三层嵌套 key 要和这里一致。

/** 后端标签响应（信封解包后） */
export interface BackendTagItem {
  name: string;
  percentage: number;
  is_default_selected: boolean;
  mutually_exclusive_group?: string | null;
}

export interface BackendTagSubDimension {
  sub_id: string;
  sub_name: string;
  tags: BackendTagItem[];
  is_mutually_exclusive: boolean;
  max_select: number | null;
}

export interface BackendTagDimension {
  dimension_id: string;
  dimension_name: string;
  sub_dimensions: BackendTagSubDimension[];
}

export interface BackendAnalysisTagsData {
  dimensions: BackendTagDimension[];
}

/** 维度 id → icon（与报告页保持一致） */
const TAG_DIM_ICON: Record<string, string> = {
  climate_consumption: '🌡️',
  fragrance_consumption: '💰',
  fashion_fragrance_map: '👗',
  lifestyle_scenario: '🎯',
};

/** 后端 AnalysisTagsData → 前端 TagDimension[] */
export function toTagDimensions(data: BackendAnalysisTagsData): TagDimension[] {
  return (data.dimensions ?? []).map(dim => ({
    dimensionId: dim.dimension_id, // 保留后端原始 key
    dimensionName: dim.dimension_name,
    icon: TAG_DIM_ICON[dim.dimension_id] ?? '📊',
    subDimensions: (dim.sub_dimensions ?? []).map(sub => ({
      subId: sub.sub_id, // 保留后端原始 key
      subName: sub.sub_name,
      tags: (sub.tags ?? []).map(t => ({
        name: t.name,
        percentage: t.percentage,
        isDefaultSelected: t.is_default_selected,
      })),
      isMutuallyExclusive: sub.is_mutually_exclusive,
      maxSelect: sub.max_select,
    })),
  }));
}

// =====================================================================
// 香调方案适配（后端 snake_case → 前端 camelCase）
// =====================================================================

export interface BackendNoteItem {
  name: string;
  description?: string;
  reason?: string;
  changed?: boolean | null;
}

export interface BackendFragrancePlan {
  plan_id: string;
  name: string;
  category?: string;
  top_notes?: BackendNoteItem[];
  middle_notes?: BackendNoteItem[];
  base_notes?: BackendNoteItem[];
  recommendation_reason?: string;
  fragrance_story?: string;
}

export interface BackendIcebergAnalysis {
  surface?: string;
  middle?: string;
  deep?: string;
}

/** 后端 note → 前端 FragranceNote */
function toFragranceNote(n: BackendNoteItem): FragranceNote {
  return {
    name: n.name,
    description: n.description ?? '',
    reason: n.reason ?? '',
    changed: n.changed ?? undefined,
  };
}

/** 后端 plan → 前端 FragrancePlan */
export function toFragrancePlan(p: BackendFragrancePlan): FragrancePlan {
  return {
    planId: p.plan_id,
    name: p.name,
    category: p.category ?? '',
    topNotes: (p.top_notes ?? []).map(toFragranceNote),
    middleNotes: (p.middle_notes ?? []).map(toFragranceNote),
    baseNotes: (p.base_notes ?? []).map(toFragranceNote),
    recommendationReason: p.recommendation_reason ?? '',
    fragranceStory: p.fragrance_story ?? '',
  };
}

/** 后端 iceberg → 前端 IcebergAnalysis */
export function toIcebergAnalysis(i: BackendIcebergAnalysis): IcebergAnalysis {
  return {
    surface: i.surface ?? '',
    middle: i.middle ?? '',
    deep: i.deep ?? '',
  };
}

/** 后端 generate/session 响应里的方案列表 → 前端 FragrancePlan[] */
export function toFragrancePlans(plans: BackendFragrancePlan[] | undefined | null): FragrancePlan[] {
  return (plans ?? []).map(toFragrancePlan);
}

// =====================================================================
// 香调 session / 对话 适配
// =====================================================================

export interface BackendGenerateData {
  session_id: string;
  status: string;
  iceberg_analysis: BackendIcebergAnalysis;
  recommendations: BackendFragrancePlan[];
  warnings?: string[];
}

export interface BackendSessionDetailData {
  session_id: string;
  task_id: string;
  selected_tags: Record<string, Record<string, string[]>>;
  iceberg_analysis: BackendIcebergAnalysis;
  recommendations: BackendFragrancePlan[];
  status: string;
  created_at: string;
}

export interface BackendChatMessageItem {
  id: string;
  role: string;
  content: string;
  updated_plans?: BackendFragrancePlan[] | null;
  created_at: string;
}

export interface BackendChatHistoryData {
  messages: BackendChatMessageItem[];
}

export interface BackendChatData {
  reply: string;
  updated_plans?: BackendFragrancePlan[] | null;
  message_id: string;
}

/** 后端 chat history → 前端 ChatMessage[] */
export function toChatMessages(items: BackendChatMessageItem[] | undefined): ChatMessage[] {
  return (items ?? []).map(m => ({
    id: m.id,
    role: m.role as 'user' | 'assistant',
    content: m.content,
    updatedPlans: m.updated_plans ? toFragrancePlans(m.updated_plans) : null,
    createdAt: m.created_at,
  }));
}

/** 后端 ChatData → 前端 { reply, updatedPlans, messageId } */
export function toChatResponse(d: BackendChatData) {
  return {
    reply: d.reply,
    updatedPlans: d.updated_plans ? toFragrancePlans(d.updated_plans) : null,
    messageId: d.message_id,
  };
}
