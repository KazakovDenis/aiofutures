from threading import Thread
from typing import Callable


def run_thread(func: Callable, *args) -> Thread:
    t = Thread(target=func, args=args)
    t.start()
    return t
