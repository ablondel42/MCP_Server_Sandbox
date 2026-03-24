"""Common types: Position and Range."""

import json
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any


@dataclass(frozen=True)
class Position:
    """A position in a file (zero-based)."""

    line: int
    character: int


@dataclass(frozen=True)
class Range:
    """A range in a file."""

    start: Position
    end: Position


def to_json(value: Any) -> str:
    """Serialize a value to JSON string.
    
    Args:
        value: The value to serialize. Can be a dataclass, dict, list, or primitive.
        
    Returns:
        JSON string with sorted keys.
    """
    if is_dataclass(value):
        return json.dumps(asdict(value), sort_keys=True)
    return json.dumps(value, sort_keys=True)


def from_json(data: str) -> Any:
    """Deserialize a JSON string to a Python object.
    
    Args:
        data: JSON string to deserialize.
        
    Returns:
        Deserialized Python object (dict, list, or primitive).
    """
    return json.loads(data)
