"""Nested functions test case - nested functions should be IGNORED."""


def outer_function(x: int) -> int:
    """Outer function that contains nested functions."""
    
    def nested_helper(y: int) -> int:
        """This nested function should NOT be extracted."""
        return y * 2
    
    def another_nested(z: int) -> int:
        """Another nested function that should NOT be extracted."""
        return z + 1
    
    result = nested_helper(x)
    result = another_nested(result)
    return result


async def async_outer(data: str) -> str:
    """Async outer function with nested functions."""
    
    async def async_nested(s: str) -> str:
        """Nested async function - should NOT be extracted."""
        return s.upper()
    
    def sync_nested(s: str) -> str:
        """Nested sync function inside async - should NOT be extracted."""
        return s.lower()
    
    return async_nested(data)


class OuterClass:
    """Class with methods containing nested functions."""
    
    def method_with_nested(self, x: int) -> int:
        """Method with nested function - nested should NOT be extracted."""
        
        def inner(y: int) -> int:
            """Inner function - should NOT be extracted."""
            return y * 2
        
        return inner(x)
    
    def simple_method(self) -> str:
        """Simple method without nested functions."""
        return "simple"
