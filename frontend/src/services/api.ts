/**
 * 真实后端 API 实现 — Part 1（分析）部分
 *
 * 所有方法返回前端 types（经 adapters 转换），与 mockApi 同签名，
 * 便于 services/index.ts 门面切换。
 *
 * 后端端点：baseURL = /api/v1（见 http.ts），下面路径均相对此。
 */
import { http } from './http';
import {
  toAnalysisTask,
  toAnalysisTaskDetail,
  toProfileReport,
  toTagDimensions,
  toFragrancePlans,
  toIcebergAnalysis,
  toChatMessages,
  toChatResponse,
  fromCreateAnalysisRequest,
  type BackendAnalysisListItem,
  type BackendAnalysisTaskDetail,
  type BackendAnalysisReportData,
  type BackendAnalysisTagsData,
  type BackendGenerateData,
  type BackendSessionDetailData,
  type BackendChatHistoryData,
} from './adapters';
import type { AnalysisTask, CreateAnalysisRequest, ProfileReport, TagDimension } from '../types/analysis';
import type { FragrancePlan, IcebergAnalysis, ChatMessage } from '../types/fragrance';

// =====================================================================
// Part 1：分析
// =====================================================================

/** GET /analysis/list → 任务列表 */
export async function getTaskList(): Promise<AnalysisTask[]> {
  const data = await http.get<{ items: BackendAnalysisListItem[]; total: number }>(
    '/analysis/list',
    { page: 1, page_size: 50 },
  );
  return (data.items ?? []).map(toAnalysisTask);
}

/** GET /analysis/{task_id} → 任务详情（含 currentStep / errorMessage） */
export async function getTask(taskId: string): Promise<AnalysisTask> {
  const data = await http.get<BackendAnalysisTaskDetail>(`/analysis/${taskId}`);
  return toAnalysisTaskDetail(data);
}

/** GET /analysis/{task_id}/report → 画像报告 */
export async function getReport(taskId: string): Promise<ProfileReport> {
  const data = await http.get<BackendAnalysisReportData>(`/analysis/${taskId}/report`);
  return toProfileReport(data);
}

/** GET /analysis/{task_id}/tags → 标签筛选数据 */
export async function getTags(taskId: string): Promise<TagDimension[]> {
  const data = await http.get<BackendAnalysisTagsData>(`/analysis/${taskId}/tags`);
  return toTagDimensions(data);
}

/** POST /analysis/create → 创建任务，返回 task_id */
export async function createTask(req: CreateAnalysisRequest): Promise<{ taskId: string }> {
  const data = await http.post<{ task_id: string; status: string; created_at: string }>(
    '/analysis/create',
    fromCreateAnalysisRequest(req),
  );
  return { taskId: data.task_id };
}

// =====================================================================
// Part 2：香调推荐
// =====================================================================

/** 生成香调的选项 */
export interface GenerateFragranceOptions {
  bloggerWeight?: number; // 0-1，博主权重，默认 0.5
  audienceWeight?: number; // 0-1，受众权重，默认 0.5
  planCount?: number; // 1-5，方案数，默认 3
}

/** 生成结果（适配为前端类型） */
export interface FragranceGenerateResult {
  sessionId: string;
  status: string;
  icebergAnalysis: IcebergAnalysis;
  recommendations: FragrancePlan[];
  warnings: string[];
  /** 关联的任务 id（generate 接口本身不返回，由调用方传入回填） */
  taskId?: string;
}

/**
 * POST /fragrance/generate → 生成香调方案，返回 session_id + 方案
 *
 * selectedTags 为后端要求的三层嵌套 {dim_id:{sub_id:[tag_name]}}，
 * 由调用方（TagSelection）从 tagDimensions + tagSelections 组装。
 */
export async function generateFragrance(
  taskId: string,
  selectedTags: Record<string, Record<string, string[]>>,
  opts?: GenerateFragranceOptions,
): Promise<FragranceGenerateResult> {
  const body = {
    task_id: taskId,
    selected_tags: selectedTags,
    blogger_weight: opts?.bloggerWeight ?? 0.5,
    audience_weight: opts?.audienceWeight ?? 0.5,
    plan_count: opts?.planCount ?? 3,
  };
  const data = await http.post<BackendGenerateData>('/fragrance/generate', body);
  return {
    sessionId: data.session_id,
    status: data.status,
    icebergAnalysis: toIcebergAnalysis(data.iceberg_analysis),
    recommendations: toFragrancePlans(data.recommendations),
    warnings: data.warnings ?? [],
    taskId,
  };
}

/** GET /fragrance/{session_id} → 会话详情（方案 + 冰山分析 + 标签） */
export async function getSession(sessionId: string): Promise<{
  sessionId: string;
  taskId: string;
  selectedTags: Record<string, Record<string, string[]>>;
  icebergAnalysis: IcebergAnalysis;
  recommendations: FragrancePlan[];
  status: string;
  createdAt: string;
}> {
  const data = await http.get<BackendSessionDetailData>(`/fragrance/${sessionId}`);
  return {
    sessionId: data.session_id,
    taskId: data.task_id,
    selectedTags: data.selected_tags,
    icebergAnalysis: toIcebergAnalysis(data.iceberg_analysis),
    recommendations: toFragrancePlans(data.recommendations),
    status: data.status,
    createdAt: data.created_at,
  };
}

/** GET /fragrance/{session_id}/history → 对话历史 */
export async function getHistory(sessionId: string): Promise<ChatMessage[]> {
  const data = await http.get<BackendChatHistoryData>(`/fragrance/${sessionId}/history`);
  return toChatMessages(data.messages);
}

/** POST /fragrance/{session_id}/chat → 对话微调，返回 reply + 可能的方案更新 */
export async function chat(
  sessionId: string,
  text: string,
): Promise<{ reply: string; updatedPlans: FragrancePlan[] | null; messageId: string }> {
  const data = await http.post<{ reply: string; updated_plans?: BackendGenerateData['recommendations'] | null; message_id: string }>(
    `/fragrance/${sessionId}/chat`,
    { message: text },
  );
  return toChatResponse(data);
}

/** POST /fragrance/{session_id}/regenerate → 重新生成方案 */
export async function regenerate(
  sessionId: string,
  opts?: GenerateFragranceOptions,
): Promise<FragranceGenerateResult> {
  const body = {
    blogger_weight: opts?.bloggerWeight ?? 0.5,
    audience_weight: opts?.audienceWeight ?? 0.5,
    plan_count: opts?.planCount ?? 3,
  };
  const data = await http.post<BackendGenerateData>(`/fragrance/${sessionId}/regenerate`, body);
  return {
    sessionId: data.session_id,
    status: data.status,
    icebergAnalysis: toIcebergAnalysis(data.iceberg_analysis),
    recommendations: toFragrancePlans(data.recommendations),
    warnings: data.warnings ?? [],
  };
}
