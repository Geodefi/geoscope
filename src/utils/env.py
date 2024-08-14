# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv


def load_env(ctx, _option, value):
    if ctx.resilient_parsing:
        return value
    # Should not override the key-value pairs if they exists
    # since we allow .env pairs to be flags or env vars.
    # Thus, --main-dir which loads .env is not eager but
    # the flags corresponding to the .env pairs are.
    load_dotenv(os.path.join(value, ".env"), override=False)
    return value


def __set_env_var(key: str, value: str):
    os.environ[str(key)] = str(value)


def set_x(ctx, _option, value):
    if not value or ctx.resilient_parsing:
        return

    __set_env_var("x", value)
