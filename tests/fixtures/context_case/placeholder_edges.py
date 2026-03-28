"""Module with placeholder edges for context testing."""

from typing import Optional
from external_module import ExternalClass, external_function
from another.external import something


class LocalService:
    """Local service using external dependencies."""
    
    def __init__(self) -> None:
        """Initialize with external class."""
        self.external = ExternalClass()
    
    def process(self, data: str) -> Optional[str]:
        """Process using external function."""
        return external_function(data)
    
    def fetch(self) -> object:
        """Fetch using another external."""
        return something.fetch()
