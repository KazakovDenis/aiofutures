# These exceptions are also used with aiofutures
from concurrent.futures import CancelledError, TimeoutError  # noqa: F401


class AsyncExecutorError(Exception):
    pass


class InvalidStateError(AsyncExecutorError):
    pass
