"""Local class in function for context testing."""


def factory_function(config: dict) -> object:
    """Factory function that creates a local class."""
    
    class LocalConfig:
        """Local configuration class."""
        
        def __init__(self) -> None:
            """Initialize local config."""
            self.settings = config.copy()
        
        def get_setting(self, key: str) -> object:
            """Get a setting value."""
            return self.settings.get(key)
        
        def set_setting(self, key: str, value: object) -> None:
            """Set a setting value."""
            self.settings[key] = value
    
    return LocalConfig()


def another_factory() -> type:
    """Another factory with local class."""
    
    class SimpleLocal:
        """Simple local class."""
        pass
    
    return SimpleLocal
