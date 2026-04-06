"""Module A that imports from module B."""

from cross_file_refs.module_b import helper


def use_helper():
    """Use the helper from module B."""
    return helper()
