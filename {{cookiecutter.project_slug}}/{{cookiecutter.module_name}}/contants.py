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
