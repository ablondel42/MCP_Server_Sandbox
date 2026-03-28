"""Common types: Position and Range."""

import json
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any


@dataclass(frozen=True)
class Position:
    """A position in a file (zero-based).
    
    Attributes:
        line: Zero-based line number.
        character: Zero-based character offset within the line.
    """

    # Note: line and character are zero-based.
    line: int
    character: int


@dataclass(frozen=True)
class Range:
    """A range in a file.
    
    Attributes:
        start: Starting position (inclusive).
        end: Ending position (exclusive).
    """

    start: Position
    end: Position


def to_json(value: Any) -> str:
    """Serialize a value to JSON string."""
    if is_dataclass(value):
        if isinstance(value, type):
            raise TypeError("to_json expects a dataclass instance, not a dataclass class")
        return json.dumps(asdict(value), sort_keys=True)
    return json.dumps(value, sort_keys=True)


def from_json(data: str) -> Any:
    """Deserialize a JSON string to a Python object."""
    return json.loads(data)
