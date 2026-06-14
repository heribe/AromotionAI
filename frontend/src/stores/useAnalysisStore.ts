/**
 * 全局状态管理 — Zustand Store
 * 管理任务列表、画像报告、标签筛选、任务进度（SSE）等全局状态
 */

import { create } from 'zustand';
import type { AnalysisTask, ProfileReport, TagDimension } from '../types/analysis';
import { analysisApi } from '../services';
import { getTask as fetchTaskDetail } from '../services/api';
import { subscribeTaskProgress, type ProgressSubStep } from '../services/sse';

interface AnalysisStore {
  // 任务列表
  taskList: AnalysisTask[];
  taskListLoading: boolean;
  fetchTaskList: () => Promise<void>;

  // 创建任务
  createTask: (bloggerUrl: string, level: string) => Promise<{ taskId: string }>;
  creating: boolean;

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

  // 任务进度（SSE）
  progressTaskId: string | null;
  progress: number;
  progressStatus: string;
  currentStep: string;
  subSteps: ProgressSubStep[];
  stepSummaries: Record<string, string>; // step → summary
  progressError: string | null;
  /** 查询任务当前真实状态（用于进度页 mount 时判断是否已终态） */
  fetchTaskStatus: (taskId: string) => Promise<AnalysisTask>;
  subscribeProgress: (taskId: string) => void;
  unsubscribeProgress: () => void;
  resetProgress: () => void;
}

/** SSE 订阅句柄（不放入 state，模块级变量） */
let progressSubscription: { close: () => void } | null = null;

export const useAnalysisStore = create<AnalysisStore>((set, get) => ({
  // ===== 任务列表 =====
  taskList: [],
  taskListLoading: false,

  fetchTaskList: async () => {
    set({ taskListLoading: true });
    try {
      const list = await analysisApi.getTaskList();
      set({ taskList: list });
    } finally {
      set({ taskListLoading: false });
    }
  },

  // ===== 创建任务 =====
  creating: false,

  createTask: async (bloggerUrl, level) => {
    set({ creating: true });
    try {
      const { taskId } = await analysisApi.createTask({
        bloggerUrl,
        platform: 'auto',
        analysisLevel: level,
      });
      // 创建成功后刷新列表，让新任务出现在列表里
      await get().fetchTaskList();
      return { taskId };
    } finally {
      set({ creating: false });
    }
  },

  // ===== 画像报告 =====
  currentReport: null,
  reportLoading: false,

  fetchReport: async (taskId: string) => {
    set({ reportLoading: true, currentReport: null });
    try {
      const report = await analysisApi.getReport(taskId);
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
      const dimensions = await analysisApi.getTags(taskId);
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

  // ===== 任务进度（SSE）=====
  progressTaskId: null,
  progress: 0,
  progressStatus: 'pending',
  currentStep: '准备开始',
  subSteps: [],
  stepSummaries: {},
  progressError: null,

  fetchTaskStatus: async (taskId: string) => {
    return fetchTaskDetail(taskId);
  },

  subscribeProgress: (taskId: string) => {
    // 先断开旧订阅
    if (progressSubscription) {
      progressSubscription.close();
      progressSubscription = null;
    }
    // 仅设置关注的任务 id 与清空 error，不重置进度（避免重复订阅时闪烁）
    set({
      progressTaskId: taskId,
      progressError: null,
    });

    progressSubscription = subscribeTaskProgress(taskId, {
      onProgress: (p) => {
        set({
          progress: p.progress,
          progressStatus: p.status,
          currentStep: p.current_step,
          subSteps: p.sub_steps ?? [],
        });
      },
      onStepComplete: (s) => {
        set(state => ({
          stepSummaries: { ...state.stepSummaries, [s.step]: s.summary },
        }));
      },
      onComplete: () => {
        set({ progress: 100, progressStatus: 'completed' });
      },
      onError: (e) => {
        set({ progressStatus: e.status, progressError: e.message });
      },
      onTransportError: () => {
        set({ progressError: '进度连接中断，请刷新重试' });
      },
    });
  },

  unsubscribeProgress: () => {
    if (progressSubscription) {
      progressSubscription.close();
      progressSubscription = null;
    }
  },

  resetProgress: () => {
    get().unsubscribeProgress();
    set({
      progressTaskId: null,
      progress: 0,
      progressStatus: 'pending',
      currentStep: '准备开始',
      subSteps: [],
      stepSummaries: {},
      progressError: null,
    });
  },
}));
