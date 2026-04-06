"""Contract validation utilities.

Provides reusable schema validation helpers for validating
required fields, field types, enum values, and payload shapes.
"""

from typing import Any


def validate_required_fields(
    payload: dict[str, Any],
    required_fields: list[str],
    context: str = "",
) -> list[str]:
    """Validate that all required fields are present in a payload.

    Args:
        payload: Dictionary to validate.
        required_fields: List of field names that must be present.
        context: Optional context string for error messages.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []
    prefix = f"{context}: " if context else ""
    for field_name in required_fields:
        if field_name not in payload:
            errors.append(f"{prefix}Missing required field: {field_name}")
    return errors


def validate_field_types(
    payload: dict[str, Any],
    expected_types: dict[str, type],
    context: str = "",
) -> list[str]:
    """Validate that fields have expected types.

    Args:
        payload: Dictionary to validate.
        expected_types: Map of field name to expected type.
        context: Optional context string for error messages.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []
    prefix = f"{context}: " if context else ""
    for field_name, expected_type in expected_types.items():
        if field_name not in payload:
            continue
        value = payload[field_name]
        if value is None:
            continue  # None is acceptable for optional fields
        if not isinstance(value, expected_type):
            errors.append(
                f"{prefix}Field '{field_name}' expected type {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
    return errors


def validate_enum_values(
    value: Any,
    allowed_values: list[str],
    context: str = "",
) -> list[str]:
    """Validate that a value is one of the allowed enum values.

    Args:
        value: Value to validate.
        allowed_values: List of allowed string values.
        context: Optional context string for error messages.

    Returns:
        List of error messages (empty if valid).
    """
    if value in allowed_values:
        return []
    prefix = f"{context}: " if context else ""
    return [f"{prefix}Value '{value}' not in allowed values: {allowed_values}"]


def validate_nested_list(
    payload: dict[str, Any],
    field_name: str,
    required_item_fields: list[str] | None = None,
    context: str = "",
) -> list[str]:
    """Validate that a field is a list and optionally that items have required fields.

    Args:
        payload: Dictionary to validate.
        field_name: Name of the list field.
        required_item_fields: Optional list of fields each item must have.
        context: Optional context string for error messages.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []
    prefix = f"{context}: " if context else ""

    if field_name not in payload:
        return [f"{prefix}Missing required field: {field_name}"]

    items = payload[field_name]
    if not isinstance(items, list):
        return [f"{prefix}Field '{field_name}' expected list, got {type(items).__name__}"]

    if required_item_fields:
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{prefix}Item {i} in '{field_name}' expected dict, got {type(item).__name__}")
                continue
            for req_field in required_item_fields:
                if req_field not in item:
                    errors.append(f"{prefix}Item {i} in '{field_name}' missing field: {req_field}")

    return errors


def validate_stable_id(
    value: str,
    prefix: str,
    context: str = "",
) -> list[str]:
    """Validate that a value is a stable ID with expected prefix.

    Args:
        value: ID string to validate.
        prefix: Expected ID prefix (e.g., 'sym:', 'file:', 'edge:').
        context: Optional context string for error messages.

    Returns:
        List of error messages (empty if valid).
    """
    if value.startswith(prefix):
        return []
    prefix_msg = f"{context}: " if context else ""
    return [f"{prefix_msg}ID '{value}' does not start with expected prefix '{prefix}'"]
