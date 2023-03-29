# These exceptions are also used with aiofutures
from concurrent.futures import CancelledError, TimeoutError  # noqa: F401


class InvalidStateError(Exception):
    pass
