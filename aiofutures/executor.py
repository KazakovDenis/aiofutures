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
from itertools import count
from threading import Thread, get_ident, main_thread
from typing import Awaitable, Callable, Optional, Set

from .exceptions import AsyncExecutorError, InvalidStateError


class AsyncExecutor(Executor):
    """The executor that runs coroutines in a different thread."""
    _loop: asyncio.AbstractEventLoop
    _counter = count()

    def __init__(self, executor: Optional[ThreadPoolExecutor] = None) -> None:
        self._loop = asyncio.new_event_loop()
        self._name = f'{self.__class__.__name__}-{next(self._counter)}'
        self._stopped = False
        self._thread_executor = executor
        self._thread = Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()

    def __repr__(self) -> str:
        return f'<{self._name} stopped={self._stopped} tasks={len(self.tasks)}>'

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
            raise InvalidStateError(f'The task has been submitted after AsyncExecutor shutdown: {task}')
        return self._submit(task, *args, **kwargs)

    def sync_to_async(self, task: Callable, *args) -> asyncio.Future:
        """Run sync function in a thread pool executor and make it awaitable.

        :param task: an async task to be scheduled
        :param args: args to pass to a task
        """
        if self._stopped:
            raise InvalidStateError(f'The task has been submitted after AsyncExecutor shutdown: {task}')
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

        self._submit(self._stop)

        if wait:
            # This will wait for all tasks to complete and
            # a thread pool executor to shut down (see self._run)
            self._thread.join()

    def cancel_futures(self) -> None:
        """Cancel all running tasks."""
        for task in self.tasks:
            task.cancel()

    def _run(self) -> None:
        if get_ident() == main_thread().ident:
            raise AsyncExecutorError('Async worker has been tried to start in the main thread')

        if self._thread_executor:
            self._loop.set_default_executor(self._thread_executor)

        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            finalizer = asyncio.gather(*self.tasks, return_exceptions=True)
            self._loop.run_until_complete(finalizer)
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()

    def _submit(self, task: Callable[..., Awaitable], *args, **kwargs) -> Future:
        coroutine = task(*args, **kwargs)
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    async def _stop(self) -> None:
        self._loop.stop()
