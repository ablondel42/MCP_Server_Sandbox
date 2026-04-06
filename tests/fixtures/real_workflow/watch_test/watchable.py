"""File for watch mode invalidation testing."""


def watched_function():
    """Function that will be modified during watch tests."""
    return "original"


class WatchedClass:
    """Class that will be modified during watch tests."""

    def get_value(self):
        """Get the value."""
        return 1
