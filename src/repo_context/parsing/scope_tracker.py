"""Scope tracker for lexical scope during AST traversal."""

from typing import Optional


class ScopeContext:
    """Context manager for scope tracking.
    
    Ensures the scope stack remains balanced even if an exception occurs
    during extraction.
    
    Usage:
        with scope_tracker.scope_context(symbol_id, name, scope):
            # extraction logic
            pass
    """
    
    def __init__(self, tracker: 'ScopeTracker', symbol_id: str, name: str, scope: str):
        self.tracker = tracker
        self.symbol_id = symbol_id
        self.name = name
        self.scope = scope
    
    def __enter__(self) -> 'ScopeTracker':
        self.tracker.push_declaration(self.symbol_id, self.name, self.scope)
        return self.tracker
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.tracker.pop_declaration()
        # Don't suppress exceptions


class ScopeTracker:
    """Track lexical scope during AST traversal.
    
    Maintains a stack of declarations to provide:
    - Current scope kind
    - Immediate lexical parent ID
    - Full lexical chain for qualified name building
    """

    def __init__(self) -> None:
        """Initialize the scope tracker with an empty declaration stack."""
        self._stack: list[dict] = []

    def push_declaration(self, symbol_id: str, name: str, scope: str) -> None:
        """Push a declaration onto the scope stack.
        
        Args:
            symbol_id: The symbol's stable ID.
            name: The declaration's simple name.
            scope: The scope kind ("module", "function", or "class").
        """
        self._stack.append({
            "symbol_id": symbol_id,
            "name": name,
            "scope": scope,
        })

    def pop_declaration(self) -> None:
        """Pop the most recent declaration from the scope stack."""
        if self._stack:
            self._stack.pop()

    def get_current_scope(self) -> str:
        """Get the current scope kind.
        
        Returns:
            The current scope ("module", "function", or "class").
            Returns "module" if the stack is empty.
        """
        if not self._stack:
            return "module"
        return self._stack[-1]["scope"]

    def get_lexical_parent_id(self) -> Optional[str]:
        """Get the immediate lexical parent symbol ID.
        
        Returns:
            The parent symbol ID, or None if at module level.
        """
        if not self._stack:
            return None
        return self._stack[-1]["symbol_id"]

    def get_lexical_chain(self) -> list[str]:
        """Get the full lexical declaration chain.
        
        Returns:
            List of declaration names from outermost to innermost.
        """
        return [decl["name"] for decl in self._stack]

    def get_lexical_chain_ids(self) -> list[str]:
        """Get the full lexical declaration chain of symbol IDs.
        
        Returns:
            List of symbol IDs from outermost to innermost.
        """
        return [decl["symbol_id"] for decl in self._stack]

    def is_empty(self) -> bool:
        """Check if the scope stack is empty.
        
        Returns:
            True if no declarations are on the stack.
        """
        return len(self._stack) == 0

    def depth(self) -> int:
        """Get the current depth of the scope stack.
        
        Returns:
            Number of declarations on the stack.
        """
        return len(self._stack)
    
    def scope_context(self, symbol_id: str, name: str, scope: str) -> ScopeContext:
        """Create a context manager for scope tracking.
        
        Args:
            symbol_id: The symbol's stable ID.
            name: The declaration's simple name.
            scope: The scope kind ("module", "function", or "class").
            
        Returns:
            ScopeContext instance for use with 'with' statement.
        """
        return ScopeContext(self, symbol_id, name, scope)
