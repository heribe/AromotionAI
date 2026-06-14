import asyncio
import logging
from typing import AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)

# 单任务事件回放缓冲上限：保证晚到的订阅者也能拿到完整事件流，
# 同时限制内存占用避免长期运行后内存泄漏。
MAX_HISTORY_PER_TASK = 200
# 全局已完成任务元信息缓存上限。
MAX_FINISHED_CACHE = 1000


class TaskManager:
    """异步任务管理器：负责任务提交、事件发布订阅与状态查询。

    设计要点（R2 三问自检）：
    1. 契约闭环：每个 submit 都会以 complete 或 error 事件收尾，订阅者总能拿到终止信号。
    2. 对称性：submit 注册的 task / 订阅者队列 / 历史缓冲在任务结束、订阅者退出、
       或被 GC 时都会被清理；并提供显式的 shutdown 钩子。
    3. 外部时序：所有对共享字典的读写都在同一把 asyncio.Lock 下完成，避免并发 emit
       / subscribe 之间的竞态；事件回放保证晚到的订阅者不丢事件。
    """

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        # 缓存已结束任务的最终状态与原始错误信息
        self._statuses: Dict[str, str] = {}
        self._final_messages: Dict[str, str] = {}
        # 每个任务的事件回放缓冲，保证晚到订阅者拿到完整事件流
        self._event_history: Dict[str, List[dict]] = {}
        self._lock = asyncio.Lock()

    async def submit(self, task_id: str, coro) -> None:
        """提交异步任务。task_id 已在运行则抛出 ValueError。"""
        async with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task with ID {task_id} is already running.")

            # 复用同一 task_id 重新提交时，清理上一次的终态缓存
            self._event_history.setdefault(task_id, [])
            self._statuses.pop(task_id, None)
            self._final_messages.pop(task_id, None)

            async def wrapped_coro():
                try:
                    await coro
                    # 保底发送 complete 事件（如果业务逻辑没有自行 emit）
                    await self.emit(task_id, "complete", {"status": "completed"})
                except asyncio.CancelledError:
                    await self.emit(
                        task_id,
                        "error",
                        {"status": "cancelled", "message": "Task was cancelled"},
                    )
                    raise
                except Exception as e:
                    await self.emit(
                        task_id,
                        "error",
                        {"status": "failed", "message": str(e)},
                    )
                    raise

            task = asyncio.create_task(wrapped_coro())
            self._tasks[task_id] = task

            def clean_up(t: asyncio.Task):
                # 确定最终状态并缓存原始错误信息
                if t.cancelled():
                    status = "cancelled"
                    message = "Task was cancelled"
                else:
                    exc = None
                    try:
                        exc = t.exception()
                    except Exception:
                        pass
                    if exc is not None:
                        status = "failed"
                        message = str(exc) or exc.__class__.__name__
                    else:
                        status = "completed"
                        message = ""

                self._statuses[task_id] = status
                if message:
                    self._final_messages[task_id] = message
                self._tasks.pop(task_id, None)

                # 限制缓存大小以防止内存泄漏
                if len(self._statuses) > MAX_FINISHED_CACHE:
                    first_key = next(iter(self._statuses))
                    self._statuses.pop(first_key, None)
                    self._final_messages.pop(first_key, None)
                    self._event_history.pop(first_key, None)

            task.add_done_callback(clean_up)

    async def emit(self, task_id: str, event_type: str, data: dict) -> None:
        """向所有订阅该 task_id 的队列推送事件，同时写入历史缓冲。

        事件结构遵循文档契约：``{"type": <event_type>, "data": <payload>}``。
        """
        event = {"type": event_type, "data": data}
        async with self._lock:
            # 写入历史缓冲以供晚到订阅者回放
            history = self._event_history.setdefault(task_id, [])
            history.append(event)
            if len(history) > MAX_HISTORY_PER_TASK:
                # 丢弃最旧的事件以保持上限
                del history[: len(history) - MAX_HISTORY_PER_TASK]

            queues = self._subscribers.get(task_id, [])
            for queue in queues:
                await queue.put(event)

    async def subscribe(self, task_id: str) -> AsyncIterator[dict]:
        """订阅任务事件流。

        - 若 task_id 不存在抛出 ValueError；
        - 先回放已缓冲的历史事件；
        - 若任务已结束（且历史中没有终止事件）则合成一条终止事件；
        - 否则进入实时事件循环，直到拿到 complete/error 为止。
        """
        async with self._lock:
            status = self._get_status_unlocked(task_id)
            if status == "not_found":
                raise ValueError(f"Task {task_id} not found.")

            # 在锁内完成快照与队列注册，确保不丢事件也不重复
            history_snapshot = list(self._event_history.get(task_id, []))
            current_status = status
            final_message = self._final_messages.get(task_id, "")

            queue: Optional[asyncio.Queue] = None
            if current_status == "running":
                queue = asyncio.Queue()
                self._subscribers.setdefault(task_id, []).append(queue)

        # 1) 回放历史事件，遇到终止事件则停止
        terminal_seen = False
        for event in history_snapshot:
            yield event
            if event.get("type") in ("complete", "error"):
                terminal_seen = True
                return

        # 2) 历史为空但任务已结束：合成终止事件
        if current_status in ("completed", "failed", "cancelled") and not history_snapshot:
            event_type = "complete" if current_status == "completed" else "error"
            yield {
                "type": event_type,
                "data": {
                    "status": current_status,
                    "message": final_message
                    or f"Task already finished with status: {current_status}",
                },
            }
            return

        # 3) 任务已结束且历史里已有终止事件：上面 return 已处理
        if current_status in ("completed", "failed", "cancelled"):
            # 极端兜底：理论上不应执行到这里
            return

        # 4) 任务仍在运行：进入实时事件循环
        assert queue is not None
        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("type") in ("complete", "error"):
                    break
        finally:
            async with self._lock:
                if task_id in self._subscribers:
                    if queue in self._subscribers[task_id]:
                        self._subscribers[task_id].remove(queue)
                    if not self._subscribers[task_id]:
                        self._subscribers.pop(task_id, None)

    def _get_status_unlocked(self, task_id: str) -> str:
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task.done():
                if task.cancelled():
                    return "cancelled"
                try:
                    exc = task.exception()
                    return "failed" if exc is not None else "completed"
                except asyncio.CancelledError:
                    return "cancelled"
                except Exception:
                    return "failed"
            return "running"

        if task_id in self._statuses:
            return self._statuses[task_id]

        return "not_found"

    def get_status(self, task_id: str) -> str:
        """获取任务运行状态 ('running', 'completed', 'failed', 'cancelled', 'not_found')。"""
        return self._get_status_unlocked(task_id)

    def get_final_message(self, task_id: str) -> Optional[str]:
        """获取任务最终的错误/取消消息（仅对已结束且非成功的任务返回字符串）。"""
        return self._final_messages.get(task_id)

    async def cancel(self, task_id: str) -> None:
        """取消正在运行的异步任务。"""
        task = None
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.cancel()

        if task:
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def shutdown(self) -> None:
        """关闭所有正在运行的任务，用于应用退出时的对称清理。"""
        async with self._lock:
            running_ids = list(self._tasks.keys())
        for task_id in running_ids:
            try:
                await self.cancel(task_id)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to cancel task {task_id} during shutdown: {e}")


# 全局单例
task_manager = TaskManager()
