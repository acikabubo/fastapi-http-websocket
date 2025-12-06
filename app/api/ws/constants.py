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
    of data package requests in the system.

    Attributes:
        GET_AUTHORS (1): Request to retrieve authors (Repository + Command pattern)
        GET_PAGINATED_AUTHORS (2): Request to retrieve paginated author list
        CREATE_AUTHOR (3): Request to create author (Repository + Command pattern)
        UNREGISTERED_HANDLER (999): Test-only PkgID with no registered handler
    """

    GET_AUTHORS = 1
    GET_PAGINATED_AUTHORS = 2
    CREATE_AUTHOR = 3
    UNREGISTERED_HANDLER = 999  # For testing handler not found scenarios
