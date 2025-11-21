"""Utility modules for the application."""

from {{cookiecutter.module_name}}.utils.file_io import read_json_file
from {{cookiecutter.module_name}}.utils.singleton import SingletonMeta

__all__ = ["SingletonMeta", "read_json_file"]
