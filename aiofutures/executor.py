"""The module with the executor implementing concurrent.futures.Executor
interface to run coroutines in a different thread.

Example:
    >>> import asyncio
    >>> import time
    >>>
    >>> async def io_bound_func(*args, **kwargs):
    >>>     print('started: async task')
    >>>     await asyncio.sleep(2)
    >>>     print('finished: async task')
    >>>     return args, kwargs
    >>>
    >>> def main_thread_blocking_func(wait_for: float):
    >>>     print('started: blocking task')
    >>>     time.sleep(wait_for)
    >>>     print('finished: blocking task')
    >>>
    >>> with AsyncExecutor() as ex:
    >>>     future1 = ex.submit(io_bound_func, 1, a=1)
    >>>     future2 = ex.submit(io_bound_func, 2, b=2)
    >>>     main_thread_blocking_func(5.0)
    >>>
    >>> print('result 1:', future1.result())
    >>> print('result 2:', future2.result())

Output:
    started: blocking task
    started: async task
    started: async task
    finished: async task
    finished: async task
    finished: blocking task
    result 1: ((1,), {'a': 1})
    result 2: ((2,), {'b': 2})
"""
import asyncio
import time
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from threading import Thread
from typing import Awaitable, Callable, Optional, Set

from .exceptions import InvalidStateError


class AsyncExecutor(Executor):
    """The executor that runs coroutines in a different thread."""
    _loop: asyncio.BaseEventLoop

    def __init__(self, executor: Optional[ThreadPoolExecutor] = None) -> None:
        def run():
            self._loop = asyncio.new_event_loop()
            if executor:
                self._loop.set_default_executor(executor)

            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._stopped = False
        self._thread = Thread(target=run, name=self.__class__.__name__, daemon=True)
        self._thread.start()

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return f'<{cls} stopped={self._stopped} tasks={len(self.tasks)}>'

    @property
    def tasks(self) -> Set[asyncio.Task]:
        return asyncio.all_tasks(self._loop)

    def submit(self, task: Callable[..., Awaitable], *args, **kwargs) -> Future:  # type: ignore[override]
        """Schedule new async task.

        :param task: an async task to be scheduled
        :param args: args to pass to a task
        :param kwargs: kwargs to pass to a task
        """
        if self._stopped:
            raise InvalidStateError(f'The task was submitted after AsyncExecutor shutdown: {task}')
        return self._submit(task, *args, **kwargs)

    def sync_to_async(self, task: Callable, *args) -> asyncio.Future:
        """Run sync function in a thread pool executor and make it awaitable.

        :param task: an async task to be scheduled
        :param args: args to pass to a task
        """
        if self._stopped:
            raise InvalidStateError(f'The task was submitted after AsyncExecutor shutdown: {task}')
        return self._loop.run_in_executor(self._thread_executor, task, *args)

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """Stop the executor and cancel tasks if needed.

        :param wait: wait for tasks to be finished or stop immediately
        :param cancel_futures: notify tasks to be cancelled
        """
        if self._stopped:
            return

        self._stopped = True

        if cancel_futures:
            self.cancel_futures()

        def has_coroutines() -> bool:
            return bool(self._loop._ready or self._loop._scheduled)

        if wait:
            while has_coroutines():
                self._release_gil()

        self._loop.stop()

        while self._loop.is_running():
            self._release_gil()

        self._loop.close()
        self._thread.join()

    def cancel_futures(self) -> None:
        """Cancel all running tasks."""
        for task in self.tasks:
            task.cancel()

    @property
    def _thread_executor(self) -> ThreadPoolExecutor:
        return self._loop._default_executor

    def _submit(self, task: Callable[..., Awaitable], *args, **kwargs) -> Future:
        coroutine = task(*args, **kwargs)
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    @staticmethod
    def _release_gil() -> None:
        """Release the GIL to let async thread make an iteration."""
        time.sleep(0)
