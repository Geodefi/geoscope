from concurrent.futures import ThreadPoolExecutor


def multithread(func, *args, num_threads: int = None, chunksize: int = 1):
    """
    turn function calls into multithread with help of iterables arguments
    """
    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        res = pool.map(func, *args, chunksize=chunksize)
    return list(res)
