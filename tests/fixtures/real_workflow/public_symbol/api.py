"""Public API module with heavily referenced symbols."""


class PublicAPI:
    """Public API class referenced by many modules."""

    def do_something(self):
        """Public method."""
        return "done"


def public_function():
    """Public function referenced by many modules."""
    api = PublicAPI()
    return api.do_something()
