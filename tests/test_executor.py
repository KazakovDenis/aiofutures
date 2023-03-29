import pytest

from aiofutures import AsyncExecutor, InvalidStateError, run_async, sync_to_async


SENTINEL = object()


async def async_task(result):
    return result


async def async_with_sync_task(executor, result):
    res = await executor.sync_to_async(lambda x: x, result)
    return res


async def async_with_sync_shortcut_task(result):
    res = await sync_to_async(lambda x: x, result)
    return res


def test_submit(executor):
    future = executor.submit(async_task, SENTINEL)
    assert future.result() == SENTINEL


def test_shortcut_run_async():
    future = run_async(async_task, SENTINEL)
    assert future.result() == SENTINEL


def test_map(executor):
    result = [SENTINEL, SENTINEL]
    res_iter = executor.map(async_task, result)
    assert list(res_iter) == result


def test_sync_to_async(executor):
    future = executor.submit(async_with_sync_task, executor, SENTINEL)
    assert future.result() == SENTINEL


def test_shortcut_sync_to_async():
    future = run_async(async_with_sync_shortcut_task, SENTINEL)
    assert future.result() == SENTINEL


@pytest.mark.parametrize('wait, cancel_futures', [
    (False, False),
    (False, True),
    (True, False),
    (True, True),
])
def test_submit_after_shutdown(wait, cancel_futures):
    executor = AsyncExecutor()
    executor.shutdown(wait, cancel_futures)
    with pytest.raises(InvalidStateError):
        executor.submit(async_task)
