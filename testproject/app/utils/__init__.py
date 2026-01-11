"""Utility modules for the application."""

from app.utils.file_io import read_json_file
from app.utils.singleton import SingletonMeta

__all__ = ["SingletonMeta", "read_json_file"]
