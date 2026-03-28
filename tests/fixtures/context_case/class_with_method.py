"""Class with method for context testing."""


class Calculator:
    """A calculator class."""
    
    def __init__(self, initial_value: int = 0) -> None:
        """Initialize the calculator."""
        self.value = initial_value
    
    def add(self, x: int) -> int:
        """Add a value."""
        self.value += x
        return self.value
    
    def multiply(self, x: int) -> int:
        """Multiply by a value."""
        self.value *= x
        return self.value
    
    def get_value(self) -> int:
        """Get current value."""
        return self.value
