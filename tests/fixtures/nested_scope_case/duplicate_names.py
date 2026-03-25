"""Duplicate names test case - same-scope duplicate declarations."""


def outer_with_duplicates():
    """Outer function with duplicate inner names."""
    
    def inner():
        """First inner - should get disambiguated ID."""
        return 1
    
    def inner():
        """Second inner (shadows first) - should get different disambiguated ID."""
        return 2
    
    return inner()


def another_duplicate_case():
    """Another case with duplicates."""
    
    def helper():
        """First helper."""
        pass
    
    def helper():
        """Second helper."""
        pass
    
    def helper():
        """Third helper."""
        pass
