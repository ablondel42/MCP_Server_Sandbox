"""Decorators test case."""

from functools import wraps
from typing import Callable, Any


def logged(func: Callable) -> Callable:
    """Log function calls."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper


def cached(func: Callable) -> Callable:
    """Cache function results."""
    cache: dict = {}
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    return wrapper


@logged
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"


@logged
@cached
def compute(x: int, y: int) -> int:
    """Compute a result."""
    return x + y


@cached
class CachedClass:
    """A class with caching decorator."""
    
    def __init__(self, value: int) -> None:
        self.value = value
    
    @logged
    def get_value(self) -> int:
        """Get the value."""
        return self.value
