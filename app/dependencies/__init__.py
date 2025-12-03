"""FastAPI dependencies for the application."""

from app.dependencies.permissions import require_roles

__all__ = ["require_roles"]
