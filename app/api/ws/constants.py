from enum import IntEnum


class RSPCode(IntEnum):
    OK = 0
    ERROR = 1
    INVALID_DATA = 2
    PERMISSION_DENIED = 3
    ACTIVE_HEATING_SCHEDULE = 4
    ACTIVE_TAG = 5

    def __str__(self):
        return f"{__class__.__name__}.{self.name}<{self.value}>"


class PkgID(IntEnum):
    GET_AUTHORS = 1
    GET_PAGINATED_AUTHORS = 2
    THIRD = 3

    def __str__(self):
        return f"{__class__.__name__}.{self.name}<{self.value}>"
