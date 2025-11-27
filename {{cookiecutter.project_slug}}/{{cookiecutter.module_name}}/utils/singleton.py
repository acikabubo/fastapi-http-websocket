"""Singleton metaclass for creating singleton pattern instances."""

import threading
from typing import Any, Dict


class SingletonMeta(type):
    """
    Metaclass that implements the Singleton pattern.

    Classes using this metaclass will only have one instance per class.
    Subsequent calls to instantiate the class return the existing instance.
    Thread-safe implementation using double-check locking pattern.

    Example:
        class MyManager(metaclass=SingletonMeta):
            def __init__(self):
                self.data = []

        # Both variables reference the same instance
        manager1 = MyManager()
        manager2 = MyManager()
        assert manager1 is manager2
    """

    _instances: Dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """
        Control instance creation to ensure only one instance exists.

        Uses double-check locking pattern for thread safety in async contexts.

        Args:
            *args: Positional arguments for instance initialization.
            **kwargs: Keyword arguments for instance initialization.

        Returns:
            The singleton instance of the class.
        """
        if cls not in cls._instances:
            with cls._lock:
                # Double-check locking pattern
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
