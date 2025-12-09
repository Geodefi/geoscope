import threading
from functools import wraps
from multiprocessing.pool import ThreadPool
from typing import Any, Callable, Iterable

from src.classes.daemon import shutdown_event
from src.utils.progress_bar import progress_bar


class LockManager:
    """Simple lock manager for thread synchronization."""

    _lock = threading.Lock()
    a = 0

    @classmethod
    def push(cls) -> None:
        """Add function name to stack and return thread tree path."""
        with cls._lock:
            cls.a += 1

    @classmethod
    def pop(cls) -> None:
        """Remove last function name from stack."""
        with cls._lock:
            cls.a -= 1


def rename_worker(fn: Callable) -> Callable:
    """
    Creates a Wrapper to change the worker name by appending the function name
    to the current thread name.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        w = fn(*args, **kwargs)
        w.name = w.name.replace("Thread", f"{(threading.current_thread()).name}")
        return w

    return wrapper


ThreadPool.Process = staticmethod(rename_worker(ThreadPool.Process))  # type: ignore


def multithread(func: Callable, *args: Iterable[Any]) -> list[Any]:
    """Executes a function in a multithreaded way over iterable arguments with a progress bar.

    Args:
        func (Callable): The function to be executed.
        *args: Iterables of arguments to pass to the function.

    Returns:
        list[Any]: List of results from the function executions.
    """
    LockManager.push()

    def wrapped_func(*args: Any) -> Callable:
        # Update current thread name for logging
        thread = threading.current_thread()
        thread.name = thread.name.replace("(worker)", f"-> {func.__name__}")
        return func(*args)

    results = []

    try:
        arguments = list(zip(*args))
        total_tasks = len(arguments)

        pbar = progress_bar(
            total=total_tasks, desc=threading.current_thread().name + f"-> {func.__name__}"
        )

        with ThreadPool() as pool:
            try:
                async_results = []
                # Convert func to wrapped_func
                for arg_set in arguments:
                    res = pool.apply_async(
                        wrapped_func, args=arg_set, callback=lambda _: pbar.update(1)
                    )
                    async_results.append(res)

                for res in async_results:
                    try:
                        # Here we need to raise rather than handle directly,
                        # so it can also handle shutdown on child threads
                        # where .get() call can also raise.
                        if shutdown_event.is_set():
                            raise KeyboardInterrupt

                        results.append(res.get(timeout=60))
                    except KeyboardInterrupt as e:
                        # Needed, handles shutdown gracefully on main thread
                        pool.terminate()
                        raise e

            except KeyboardInterrupt as e:
                pool.terminate()
                raise e

            else:
                pool.close()

            finally:
                pool.join()

        return results

    finally:
        if pbar:
            pbar.clear()  # Ensure bar is cleared
            pbar.close()  # Ensure bar is closed

        LockManager.pop()


def multithread_old(func: Callable, *args: Any) -> list[Any]:
    """Turn function calls into multithread with help of iterables arguments and return the results.

    Args:
        func (Callable): function to be called
        *args: arguments to be passed to the function
        num_threads (int, optional): number of threads to be used. Defaults to None,
            which spams as many proceeses as possible.
        chunk_size (int, optional): size of the chunk. Defaults to 1.

    Returns:
        list[Any]: list of results from the function calls
    """
    with ThreadPool(processes=None) as pool:
        res: Any = pool.starmap(func, zip(*args), chunksize=1)

    return list(res)
