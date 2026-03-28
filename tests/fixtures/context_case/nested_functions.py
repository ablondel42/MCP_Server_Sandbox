"""Nested functions for context testing."""


def outer_function(x: int) -> int:
    """Outer function containing nested function."""
    
    def inner_helper(y: int) -> int:
        """Inner helper function."""
        return y + 1
    
    def another_inner(z: int) -> int:
        """Another inner function."""
        return z * 2
    
    result = inner_helper(x)
    result = another_inner(result)
    return result


async def async_outer(data: str) -> str:
    """Async outer function."""
    
    async def async_inner(s: str) -> str:
        """Async inner function."""
        return s.upper()
    
    return await async_inner(data)
