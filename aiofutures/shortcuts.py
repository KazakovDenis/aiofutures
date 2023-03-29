import asyncio
import os
from concurrent.futures import Future
from typing import Awaitable, Callable

from .executor import AsyncExecutor


if os.getenv('AIOFUTURES_INIT'):
    _global_executor = AsyncExecutor()

    def run_async(func: Callable[..., Awaitable], *args, **kwargs) -> Future:
        """The single entrypoint to run async tasks in another thread.

        :param func: an async function to run in another thread
        :param args: args to pass to a func
        :param kwargs: kwargs to pass to a func
        """
        return _global_executor.submit(func, *args, **kwargs)

    def sync_to_async(func: Callable, *args) -> asyncio.Future:
        """Run sync function in a thread pool executor and make it awaitable.

        :param func: an async task to be scheduled
        :param args: args to pass to a task
        """
        return _global_executor.sync_to_async(func, *args)
