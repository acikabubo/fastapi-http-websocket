# -*- coding: utf-8 -*-
from enum import IntEnum


class CustomIntEnum(IntEnum):
    @classmethod
    def options(cls):
        return [o.value for o in cls]

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)

    @classmethod
    def get_name(cls, value):
        try:
            return cls(value).name.replace("_", " ")
        except ValueError:
            return "Unknown"

    def __str__(self):
        return str(self.value)


class RSPCode(CustomIntEnum):
    OK = 0
    ERROR = 1
    INVALID_DATA = 2
    PERMISSION_DENIED = 3


class PkgID(CustomIntEnum):
    # TODO: Add package ID on format PKG_NAME = <int>
    pass

    def __str__(self):
        return f"{__class__.__name__}.{self.name}<{self.value}>"
