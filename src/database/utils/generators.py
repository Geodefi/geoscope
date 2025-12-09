"""
Functions that generate SQL statements for creating, dropping,
and inserting into database tables based on the schemas defined in `schemas.py`.
"""

from dataclasses import dataclass

from src.database.utils.helpers import get_table_schema, quote_identifier
from src.globals.constants.database import SCHEMA_CONSTRAINTS_KEY, SCHEMA_SQL_TYPE_KEY


@dataclass
class Condition:
    field: str
    operator: str


def generate_create_table_sql(table_key: str) -> str:
    """
    Generates a sanitized SQL 'CREATE TABLE' statement.

    Args:
        table_key (str): The key identifier for the table, also the table name.

    Returns:
        str: A SQL statement for creating the table with the specified fields.

    Raises:
        ValueError: If table_key is invalid, or table/field names contain invalid characters.
    """
    table_name_quoted = quote_identifier(table_key)

    schema = get_table_schema(table_key)
    fields_sql_parts = []

    for field_name, field_def in schema.items():
        field_name_quoted = quote_identifier(field_name)
        sql_type = field_def[SCHEMA_SQL_TYPE_KEY]
        constraints = field_def.get(SCHEMA_CONSTRAINTS_KEY, "")
        fields_sql_parts.append(f"{field_name_quoted} {sql_type} {constraints}".strip())

    fields_sql = ",\n    ".join(fields_sql_parts)

    return f"""
    CREATE TABLE IF NOT EXISTS {table_name_quoted} ({fields_sql});
    """


def generate_drop_table_sql(table_key: str) -> str:
    """
    Generates a sanitized SQL 'DROP TABLE' statement.

    Args:
        table_key (str): The key identifier for the table, also the table name.

    Returns:
        str: A SQL statement for dropping the table if it exists.

    Raises:
        ValueError: If table_key is invalid, or table/field names contain invalid characters.
    """
    table_name_quoted = quote_identifier(table_key)
    return f"""
    DROP TABLE IF EXISTS {table_name_quoted};
    """


def generate_insert_sql(table_key: str, only_not_null_fields: bool = False) -> str:
    """
    Generates a SQL 'INSERT INTO' statement with named placeholders.

    Args:
        table_key (str): The key identifier for the table.
        only_not_null_fields (bool, optional): If True, include only fields whose schema constraints
            include 'NOT NULL'. Defaults to False.

    Returns:
        str: A SQL statement for inserting into the table using named placeholders.

    Raises:
        ValueError: If table_key is invalid, or table/field names contain invalid characters.
    """
    table_name_quoted = quote_identifier(table_key)
    schema = get_table_schema(table_key)

    if only_not_null_fields:
        # Filter fields to include only those with 'NOT NULL' in constraints
        field_names = [
            name
            for name, field_def in schema.items()
            if "NOT NULL" in field_def.get(SCHEMA_CONSTRAINTS_KEY, "")
        ]
    else:
        field_names = list(schema.keys())

    field_names_quoted = [quote_identifier(name) for name in field_names]
    fields_sql = ", ".join(field_names_quoted)

    placeholders = [f":{name}" for name in field_names]
    placeholders_sql = ", ".join(placeholders)

    return f"""
    INSERT INTO {table_name_quoted} ({fields_sql}) VALUES ({placeholders_sql});
    """


def generate_count_sql(table_key: str) -> str:
    """
    Generates a SQL 'SELECT COUNT(*) FROM table' statement.

    Args:
        table_key (str): The key identifier for the table.

    Returns:
        str: A SQL statement for counting the number of records in the table.

    Raises:
        ValueError: If table_key contains invalid characters.
    """
    table_name_quoted = quote_identifier(table_key)
    return f"""
    SELECT COUNT(*) FROM {table_name_quoted};
    """


def generate_select_exists_sql(table_key: str, condition_field: str) -> str:
    """
    Generates a SQL 'SELECT 1 FROM table WHERE field = :field LIMIT 1' statement.

    Args:
        table_key (str): The key identifier for the table.
        condition_field (str): The field name to use in the WHERE clause and as the placeholder.

    Returns:
        str: A SQL statement for checking if a record exists based on the condition.

    Raises:
        ValueError: If table_key or field names contain invalid characters.
    """
    table_name_quoted = quote_identifier(table_key)
    field_name_quoted = quote_identifier(condition_field)

    return f"""
        SELECT 1 FROM {table_name_quoted} WHERE {field_name_quoted} = :{condition_field} LIMIT 1;
        """


