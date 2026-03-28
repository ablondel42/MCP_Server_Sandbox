"""Another module for graph storage testing."""

from sample_repo import UserService, process_data


class OrderService:
    """Service for managing orders."""
    
    def __init__(self) -> None:
        """Initialize the order service."""
        self.user_service = UserService("default")
    
    def create_order(self, user_id: int) -> dict:
        """Create an order for a user."""
        user = self.user_service.get_user(user_id)
        return {"user": user, "items": []}


def helper_function(x: int) -> int:
    """A helper function."""
    return x * 2


def nested_example():
    """Example with nested function."""
    
    def inner_helper(y: int) -> int:
        """Inner helper function."""
        return y + 1
    
    return inner_helper(5)
