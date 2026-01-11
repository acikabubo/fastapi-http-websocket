from enum import IntEnum


class RSPCode(IntEnum):
    """
    Response code enumeration for indicating operation results and error states.

    This enum defines standard response codes used throughout the application to
    represent different operation outcomes and error conditions.

    Attributes:
        OK (0): Operation completed successfully
        ERROR (1): General error occurred
        INVALID_DATA (2): Provided data is invalid or malformed
        PERMISSION_DENIED (3): User lacks required permissions for the operation

    Example:
        >>> status = RSPCode.OK
        >>> str(status)
        'RSPCode.OK<0>'
    """

    OK = 0
    ERROR = 1
    INVALID_DATA = 2
    PERMISSION_DENIED = 3

    def __str__(self):
        """
        Returns a string representation of the enum member in the format example "RSPCode.OK<0>".
        """
        return f"{__class__.__name__}.{self.name}<{self.value}>"


class PkgID(IntEnum):
    """
    Package identifier enumeration for different types of data requests.

    This enum defines identifiers used to distinguish between different types
    of data package requests in the system. Add your own package IDs here
    when implementing WebSocket handlers.

    Example:
        >>> class PkgID(IntEnum):
        ...     GET_USERS = 1
        ...     CREATE_USER = 2
        ...     UPDATE_USER = 3
    """

    # Test-only package IDs used by the test suite
    # You can remove these and add your own package IDs
    TEST_HANDLER = 999
    UNREGISTERED_HANDLER = 998  # Used to test handler-not-found scenario
