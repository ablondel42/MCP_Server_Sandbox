"""Graph filtering helpers."""



CALLABLE_KINDS = {
    "function",
    "async_function",
    "method",
    "async_method",
    "local_function",
    "local_async_function",
}

LOCAL_CALLABLE_KINDS = {"local_function", "local_async_function"}

STRUCTURAL_EDGE_KINDS = {"contains", "imports", "inherits"}

SCOPE_EDGE_KIND = "SCOPE_PARENT"


def filter_nodes_by_kind(nodes: list[dict], kinds: set[str]) -> list[dict]:
    """Filter nodes by kind.
    
    Args:
        nodes: List of node dictionaries.
        kinds: Set of kinds to keep.
        
    Returns:
        Filtered list of nodes.
    """
    return [n for n in nodes if n.get("kind") in kinds]


def filter_nodes_by_scope(nodes: list[dict], scope: str) -> list[dict]:
    """Filter nodes by scope.
    
    Args:
        nodes: List of node dictionaries.
        scope: Scope value to filter by.
        
    Returns:
        Filtered list of nodes.
    """
    return [n for n in nodes if n.get("scope") == scope]


def filter_edges_by_kind(edges: list[dict], kind: str) -> list[dict]:
    """Filter edges by kind.
    
    Args:
        edges: List of edge dictionaries.
        kind: Edge kind to filter by.
        
    Returns:
        Filtered list of edges.
    """
    return [e for e in edges if e.get("kind") == kind]


def filter_edges_by_kinds(edges: list[dict], kinds: set[str]) -> list[dict]:
    """Filter edges by multiple kinds.
    
    Args:
        edges: List of edge dictionaries.
        kinds: Set of kinds to keep.
        
    Returns:
        Filtered list of edges.
    """
    return [e for e in edges if e.get("kind") in kinds]


def get_callable_nodes(nodes: list[dict]) -> list[dict]:
    """Get all callable nodes from a list.
    
    Args:
        nodes: List of node dictionaries.
        
    Returns:
        List of callable nodes.
    """
    return filter_nodes_by_kind(nodes, CALLABLE_KINDS)


def get_local_callable_nodes(nodes: list[dict]) -> list[dict]:
    """Get all local callable nodes from a list.
    
    Args:
        nodes: List of node dictionaries.
        
    Returns:
        List of local callable nodes.
    """
    return filter_nodes_by_kind(nodes, LOCAL_CALLABLE_KINDS)


def get_scope_parent_edges(edges: list[dict]) -> list[dict]:
    """Get all SCOPE_PARENT edges from a list.
    
    Args:
        edges: List of edge dictionaries.
        
    Returns:
        List of SCOPE_PARENT edges.
    """
    return filter_edges_by_kind(edges, SCOPE_EDGE_KIND)


def get_structural_edges(edges: list[dict]) -> list[dict]:
    """Get all structural edges (contains, imports, inherits).
    
    Args:
        edges: List of edge dictionaries.
        
    Returns:
        List of structural edges.
    """
    return filter_edges_by_kinds(edges, STRUCTURAL_EDGE_KINDS)
