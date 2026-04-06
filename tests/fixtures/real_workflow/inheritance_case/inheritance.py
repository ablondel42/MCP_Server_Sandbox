"""Module with class inheritance."""


class Base:
    """Base class."""

    def base_method(self):
        """Method on base class."""
        return "base"


class Derived(Base):
    """Derived class that inherits from Base."""

    def derived_method(self):
        """Method on derived class."""
        return self.base_method() + " derived"
