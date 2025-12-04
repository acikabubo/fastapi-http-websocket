"""FastAPI dependencies for the application."""

from {{cookiecutter.module_name}}.dependencies.permissions import require_roles

__all__ = ["require_roles"]
