"""Naming helpers for building symbol IDs and qualified names."""


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
        kind: Callable kind ('function', 'async_function', 'method', 'async_method').
        qualified_name: Callable qualified name.
        
    Returns:
        Node ID in format 'sym:{repo_id}:{kind}:{qualified_name}'.
    """
    return f"sym:{repo_id}:{kind}:{qualified_name}"
