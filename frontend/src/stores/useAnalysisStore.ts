/**
 * 全局状态管理 — Zustand Store
 * 管理任务列表、画像报告、标签筛选等全局状态
 */

import { create } from 'zustand';
import type { AnalysisTask, ProfileReport, TagDimension } from '../types/analysis';
import { mockApi } from '../services/mockData';

interface AnalysisStore {
  // 任务列表
  taskList: AnalysisTask[];
  taskListLoading: boolean;
  fetchTaskList: () => Promise<void>;

  // 画像报告
  currentReport: ProfileReport | null;
  reportLoading: boolean;
  fetchReport: (taskId: string) => Promise<void>;

  // 标签数据
  tagDimensions: TagDimension[];
  tagSelections: Record<string, string[]>; // subId → 选中的标签名列表
  tagsLoading: boolean;
  fetchTags: (taskId: string) => Promise<void>;
  toggleTag: (subId: string, tagName: string, isMutuallyExclusive: boolean, maxSelect: number | null) => void;
  getSelectedTags: () => Array<{ subId: string; tags: string[] }>;
  resetToDefault: () => void;
}

export const useAnalysisStore = create<AnalysisStore>((set, get) => ({
  // ===== 任务列表 =====
  taskList: [],
  taskListLoading: false,

  fetchTaskList: async () => {
    set({ taskListLoading: true });
    try {
      const list = await mockApi.getTaskList();
      set({ taskList: list });
    } finally {
      set({ taskListLoading: false });
    }
  },

  // ===== 画像报告 =====
  currentReport: null,
  reportLoading: false,

  fetchReport: async (taskId: string) => {
    set({ reportLoading: true, currentReport: null });
    try {
      const report = await mockApi.getReport(taskId);
      set({ currentReport: report });
    } finally {
      set({ reportLoading: false });
    }
  },

  // ===== 标签筛选 =====
  tagDimensions: [],
  tagSelections: {},
  tagsLoading: false,

  fetchTags: async (taskId: string) => {
    set({ tagsLoading: true });
    try {
      const dimensions = await mockApi.getTags(taskId);
      // 初始化默认选中
      const defaultSelections: Record<string, string[]> = {};
      dimensions.forEach(dim => {
        dim.subDimensions.forEach(sub => {
          defaultSelections[sub.subId] = sub.tags
            .filter(t => t.isDefaultSelected)
            .map(t => t.name);
        });
      });
      set({ tagDimensions: dimensions, tagSelections: defaultSelections });
    } finally {
      set({ tagsLoading: false });
    }
  },

  toggleTag: (subId, tagName, isMutuallyExclusive, maxSelect) => {
    set(state => {
      const current = state.tagSelections[subId] || [];

      if (isMutuallyExclusive) {
        // 互斥：直接替换
        return { tagSelections: { ...state.tagSelections, [subId]: [tagName] } };
      }

      if (current.includes(tagName)) {
        // 取消选中
        return { tagSelections: { ...state.tagSelections, [subId]: current.filter(t => t !== tagName) } };
      }

      // 检查最大数量限制
      if (maxSelect !== null && current.length >= maxSelect) {
        // 超出限制，不做任何操作（组件层可以弹 toast）
        return state;
      }

      return { tagSelections: { ...state.tagSelections, [subId]: [...current, tagName] } };
    });
  },

  getSelectedTags: () => {
    const { tagSelections } = get();
    return Object.entries(tagSelections)
      .filter(([, tags]) => tags.length > 0)
      .map(([subId, tags]) => ({ subId, tags }));
  },

  resetToDefault: () => {
    const { tagDimensions } = get();
    const defaultSelections: Record<string, string[]> = {};
    tagDimensions.forEach(dim => {
      dim.subDimensions.forEach(sub => {
        defaultSelections[sub.subId] = sub.tags
          .filter(t => t.isDefaultSelected)
          .map(t => t.name);
      });
    });
    set({ tagSelections: defaultSelections });
  },
}));
