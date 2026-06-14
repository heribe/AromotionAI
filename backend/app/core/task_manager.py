import asyncio
import logging
from typing import AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._statuses: Dict[str, str] = {}  # 缓存已结束任务的最终状态
        self._lock = asyncio.Lock()

    async def submit(self, task_id: str, coro) -> None:
        """提交异步任务"""
        async with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task with ID {task_id} is already running.")
            
            async def wrapped_coro():
                try:
                    await coro
                    # 保底发送 complete 事件
                    await self.emit(task_id, "complete", {"status": "completed"})
                except asyncio.CancelledError:
                    # 发送 error 事件以通知订阅者任务被取消
                    await self.emit(task_id, "error", {"status": "cancelled", "message": "Task was cancelled"})
                    raise
                except Exception as e:
                    # 发送 error 事件以通知订阅者任务出错
                    await self.emit(task_id, "error", {"status": "failed", "message": str(e)})
                    raise

            task = asyncio.create_task(wrapped_coro())
            self._tasks[task_id] = task

            def clean_up(t: asyncio.Task):
                # 确定最终状态
                if t.cancelled():
                    status = "cancelled"
                else:
                    exc = None
                    try:
                        exc = t.exception()
                    except Exception:
                        pass
                    status = "failed" if exc is not None else "completed"

                self._statuses[task_id] = status
                self._tasks.pop(task_id, None)

                # 限制缓存大小以防止内存泄漏
                if len(self._statuses) > 1000:
                    first_key = next(iter(self._statuses))
                    self._statuses.pop(first_key, None)

            task.add_done_callback(clean_up)

    async def emit(self, task_id: str, event_type: str, data: dict) -> None:
        """向所有订阅该 task_id 的队列推送事件"""
        event = {
            "event_type": event_type,
            "data": data
        }
        async with self._lock:
            queues = self._subscribers.get(task_id, [])
            for queue in queues:
                await queue.put(event)

    async def subscribe(self, task_id: str) -> AsyncIterator[dict]:
        """订阅任务的事件流 (当收到类型为 complete 或 error 时停止推送)"""
        async with self._lock:
            status = self._get_status_unlocked(task_id)
            if status == "not_found":
                raise ValueError(f"Task {task_id} not found.")

            if status in ("completed", "failed", "cancelled"):
                event_type = "complete" if status == "completed" else "error"
                yield_immediate = {
                    "event_type": event_type,
                    "data": {
                        "status": status,
                        "message": f"Task already finished with status: {status}"
                    }
                }
            else:
                yield_immediate = None
                queue = asyncio.Queue()
                if task_id not in self._subscribers:
                    self._subscribers[task_id] = []
                self._subscribers[task_id].append(queue)

        if yield_immediate:
            yield yield_immediate
            return

        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("event_type") in ("complete", "error"):
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
        """获取任务在 asyncio 任务池中的运行状态 ('running', 'completed', 'failed', 'cancelled', 'not_found' 等)"""
        return self._get_status_unlocked(task_id)

    async def cancel(self, task_id: str) -> None:
        """取消正在运行的异步任务"""
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

# 全局单例
task_manager = TaskManager()
