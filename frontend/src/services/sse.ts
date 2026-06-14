/**
 * SSE 客户端 — 订阅任务进度流
 *
 * 后端端点：GET /api/v1/analysis/{task_id}/progress （text/event-stream）
 *
 * SSE 帧格式（后端 analysis.py:212）：
 *   event: <event_type>\n
 *   data: <payload 的 JSON 字符串>\n\n
 *
 * 注意：data 字段就是 payload 本身（已被后端从 task_manager 的 {type,data} 内部
 * 结构中解包），前端直接 JSON.parse 即可，无需再取一层 .data。
 *
 * 事件类型：
 *   - progress     ：管道每步推送，payload = {task_id, status, progress, current_step, sub_steps[]}
 *   - step_complete：某步骤完成，payload = {step, summary}
 *   - complete     ：任务成功终止，payload = {task_id, report_id}（终止信号）
 *   - error        ：任务失败/取消，payload = {status, message}（终止信号）
 *
 * EventSource 天然支持 `addEventListener(eventType, ...)`，对应 SSE 帧的 `event:` 字段。
 */

/** 子步骤状态 */
export type SubStepStatus = 'pending' | 'running' | 'completed';

/** 单个子步骤（固定 7 个，名称顺序与后端 analysis_service 一致） */
export interface ProgressSubStep {
  name: string;
  status: SubStepStatus;
}

/** progress 事件的 payload */
export interface ProgressPayload {
  task_id: string;
  status: 'collecting' | 'analyzing' | string;
  progress: number; // 0-100
  current_step: string;
  sub_steps: ProgressSubStep[];
}

/** step_complete 事件的 payload */
export interface StepCompletePayload {
  step: string;
  summary: string;
}

/** complete 事件的 payload（终止信号） */
export interface CompletePayload {
  task_id: string;
  report_id: string;
}

/** error 事件的 payload（终止信号） */
export interface ErrorPayload {
  status: 'failed' | 'cancelled' | string;
  message: string;
}

export interface ProgressHandlers {
  onProgress?: (p: ProgressPayload) => void;
  onStepComplete?: (s: StepCompletePayload) => void;
  onComplete?: (c: CompletePayload) => void;
  onError?: (e: ErrorPayload) => void;
  /** EventSource 自身打开/连接错误（非业务 error 事件） */
  onTransportError?: (err: Event) => void;
}

/** 订阅任务进度。返回一个 close() 用于手动断开（组件卸载时调用）。 */
export function subscribeTaskProgress(
  taskId: string,
  handlers: ProgressHandlers,
): { close: () => void } {
  // 相对路径，走 vite proxy 同源到后端
  const url = `${import.meta.env.VITE_API_BASE ?? '/api/v1'}/analysis/${taskId}/progress`;
  const source = new EventSource(url);

  // data 字段就是 payload 本身，直接 JSON.parse
  const parse = <T>(raw: string | null): T | null => {
    if (!raw) return null;
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  };

  source.addEventListener('progress', (e) => {
    const p = parse<ProgressPayload>((e as MessageEvent).data);
    if (p) handlers.onProgress?.(p);
  });

  source.addEventListener('step_complete', (e) => {
    const s = parse<StepCompletePayload>((e as MessageEvent).data);
    if (s) handlers.onStepComplete?.(s);
  });

  source.addEventListener('complete', (e) => {
    const c = parse<CompletePayload>((e as MessageEvent).data);
    if (c) handlers.onComplete?.(c);
    // 终止事件：主动关闭，避免 EventSource 自动重连
    source.close();
  });

  source.addEventListener('error', (e) => {
    // 后端业务 error 事件（event:error，带 data）vs EventSource 传输错误（无 data）
    const me = e as MessageEvent;
    if (me.data) {
      const errPayload = parse<ErrorPayload>(me.data);
      if (errPayload) handlers.onError?.(errPayload);
      source.close();
      return;
    }
    // 传输层错误（如连接被拒）
    handlers.onTransportError?.(e);
    source.close();
  });

  return {
    close: () => source.close(),
  };
}

export default subscribeTaskProgress;
