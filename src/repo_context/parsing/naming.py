"""Naming helpers for building symbol IDs and qualified names."""

from typing import Optional


class DuplicateTracker:
    """Track symbol names to detect duplicates within a file extraction.
    
    When duplicate (kind, qualified_name) pairs are detected, adds a
    disambiguation suffix to the symbol ID.
    
    Usage:
        tracker = DuplicateTracker()
        # First occurrence - clean ID
        id1 = tracker.get_symbol_id("repo:test", "function", "outer.inner")
        # Returns: sym:repo:test:function:outer.inner
        
        # Second occurrence - disambiguated ID
        id2 = tracker.get_symbol_id("repo:test", "function", "outer.inner")
        # Returns: sym:repo:test:function:outer.inner:dup1
    """
    
    def __init__(self) -> None:
        """Initialize empty duplicate tracker."""
        self._seen: dict[tuple[str, str], int] = {}  # (kind, qualified_name) -> count
    
    def get_symbol_id(self, repo_id: str, kind: str, qualified_name: str) -> str:
        """Get symbol ID, adding disambiguation suffix if duplicate.
        
        Args:
            repo_id: Repository ID.
            kind: Symbol kind.
            qualified_name: Symbol qualified name.
            
        Returns:
            Symbol ID with optional :dup{N} suffix for duplicates.
        """
        key = (kind, qualified_name)
        count = self._seen.get(key, 0)
        self._seen[key] = count + 1
        
        base_id = f"sym:{repo_id}:{kind}:{qualified_name}"
        if count > 0:
            return f"{base_id}:dup{count}"
        return base_id


def build_module_qualified_name(module_path: str) -> str:
    """Build qualified name for a module.

    Args:
        module_path: Module path from file record.

    Returns:
        Qualified name (same as module_path).
    """
    return module_path


def build_class_qualified_name(module_path: str, class_name: str) -> str:
    """Build qualified name for a class.

    Args:
        module_path: Module path where class is defined.
        class_name: Simple class name.

    Returns:
        Qualified name (e.g., 'app.services.AuthService').
    """
    if module_path:
        return f"{module_path}.{class_name}"
    return class_name


def build_callable_qualified_name(parent_qualified_name: str, callable_name: str) -> str:
    """Build qualified name for a callable (function or method).

    Args:
        parent_qualified_name: Qualified name of parent (module or class).
        callable_name: Simple callable name.

    Returns:
        Qualified name (e.g., 'app.services.auth.login').
    """
    if parent_qualified_name:
        return f"{parent_qualified_name}.{callable_name}"
    return callable_name


def build_nested_qualified_name(module_path: str, lexical_chain: list[str], name: str) -> str:
    """Build qualified name including lexical nesting path.

    Args:
        module_path: Module path from file record.
        lexical_chain: List of declaration names from outermost to innermost.
        name: Simple declaration name.

    Returns:
        Nested qualified name (e.g., 'app.module.outer.inner').
    """
    parts = [module_path] if module_path else []
    parts.extend(lexical_chain)
    parts.append(name)
    return ".".join(parts)


def build_module_node_id(repo_id: str, module_path: str) -> str:
    """Build stable node ID for a module.

    Args:
        repo_id: Repository ID.
        module_path: Module path.

    Returns:
        Node ID in format 'sym:{repo_id}:module:{module_path}'.
    """
    return f"sym:{repo_id}:module:{module_path}"


def build_class_node_id(repo_id: str, qualified_name: str) -> str:
    """Build stable node ID for a class.

    Args:
        repo_id: Repository ID.
        qualified_name: Class qualified name.

    Returns:
        Node ID in format 'sym:{repo_id}:class:{qualified_name}'.
    """
    return f"sym:{repo_id}:class:{qualified_name}"


def build_callable_node_id(repo_id: str, kind: str, qualified_name: str) -> str:
    """Build stable node ID for a callable.

    Args:
        repo_id: Repository ID.
        kind: Callable kind ('function', 'async_function', 'method', 'async_method',
              'local_function', 'local_async_function').
        qualified_name: Callable qualified name.

    Returns:
        Node ID in format 'sym:{repo_id}:{kind}:{qualified_name}'.
    """
    return f"sym:{repo_id}:{kind}:{qualified_name}"
