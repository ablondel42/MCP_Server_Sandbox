"""Module with function for context testing."""

from typing import Optional


def module_function(x: int) -> int:
    """A module-level function."""
    return x * 2


async def async_module_function(data: str) -> str:
    """An async module-level function."""
    return data.upper()
