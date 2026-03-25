"""Mixed nesting test case - combination of nested funcs, async, and local classes."""


async def async_outer(data: str) -> str:
    """Async outer function."""
    
    async def async_inner(s: str) -> str:
        """Nested async function - local_async_function."""
        return s.upper()
    
    def sync_helper(s: str) -> str:
        """Nested sync function - local_function."""
        return s.lower()
    
    class LocalFormatter:
        """Local class in async function."""
        
        def format(self, text: str) -> str:
            """Method in local class."""
            return f"[{text}]"
    
    return await async_inner(data)


def mixed_container():
    """Function with mixed nested declarations."""
    
    def nested_func():
        """Nested function."""
        pass
    
    async def nested_async():
        """Nested async function."""
        pass
    
    class NestedClass:
        """Nested class."""
        
        def method(self):
            """Method in nested class."""
            pass
    
    return nested_func
