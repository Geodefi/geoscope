from typing import Any

import click


class CustomParamType(click.ParamType):
    """
    Base class for custom parameter types used with Click commands.

    Attributes:
        name (str): The name of the parameter type.
    """

    name: str


class ListParamType(CustomParamType):
    """
    Parameter type for Click commands that accepts a delimited string and converts it into a list.

    Args:
        param_type (click.ParamType): The underlying type of the list elements.
        separator (str, optional): The delimiter used to split the input string. Defaults to ",".
        name (str, optional): The name of the parameter type. Defaults to the class name.
        ignore_empty (bool, optional): Whether to ignore empty strings and return an empty list.
        Defaults to False.

    Raises:
        TypeError: If the separator is not a string.

    Methods:
        _strip_separator(expression: str) -> str:
            Removes leading and trailing separator characters from the input string.

        _convert_expression_to_list(expression: str) -> tuple[list[str], Any]:
            Splits and converts the input string into a list of the specified parameter type.
            Returns a tuple containing errors (invalid items) and the converted list.

        convert(value: Any, param: click.Parameter | None, ctx: click.Context | None) -> Any:
            Required for click package.
            Converts the input value into a list, performing validation and error handling.

        __repr__() -> str:
            Returns the name of the parameter type in uppercase.
    """

    def __init__(
        self,
        param_type: click.ParamType,
        separator: str = ",",
        name: str | None = None,
        ignore_empty: bool = False,
    ):
        if not isinstance(separator, str):
            raise TypeError("separator must be a string")
        self._separator = separator
        self._name = name or self.name
        self._param_type = param_type
        self._error_message = "These items are not %s: {errors}" % self._name
        self._ignore_empty = ignore_empty

    def _strip_separator(self, expression: str) -> str:
        """
        Removes leading and trailing occurrences of the separator from the input string.

        Args:
            expression (str): The input string.

        Returns:
            str: The stripped string.
        """
        return expression.strip(self._separator)

    def _convert_expression_to_list(self, expression: str) -> tuple[list[str], Any]:
        """
        Converts expression and returns a tuple (errors, converted_items)
        where errors is a list of non-compliant items
        and converted_items is the list of converted expression items.

        Args:
            expression (str): The string to convert.

        Returns:
            tuple[list[str], Any]: A tuple containing a list of errors (invalid items)
            and the converted list.
        """
        errors = []
        converted_items = []
        for item in expression.split(self._separator):
            try:
                converted_items.append(self._param_type.convert(item, None, None))
            except click.BadParameter:
                errors.append(item)
        return errors, converted_items

    def convert(
        self,
        value: Any,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> Any:
        """
        Converts the input value into a validated list, handling errors and empty values.

        Args:
            value (Any): The input value to be converted.
            param (click.Parameter | None): The Click parameter object, if provided.
            ctx (click.Context | None): The Click context object, if provided.

        Returns:
            Any: The converted list or raises a Click error if validation fails.

        Raises:
            click.BadParameter: If any element in the input string fails validation.
        """

        # if a value is already converted, we returned it
        if isinstance(value, list):
            return value

        if self._ignore_empty and value == "":
            return []
        value = self._strip_separator(value)
        errors, converted_list = self._convert_expression_to_list(value)
        if errors:
            self.fail(self._error_message.format(errors=errors), param, ctx)

        return converted_list

    def __repr__(self) -> str:
        return self.name.upper()


class StringListParamType(ListParamType):
    """
    Parameter type for Click commands that accepts a delimited string
    and converts it into a list of strings.

    Args:
        separator (str, optional): The delimiter used to split the input string. Defaults to ",".
        ignore_empty (bool, optional): Whether to ignore empty strings and return an empty list.
        Defaults to False.
    """

    name = "string list"

    def __init__(self, separator: str = ",", ignore_empty: bool = False):
        super().__init__(click.STRING, separator, ignore_empty=ignore_empty)
