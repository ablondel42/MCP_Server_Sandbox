"""Sample module for graph storage testing."""

from typing import Optional


class UserService:
    """Service for managing users."""
    
    def __init__(self, name: str) -> None:
        """Initialize the service."""
        self.name = name
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Get a user by ID."""
        return {"id": user_id, "name": self.name}
    
    def create_user(self, name: str) -> dict:
        """Create a new user."""
        return {"id": 1, "name": name}


def process_data(data: str) -> str:
    """Process some data."""
    return data.upper()


async def fetch_remote(url: str) -> str:
    """Fetch data from a remote URL."""
    return "data"
