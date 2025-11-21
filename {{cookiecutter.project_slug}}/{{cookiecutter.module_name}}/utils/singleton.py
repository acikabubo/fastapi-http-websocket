"""Singleton metaclass for creating singleton pattern instances."""

from typing import Any, Dict


class SingletonMeta(type):
    """
    Metaclass that implements the Singleton pattern.

    Classes using this metaclass will only have one instance per class.
    Subsequent calls to instantiate the class return the existing instance.

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

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """
        Control instance creation to ensure only one instance exists.

        Args:
            *args: Positional arguments for instance initialization.
            **kwargs: Keyword arguments for instance initialization.

        Returns:
            The singleton instance of the class.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
