"""Nested functions test case - nested functions become local_function symbols."""


def outer(x: int) -> int:
    """Outer function."""
    
    def inner(y: int) -> int:
        """Nested function - should be local_function."""
        return y * 2
    
    return inner(x)


def outer_with_deep_nesting(x: int) -> int:
    """Outer function with deep nesting."""
    
    def level1(y: int) -> int:
        """Level 1 nested."""
        
        def level2(z: int) -> int:
            """Level 2 nested - deeply nested local_function."""
            return z * 3
        
        return level2(y)
    
    return level1(x)
