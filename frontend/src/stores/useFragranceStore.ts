import { create } from 'zustand';
import type { 
  FragranceSessionData, 
  FragrancePlan, 
  IcebergAnalysis, 
  ChatMessage, 
  NoteChangeAnimation 
} from '../types/fragrance';
import { mockFragranceApi } from '../services/mockFragranceData';
import { message } from 'antd';

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
  initSession: (sessionId: string) => Promise<void>;
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
    set({ isLoading: true });
    try {
      const [sessionData, historyData] = await Promise.all([
        mockFragranceApi.getSession(sessionId),
        mockFragranceApi.getHistory(sessionId)
      ]);
      
      /* =========================================================================
       * [TODO] 接入真实后端时的替换逻辑：
       * =========================================================================
       * 1. 判断 sessionData.status:
       * 
       * if (sessionData.status === 'completed') {
       *   // 场景A: 切出后切回 (早已完成)
       *   // 直接放入全部数据，设置 isLoading: false
       *   // 视图层会在极短时间内(0.5s)结束 loading 动画，瞬间触发阶梯入场。
       *   set({ plans: ..., icebergAnalysis: ..., isLoading: false });
       * } else {
       *   // 场景B: 真实生成中 (全程驻留)
       *   // 保持 isLoading: true，存入基础信息(taskId, selectedTags)，让视图显示萃取动画。
       *   // 然后开启 setInterval 轮询 getSession 接口。
       *   // 当查到 status === 'completed' 时，再 set({ plans, isLoading: false }) 并 clearInterval。
       * }
       * ========================================================================= 
       */

      // 第一阶段：立刻拥有 sessionId, taskId, selectedTags，但处于 loading
      set({
        sessionId,
        taskId: sessionData.taskId,
        selectedTags: sessionData.selectedTags,
        // 清空之前的数据
        plans: [],
        icebergAnalysis: null,
        messages: [],
      });

      // 第二阶段：模拟大模型生成的 5 秒延迟 (真实后端接入后替换为上述轮询逻辑)
      setTimeout(() => {
        set({
          plans: sessionData.recommendations,
          icebergAnalysis: sessionData.icebergAnalysis,
          messages: historyData.messages,
          isLoading: false
        });
      }, 5000);

    } catch (err) {
      console.error(err);
      message.error('加载会话失败');
      set({ isLoading: false });
    }
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
      /* =========================================================================
       * [TODO] 接入真实后端时的替换逻辑（流式对话与配方更新）：
       * =========================================================================
       * 1. 替换 mockFragranceApi.chat 为真正的 SSE / WebSocket 或 Fetch 流式调用。
       * 2. 如果是流式响应（SSE）：
       *    - 需要在本地维护一个临时的 assistantMsg，每收到一个 chunk 就拼接 content 并更新 messages 数组。
       * 3. 流结束时，如果后端返回了 updatedPlans：
       *    - 执行下方的计划替换逻辑，并设置 changeAnimation 触发卡片高亮与香材[NEW]动效。
       * =========================================================================
       */
      
      // 2. 调用 Mock API
      const response = await mockFragranceApi.chat(sessionId, text);
      
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
          ['topNotes', 'middleNotes', 'baseNotes'].forEach(key => {
            (updatedPlan as any)[key]?.forEach((note: any) => {
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
      message.error('发送失败，请重试');
    } finally {
      set({ isSending: false });
    }
  },
  
  clearChangeAnimation: () => set({ changeAnimation: null })
}));
