# -*- coding: utf-8 -*-

from typing import Any, Callable
from multiprocessing.pool import ThreadPool
from threading import current_thread
from functools import wraps

from src.globals import get_logger


def rename_worker(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):
        w = fn(*args, **kwargs)
        w.name = w.name.replace("Thread", (current_thread()).name)
        return w

    return wrapper


ThreadPool.Process = staticmethod(rename_worker(ThreadPool.Process))


def multithread(func: Callable, *args, num_threads: int = None, chunk_size: int = 1) -> list[Any]:
    """Turn function calls into multithread with help of iterables arguments and return the results.

    Args:
        func (Callable): function to be called
        *args: arguments to be passed to the function
        num_threads (int, optional): number of threads to be used. Defaults to None.
        chunk_size (int, optional): size of the chunk. Defaults to 1.

    Returns:
        list[Any]: list of results from the function calls
    """
    get_logger().debug(f"Calling {func.__name__:^21} multithreaded.")
    with ThreadPool(processes=num_threads) as pool:
        res: Any = pool.starmap(func, zip(*args), chunksize=chunk_size)

    return list(res)
