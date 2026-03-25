"""Inheritance test case."""


class Animal:
    """Base animal class."""
    pass


class Mammal(Animal):
    """Mammal class."""
    pass


class Bird(Animal):
    """Bird class."""
    pass


class Dog(Mammal):
    """Dog class inheriting from Mammal."""
    pass


class Cat(Mammal):
    """Cat class inheriting from Mammal."""
    pass


class Parrot(Bird):
    """Parrot class inheriting from Bird."""
    pass


class MultiInherit(Dog, Cat):
    """Class with multiple inheritance."""
    pass
