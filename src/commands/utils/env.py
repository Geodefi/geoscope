import os
from typing import Any

import click


def set_env_var(ctx: click.Context, _option: click.Parameter, value: Any) -> Any:
    """
    Sets an environment variable based on the provided option value.

    This function is used as a callback for envvar based options, assigning the given value
    to the corresponding environment variable. If the value is not provided or
    resilient parsing is enabled, the function exits without making changes.

    Args:
        ctx (click.Context): The Click context object, representing the current command-line
                             execution context.
        _option (click.Parameter): The Click parameter object associated with the option
                                   invoking this callback. Its `envvar` attribute specifies
                                   the environment variable name to be set.
        value (Any): The value to be assigned to the environment variable. It is converted
                     to a string before being set.

    Returns:
        None: The function does not return a value but modifies the environment variables
              in the current process.
    """

    if not value or ctx.resilient_parsing:
        return
    key = str(_option.envvar)
    os.environ[key] = str(value)  # overrides current envvars.
    return value
