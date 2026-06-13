/**
 * Part 2: 香调推荐 — 全局类型定义
 * 严格对齐 docs/04-part2-frontend.md 的数据结构
 */

export interface FragranceNote {
  name: string;
  description: string;
  reason: string;
  changed?: boolean;  // 是否被对话修改（前端标识位）
}

export interface IcebergAnalysis {
  surface: string;   // 显性行为层
  middle: string;    // 情感价值层
  deep: string;      // 深层需求
}

export interface FragrancePlan {
  planId: string;
  name: string;
  category: string;
  topNotes: FragranceNote[];
  middleNotes: FragranceNote[];
  baseNotes: FragranceNote[];
  recommendationReason: string;
  fragranceStory: string;
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
