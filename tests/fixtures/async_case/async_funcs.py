"""Async function test case."""


async def fetch_user(user_id: int) -> dict:
    """Fetch a user by ID."""
    return {"id": user_id}


async def fetch_posts(user_id: int) -> list:
    """Fetch posts for a user."""
    return []


async def main() -> None:
    """Main async entry point."""
    user = await fetch_user(1)
    posts = await fetch_posts(user["id"])
    print(user, posts)


def sync_helper() -> str:
    """A synchronous helper function."""
    return "helper"


class AsyncService:
    """Service with async methods."""
    
    async def connect(self) -> bool:
        """Connect to the service."""
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from the service."""
        pass
    
    def sync_method(self) -> str:
        """A synchronous method."""
        return "sync"
