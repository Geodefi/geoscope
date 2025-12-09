import random
from time import sleep
from typing import Iterable

from tqdm import tqdm


def __get_random_color(pastel_factor: float = 0.5) -> str:
    rgb: list[float] = [
        (x + pastel_factor) / (1.0 + pastel_factor)
        for x in [random.uniform(0, 1.0) for i in [1, 2, 3]]
    ]
    rgb_hex = "#%02x%02x%02x" % (
        int(rgb[0] * 255),
        int(rgb[1] * 255),
        int(rgb[2] * 255),
    )
    return rgb_hex


# TODO:(crash) can we add more progress_bars? Any suggestions?
def progress_bar(
    desc: str | None = None,
    unit: str | None = None,
    total: int | None = None,
    iterable: Iterable | None = None,
    colour: str | None = None,
    show_percentage: bool = False,
    show_iter: bool = True,
    show_time: bool = True,
    leave: bool = False,
) -> tqdm:
    """
    Create a customized tqdm progress bar.

    Args:
        desc (str, optional): Description to display alongside the progress bar.
        unit (str, optional): Unit of measurement for each iteration.
        total (int, optional): Total number of iterations.
        iterable (Iterable, optional): An iterable object to wrap with the progress bar.
        colour (str, optional): Hex color code for the progress bar.
            Default is RANDOM.
        leave (bool, False): Whether to leave the progress bar on the screen after completion.
            Default is False.
        show_percentage (bool, optional): Whether to display the completion percentage.
            Default is True.
        show_iter (bool, optional): Whether to display iteration counts.
            Default is True.
        show_time (bool, optional): Whether to display elapsed and remaining time.
            Default is True.


    Returns:
        tqdm: A tqdm progress bar object.
    """
    bar_format: str = ""
    if desc:
        bar_format += "[{desc}] "

    if show_percentage:
        bar_format += "{percentage:3.1f}%|"

    bar_format += "{bar}"

    if show_time and show_iter:
        bar_format += " [{n_fmt}/{total_fmt}{unit} " + "| {elapsed}/{remaining}]"
    elif show_iter:
        bar_format += " [{n_fmt}/{total_fmt}{unit}]"
    elif show_time:
        bar_format += " [{elapsed}/{remaining}]"

    if unit is None:
        unit = ""

    if colour is None:
        colour = __get_random_color()

    return tqdm(
        desc=desc,
        unit=unit,
        total=total,
        iterable=iterable,
        colour=colour,
        leave=leave,
        bar_format=bar_format,
        miniters=1,
    )


def time_bar(duration: int, desc: str | None = None) -> None:
    """
    Display a progress bar that lasts for a specified duration.

    Args:
        duration (int): Duration of the progress bar in seconds.
        desc (str, optional): Description to display alongside the progress bar.
    """
    pbar = progress_bar(
        total=duration, desc=desc, leave=True, unit="s", show_iter=False, show_time=True
    )
    try:
        for _ in range(duration):
            sleep(1)
            pbar.update(1)
    finally:
        if pbar:
            pbar.clear()  # Ensure bar is cleared
            pbar.close()  # Ensure bar is closed
