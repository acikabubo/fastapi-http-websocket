# -*- coding: utf-8 -*-
from enum import IntEnum


class RSPCode(IntEnum):
    OK = 0
    ERROR = 1
    INVALID_DATA = 2
    PERMISSION_DENIED = 3

    def __str__(self):
        return f"{__class__.__name__}.{self.name}<{self.value}>"
class PkgID(IntEnum):
    # TODO: Add package ID on format PKG_NAME = <int>
    pass
