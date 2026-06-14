"""
Unit tests for TaskManager.

R2 Three-Question Self-Check:
1. Contract Closure: Validates event emission, subscription lifecycles, and cancellation errors.
2. Symmetry: Verifies that tasks and subscriptions are completely cleared upon completion, cancellation, or error.
3. External Timing: Uses sleep and task orchestration to ensure consistent event-driven state transitions.
"""

import asyncio
import pytest
from app.core.task_manager import TaskManager

async def collect_events(async_iterator):
    events = []
    async for event in async_iterator:
        events.append(event)
    return events

@pytest.mark.asyncio
async def test_basic_pub_sub():
    tm = TaskManager()
    task_id = "test_task_1"
    
    async def mock_coro():
        await tm.emit(task_id, "progress", {"percent": 20})
        await asyncio.sleep(0.01)
        await tm.emit(task_id, "progress", {"percent": 60})
        await asyncio.sleep(0.01)
        await tm.emit(task_id, "complete", {"percent": 100})

    await tm.submit(task_id, mock_coro())
    
    events = await collect_events(tm.subscribe(task_id))
    
    assert len(events) >= 3
    assert events[0] == {"event_type": "progress", "data": {"percent": 20}}
    assert events[1] == {"event_type": "progress", "data": {"percent": 60}}
    assert events[-1]["event_type"] == "complete"
    
    # Wait slightly to ensure done callback completes state transfer
    await asyncio.sleep(0.01)
    assert tm.get_status(task_id) == "completed"

@pytest.mark.asyncio
async def test_task_cancellation():
    tm = TaskManager()
    task_id = "test_cancel_task"
    
    async def long_running_coro():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise
            
    await tm.submit(task_id, long_running_coro())
    assert tm.get_status(task_id) == "running"
    
    sub_task = asyncio.create_task(collect_events(tm.subscribe(task_id)))
    await asyncio.sleep(0.01)  # Allow subscription queue initialization
    
    await tm.cancel(task_id)
    
    assert tm.get_status(task_id) == "cancelled"
    assert task_id not in tm._tasks
    
    events = await sub_task
    assert len(events) > 0
    assert events[-1]["event_type"] == "error"
    assert events[-1]["data"]["status"] == "cancelled"

@pytest.mark.asyncio
async def test_multiple_subscribers():
    tm = TaskManager()
    task_id = "test_multi_sub"
    
    async def mock_coro():
        await tm.emit(task_id, "progress", {"step": 1})
        await asyncio.sleep(0.01)
        await tm.emit(task_id, "progress", {"step": 2})
        await asyncio.sleep(0.01)
        await tm.emit(task_id, "complete", {"step": 3})
        
    await tm.submit(task_id, mock_coro())
    
    sub_task1 = asyncio.create_task(collect_events(tm.subscribe(task_id)))
    sub_task2 = asyncio.create_task(collect_events(tm.subscribe(task_id)))
    
    events1 = await sub_task1
    events2 = await sub_task2
    
    assert len(events1) >= 3
    assert len(events2) >= 3
    assert events1 == events2

@pytest.mark.asyncio
async def test_symmetric_cleanup():
    tm = TaskManager()
    task_id = "test_cleanup"

    async def mock_coro():
        await tm.emit(task_id, "progress", {"step": 1})
        await asyncio.sleep(0.02)
        await tm.emit(task_id, "complete", {"step": 2})

    await tm.submit(task_id, mock_coro())

    # Before subscription, subscribers dict should be empty for this task
    assert task_id not in tm._subscribers

    async for event in tm.subscribe(task_id):
        assert task_id in tm._subscribers
        assert len(tm._subscribers[task_id]) == 1

    # After normal exit, subscriber queue must be fully cleaned up
    assert task_id not in tm._subscribers

    # Test clean up on abrupt subscription exit. Python 的 `async for`
    # 不会自动调用 aclose()，因此订阅方必须显式关闭生成器，这是约定俗成
    # 的资源对称性要求；这里显式 aclose 后再断言清理完成。
    task_id_err = "test_cleanup_err"

    async def mock_coro_err():
        await tm.emit(task_id_err, "progress", {"step": 1})
        await asyncio.sleep(0.02)
        await tm.emit(task_id_err, "complete", {"step": 2})

    await tm.submit(task_id_err, mock_coro_err())

    gen = tm.subscribe(task_id_err)
    try:
        async for _ in gen:
            assert task_id_err in tm._subscribers
            assert len(tm._subscribers[task_id_err]) == 1
            raise RuntimeError("Interrupt subscription")
    except RuntimeError:
        pass
    finally:
        await gen.aclose()

    # After explicit close, subscriber queue must be fully cleaned up
    assert task_id_err not in tm._subscribers

@pytest.mark.asyncio
async def test_duplicate_submit():
    tm = TaskManager()
    task_id = "dup_task"

    async def coro():
        await asyncio.sleep(1)

    await tm.submit(task_id, coro())
    dup_coro = coro()
    try:
        with pytest.raises(ValueError, match="already running"):
            await tm.submit(task_id, dup_coro)
    finally:
        # 显式关闭未被接受的协程，避免 RuntimeWarning
        dup_coro.close()

    await tm.cancel(task_id)

@pytest.mark.asyncio
async def test_subscribe_not_found():
    tm = TaskManager()
    with pytest.raises(ValueError, match="not found"):
        async for _ in tm.subscribe("non_existent"):
            pass

@pytest.mark.asyncio
async def test_task_failed_state():
    tm = TaskManager()
    task_id = "failed_task"
    
    async def bad_coro():
        raise RuntimeError("Something went wrong")
        
    await tm.submit(task_id, bad_coro())
    
    # Wait for the task to finish failing
    await asyncio.sleep(0.01)
    
    assert tm.get_status(task_id) == "failed"
    
    events = []
    async for event in tm.subscribe(task_id):
        events.append(event)
        
    assert len(events) == 1
    assert events[0]["event_type"] == "error"
    assert events[0]["data"]["status"] == "failed"
    assert "Something went wrong" in events[0]["data"]["message"]
