"""Local classes test case - classes inside functions become local symbols."""


def factory():
    """Factory function with local class."""
    
    class LocalClass:
        """Local class inside function."""
        
        def method(self) -> str:
            """Method in local class."""
            return "value"
        
        def helper(self, x: int) -> int:
            """Another method in local class."""
            return x * 2
    
    return LocalClass()


def another_factory():
    """Another factory with local class."""
    
    class AnotherLocal:
        """Another local class."""
        pass
    
    return AnotherLocal()
