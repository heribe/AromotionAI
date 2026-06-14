import { create } from 'zustand';
import type {
  FragrancePlan,
  IcebergAnalysis,
  ChatMessage,
  NoteChangeAnimation
} from '../types/fragrance';
import { message } from 'antd';
import {
  getSession,
  getHistory,
  generateFragrance,
  chat as apiChat,
  type FragranceGenerateResult,
} from '../services/api';
import { ApiError } from '../services/http';

interface FragranceState {
  // Session 数据
  sessionId: string | null;
  taskId: string | null;
  selectedTags: Record<string, Record<string, string[]>> | null;

  // 推荐方案
  plans: FragrancePlan[];
  icebergAnalysis: IcebergAnalysis | null;
  isLoading: boolean;

  // 对话
  messages: ChatMessage[];
  isSending: boolean;

  // 变更动画
  changeAnimation: NoteChangeAnimation | null;

  // Actions
  /** 初始化已有会话：sessionId 已知，从后端拉取（切回/直接进入调配室） */
  initSession: (sessionId: string) => Promise<void>;
  /** 生成并加载：标签页点「生成」跳来，进入「生成中」动画，后台调 generate，完成后填充 */
  generateAndLoad: (
    taskId: string,
    selectedTags: Record<string, Record<string, string[]>>,
    onSessionReady?: (sessionId: string) => void,
  ) => Promise<void>;
  /** 直接用生成结果填充 */
  hydrateFromResult: (result: FragranceGenerateResult) => void;
  sendMessage: (text: string) => Promise<void>;
  clearChangeAnimation: () => void;
}

export const useFragranceStore = create<FragranceState>((set, get) => ({
  sessionId: null,
  taskId: null,
  selectedTags: null,
  plans: [],
  icebergAnalysis: null,
  isLoading: false,

  messages: [],
  isSending: false,

  changeAnimation: null,

  initSession: async (sessionId: string) => {
    // 已有会话：从后端拉取 session + 历史
    // 若 session 正在 generating（如从历史记录进入一个正在重新生成的工坊），
    // 保持 isLoading=true 显示等待动画，并轮询直到完成，避免误显示「暂无方案」。
    set({ isLoading: true, sessionId });
    const poll = async (): Promise<void> => {
      try {
        const [sessionData, historyData] = await Promise.all([
          getSession(sessionId),
          getHistory(sessionId),
        ]);
        if (sessionData.status === 'generating') {
          // 仍在生成，2s 后重试
          await new Promise(r => setTimeout(r, 2000));
          return poll();
        }
        set({
          sessionId: sessionData.sessionId,
          taskId: sessionData.taskId,
          selectedTags: sessionData.selectedTags,
          plans: sessionData.recommendations,
          icebergAnalysis: sessionData.icebergAnalysis,
          messages: historyData,
          isLoading: false,
        });
      } catch (err) {
        console.error(err);
        const msg = err instanceof ApiError ? err.message : '加载会话失败';
        message.error(msg);
        set({ isLoading: false });
      }
    };
    await poll();
  },

  generateAndLoad: async (
    taskId,
    selectedTags,
    onSessionReady,
  ) => {
    // 进入「生成中」动画态：保留 loading=true，清空旧方案
    set({
      isLoading: true,
      taskId,
      selectedTags,
      plans: [],
      icebergAnalysis: null,
      messages: [],
      sessionId: null,
    });
    try {
      const result = await generateFragrance(taskId, selectedTags, { planCount: 3 });
      // 填充方案
      set({
        sessionId: result.sessionId,
        plans: result.recommendations,
        icebergAnalysis: result.icebergAnalysis,
        isLoading: false,
      });
      // 拉取初始 assistant 消息
      try {
        const history = await getHistory(result.sessionId);
        set({ messages: history });
      } catch {
        /* 历史拉取失败不阻塞 */
      }
      onSessionReady?.(result.sessionId);
    } catch (err) {
      console.error(err);
      const msg = err instanceof ApiError ? err.message : '生成香调方案失败';
      message.error(msg);
      set({ isLoading: false });
    }
  },

  hydrateFromResult: (result) => {
    set({
      sessionId: result.sessionId,
      taskId: result.taskId ?? null,
      selectedTags: null,
      plans: result.recommendations,
      icebergAnalysis: result.icebergAnalysis,
      messages: [],
      isLoading: false,
    });
  },

  sendMessage: async (text: string) => {
    const { sessionId, messages } = get();
    if (!sessionId || !text.trim()) return;

    // 1. 立即把 User 消息塞进去
    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: text,
      updatedPlans: null,
      createdAt: new Date().toISOString()
    };
    set({ messages: [...messages, userMsg], isSending: true });

    try {
      // 2. 调真实后端 chat
      const response = await apiChat(sessionId, text);

      // 3. 处理 Assistant 回复
      const astMsg: ChatMessage = {
        id: response.messageId,
        role: 'assistant',
        content: response.reply,
        updatedPlans: response.updatedPlans,
        createdAt: new Date().toISOString()
      };

      // 4. 如果有方案更新，替换当前 plans 并触发动画
      if (response.updatedPlans && response.updatedPlans.length > 0) {
        const newPlans = [...get().plans];
        const changedNoteNames: string[] = [];

        response.updatedPlans.forEach(updatedPlan => {
          const idx = newPlans.findIndex(p => p.planId === updatedPlan.planId);
          if (idx !== -1) {
            newPlans[idx] = updatedPlan;
          }

          // 收集所有被标记为 changed: true 的香材名字，用于动画
          const noteGroups = [updatedPlan.topNotes, updatedPlan.middleNotes, updatedPlan.baseNotes];
          noteGroups.forEach(notes => {
            notes.forEach(note => {
              if (note.changed) changedNoteNames.push(note.name);
            });
          });
        });

        set({
          plans: newPlans,
          changeAnimation: {
            planId: response.updatedPlans[0].planId,
            changedNotes: changedNoteNames,
            timestamp: Date.now()
          }
        });

        // 3秒后自动清除动画状态
        setTimeout(() => {
          get().clearChangeAnimation();
        }, 3000);
      }

      // 更新消息列表
      set(state => ({ messages: [...state.messages, astMsg] }));

    } catch (err) {
      console.error(err);
      const msg = err instanceof ApiError ? err.message : '发送失败，请重试';
      message.error(msg);
    } finally {
      set({ isSending: false });
    }
  },

  clearChangeAnimation: () => set({ changeAnimation: null })
}));
