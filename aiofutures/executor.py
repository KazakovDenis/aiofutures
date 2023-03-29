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
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from threading import Thread
from typing import Awaitable, Callable, Optional

from .exceptions import InvalidStateError


class AsyncExecutor(Executor):
    """The executor that runs coroutines in a different thread."""

    def __init__(self, executor: Optional[ThreadPoolExecutor] = None) -> None:
        def run():
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._stopped = False
        self._loop = asyncio.new_event_loop()
        if executor:
            self._loop.set_default_executor(executor)

        self._thread = Thread(target=run, name=self.__class__.__name__, daemon=True)
        self._thread.start()

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
        return self._loop.run_in_executor(None, task, *args)

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """Stop the executor and cancel tasks if needed.

        :param wait: wait for tasks to be finished or stop immediately
        :param cancel_futures: notify tasks to be cancelled
        """
        # as said in Executor it may be called several times
        if self._stopped:
            return

        self._stopped = True
        self._loop.stop()

        if cancel_futures:
            self.cancel_futures()

        self._submit(self._stop_loop, not wait)
        del self._loop, self._thread

    def cancel_futures(self) -> None:
        """Cancel all running tasks."""
        for task in asyncio.all_tasks(self._loop):
            task.cancel()

    def _submit(self, task: Callable[..., Awaitable], *args, **kwargs) -> Future:
        coroutine = task(*args, **kwargs)
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    @staticmethod
    async def _stop_loop(force: bool) -> None:
        """Force an iteration in the loop to meet stop condition."""
        if force:
            raise KeyboardInterrupt
