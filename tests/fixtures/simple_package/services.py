"""Simple package for testing AST extraction.

This module has a docstring for testing.
"""

from typing import Optional


class BaseService:
    """Base service class for testing."""
    
    def __init__(self, name: str) -> None:
        """Initialize the service."""
        self.name = name
    
    def process(self, data: str) -> str:
        """Process the input data."""
        return data.upper()


class AuthService(BaseService):
    """Authentication service."""
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate a user."""
        return True
    
    def logout(self) -> None:
        """Log out the current user."""
        pass


def create_service(name: str) -> BaseService:
    """Create a new service instance."""
    return BaseService(name)


async def fetch_data(url: str) -> Optional[str]:
    """Fetch data from a URL."""
    return None