def generate_select_fields_sql(table_key: str, *field_names: str) -> str:
    """
    Generates a SQL 'SELECT field1, field2, ... FROM table' statement.

    Args:
        table_key (str): The key identifier for the table.
        *field_names (str): Variable length argument list of field names to select.

    Returns:
        str: A SQL statement for selecting specified fields from all records in the table.

    Raises:
        ValueError: If table_key or any of the field_names contain invalid characters.
    """
    table_name_quoted = quote_identifier(table_key)
    field_names_quoted = ", ".join(quote_identifier(field) for field in field_names)
    return f"""
    SELECT {field_names_quoted} FROM {table_name_quoted};
    """


def generate_select_fields_where_conditions_sql(
    table_key: str, conditions: list[Condition], *select_fields: str
) -> str:
    """
    Generates a SQL 'SELECT fields FROM table WHERE condition1 AND condition2 ...' statement.

    Args:
        table_key (str): The key identifier for the table.
        conditions (list[Condition]): List of conditions for the WHERE clause.
        *select_fields (str): Variable length argument list of field names to select.

    Returns:
        str: A SQL statement for selecting specified fields from the table with conditions.

    Raises:
        ValueError: If table_key, any field names, or operators are invalid or unsupported.
    """
    if not select_fields:
        raise ValueError("At least one select field must be provided.")
    if not conditions:
        raise ValueError("At least one condition must be provided.")

    table_name_quoted = quote_identifier(table_key)
    select_fields_quoted = ", ".join(quote_identifier(field) for field in select_fields)

    condition_clauses = []
    for condition in conditions:
        field_quoted = quote_identifier(condition.field)
        operator = condition.operator.upper()
        if operator in {"IS NULL", "IS NOT NULL"}:
            clause = f"{field_quoted} {operator}"
        elif operator in {"=", "!=", "<>", ">", "<", ">=", "<=", "LIKE"}:
            clause = f"{field_quoted} {operator} :{condition.field}"
        else:
            # Use the appropriate generator for 'IN' clauses.
            raise ValueError(f"Unsupported operator: {operator}")
        condition_clauses.append(clause)

    where_clause = " AND ".join(condition_clauses)

    return f"""
    SELECT {select_fields_quoted} FROM {table_name_quoted} WHERE {where_clause};
    """


def generate_select_fields_where_in_sql(
    table_key: str, select_fields: list[str], condition_field: str, num_values: int
) -> str:
    """
    Generates a SQL 'SELECT field1, field2 FROM table WHERE condition_field IN (?, ?, ...)' statement.

    Args:
        table_key (str): The key identifier for the table.
        select_fields (list[str]): The list of field names to select.
        condition_field (str): The field name to use in the WHERE IN clause.
        num_values (int): The number of values in the IN clause.

    Returns:
        str: A SQL statement for selecting fields from the table where the condition field is in a list.

    Raises:
        ValueError: If num_values is less than or equal to 0.
    """
    if num_values <= 0:
        raise ValueError("num_values must be greater than 0")

    table_name_quoted = quote_identifier(table_key)
    select_fields_quoted = ", ".join([quote_identifier(field) for field in select_fields])
    condition_field_quoted = quote_identifier(condition_field)

    placeholders = ", ".join(["?"] * num_values)
    sql = (
        f"SELECT {select_fields_quoted} FROM {table_name_quoted} "
        f"WHERE {condition_field_quoted} IN ({placeholders});"
    )
    return sql


def generate_update_where_conditions_sql(
    table_key: str, conditions: list[Condition], *set_fields: str
) -> str:
    """
    Generates a SQL 'UPDATE table SET field1 = :field1, field2 = :field2 WHERE condition1 AND condition2 ...;' statement.

    Args:
        table_key (str): The name of the table to update.
        conditions (list[Condition]): List of conditions for the WHERE clause.
        *set_fields (str): Variable length argument list of field names to set.

    Returns:
        str: A parameterized SQL UPDATE statement.

    Raises:
        ValueError: If table_key, set_fields, or conditions contain invalid characters or unsupported operators.
    """
    table_name_quoted = quote_identifier(table_key)
    set_clause = ", ".join(f"{quote_identifier(field)} = :{field}" for field in set_fields)

    condition_clauses = []
    for condition in conditions:
        field_quoted = quote_identifier(condition.field)
        operator = condition.operator.upper()
        if operator in {"IS NULL", "IS NOT NULL"}:
            clause = f"{field_quoted} {operator}"
        elif operator in {"=", "!=", "<>", ">", "<", ">=", "<=", "LIKE"}:
            clause = f"{field_quoted} {operator} :{condition.field}"
        else:
            raise ValueError(f"Unsupported operator: {operator}.")
        condition_clauses.append(clause)

    where_clause = " AND ".join(condition_clauses)

    return f"""
        UPDATE {table_name_quoted}
        SET {set_clause}
        WHERE {where_clause};
    """
