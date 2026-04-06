"""Module with nested scope (local functions)."""


def outer():
    """Outer function with local functions."""

    def inner_a():
        """Local function A."""
        return "a"

    def inner_b():
        """Local function B."""
        return inner_a() + "b"

    return inner_b()


class Container:
    """Class with local methods."""

    def method_with_local(self):
        """Method with a local function inside."""

        def local_helper():
            """Local helper function."""
            return 42

        return local_helper()
