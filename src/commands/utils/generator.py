import json
import os
from typing import Any, Callable

import click

from src.globals import get_config, set_config
from src.globals.constants.config import (
    CHAIN_NAME_FIELD,
    EXPECTED_VERSION,
    MAIN_DIR_FIELD,
    VERSION_KEY,
)
from src.utils.dict import get_nested_value, set_nested_value

# pylint: disable=global-statement
CONFIG_CHANGED: bool = False
FLAT_VALUES: dict = {}


def __save_config(ctx: click.Context, _option: click.Parameter, value: Any) -> Any:

    if ctx.resilient_parsing:
        return value

    global CONFIG_CHANGED
    global FLAT_VALUES

    if CONFIG_CHANGED:

        if not value:
            value = click.prompt(
                "Would you like to save the new config.json with the applied flags"
                " and confirmed changes?"
                " (Environment values will not be overriden or revealed)",
                default=True,
                type=click.BOOL,
            )

        if value:
            new_config = {
                VERSION_KEY: EXPECTED_VERSION,
                get_config(field=CHAIN_NAME_FIELD): FLAT_VALUES,
            }
            config_path = os.path.join(get_config(field=MAIN_DIR_FIELD), "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f)

    del FLAT_VALUES
    del CONFIG_CHANGED
    return value


def __parse_template(template: dict[str, dict]) -> list[dict]:
    """
    Converts a nested template dictionary into a flat list of dictionaries
    suitable for Click options generation.

    :param template: Nested dictionary containing option configurations.
    :return: List of dictionaries with 'name', 'help', 'type', and optionally 'default' keys.
    """
    options = []

    def process_template(prefix: str, data: Any) -> None:
        for key, value in data.items():
            if isinstance(value, dict):
                if "type" in value and "help" in value:
                    # Check if this is a leaf node (has type and help)
                    option = {
                        "name": f"{prefix}.{key}" if prefix else key,
                        "help": value.get("help", ""),
                        "type": value.get("type"),
                        "default": value.get("default", None),
                        "mutator": value.get("mutator", None),
                        "verifier": value.get("verifier", None),
                    }
                    options.append(option)
                else:
                    # Recurse into nested dictionary
                    process_template(f"{prefix}.{key}" if prefix else key, value)

    process_template("", template)
    return options


def __populate_option_decorators(options: list[dict]) -> Callable:
    """
    Decorator to generate Click options from a list of dictionaries.
    Uses a callback to handle config and default logic.

    Args:
        options: List of dicts containing 'name', 'help', and 'type' keys.

    """

    def decorator(func: Callable) -> Callable:

        # Process options generated from template:
        for option in options:
            callback = __callback_factory(option)
            func = click.option(
                f"--{option['name']}".replace(".", "-").replace("_", "-"),
                help=option.get("help", ""),
                type=option.get("type", click.STRING),
                callback=callback,
                show_default=True,
            )(func)

        # Add default options --silent and --save, since we are using it in this file below.
        func = click.option(
            "--silent",
            is_flag=True,
            is_eager=True,
            required=False,
            default=False,
            help="""Normally user is prompted for the missing parts in the configuration.
            Instead, accepts default values or fails if no default exists.""",
        )(func)
        func = click.option(
            "--save",
            is_flag=True,
            is_eager=False,
            required=False,
            default=False,
            callback=__save_config,
            help="Save the new configuration to a config.json."
            " Same flags will be applied on the next run.",
        )(func)

        return func

    return decorator


def __callback_factory(option_template: dict[str, Any]) -> Callable:
    """
    Returns a callback function for click.option that:
    1) If CLI value is not None, set to config and return.
    2) If CLI value is None:
       - Check config, if config has a valid value (convertible by option_type), use it.
       - If no config value or invalid: check if template has a default:
         * If default present, ask user if they want to set it.
           If yes, set in config and use it.
           If no, abort.
       - If no default present, abort.
    """

    def callback(ctx: click.Context, _option: click.Parameter, value: Any) -> Any:
        silent = ctx.params["silent"]
        config = get_config()
        option_path = option_template["name"].split(".")
        template_type: click.ParamType = option_template["type"]

        new_value = value

        global CONFIG_CHANGED
        if value is None:
            # CLI did not provide a value, try config
            config_val = get_nested_value(config, option_path, abort=False)

            if config_val is None:
                CONFIG_CHANGED = True
                # No config value, check default
                template_default = option_template.get("default", None)

                if template_default is None:
                    if silent:
                        ctx.fail(
                            f"Value {template_default} for {option_template['name']} is invalid."
                        )
                    else:
                        new_value = click.prompt(
                            f"No value provided for {option_template['name']}:"
                            "\n{option_template['help']}"
                            "\nThere are no default values as well. Please provide a value",
                            default=template_default,
                            type=template_type,
                        )
                else:
                    if silent:
                        new_value = template_default
                    else:
                        new_value = click.prompt(
                            f"No value provided for {option_template['name']}:"
                            "\n{option_template['help']}"
                            "\nPress enter to use default value or provide a value",
                            default=template_default,
                            type=template_type,
                        )

            else:
                new_value = config_val

        else:
            CONFIG_CHANGED = True

        checked_val = template_type.convert(value=new_value, param=_option, ctx=ctx)

        if checked_val is None:
            ctx.fail(f"Value {template_default} for {option_template['name']} is invalid.")

        # In case --save is provided we should keep the changed values recorded before mutating
        # the value with a mutator, so we don't reveal .env values.
        global FLAT_VALUES
        FLAT_VALUES = set_nested_value(FLAT_VALUES, option_path, checked_val)

        # If a mutator callback is provided in the template, call it before setting the config
        mutator: Callable | None = option_template.get("mutator", None)
        if mutator is not None and callable(mutator):
            checked_val = mutator(checked_val)

        new_config = set_nested_value(config, option_path, checked_val)
        set_config(new_config)

        # If a verifier callback is provided in the template, call it after setting the config
        # Currently not utilized.
        verifier: Callable | None = option_template.get("verifier", None)
        if verifier is not None and callable(verifier):
            verifier()

        return checked_val

    return callback


def generate_options(template: dict[str, dict]) -> Callable:
    """
    Generates Click options based on a provided template.

    Parses a nested dictionary template into Click options and applies them as
    decorators to a target function.

    Args:
        template (dict[str, dict]): Nested dictionary defining option configurations.

    Returns:
        Callable: A decorator that applies the generated Click options.
    """

    options = __parse_template(template)
    decorators = __populate_option_decorators(options)
    return decorators
