# Code Quality

## Overview

The project maintains high code quality standards through automated tools and pre-commit hooks.

## Code Style

### Line Length

79 characters maximum (enforced by Ruff)

### Formatting

```bash
# Format code
uvx ruff format

# Check formatting
uvx ruff check --config=pyproject.toml
```

### Type Hints

Required on all functions (enforced by mypy --strict):

```python
def get_author(author_id: int) -> Author | None:
    """Get author by ID."""
    pass
```

### Docstrings

Required on all public functions, classes, and methods (80% coverage minimum):

```python
def create_author(name: str) -> Author:
    """
    Create a new author.

    Args:
        name: Author's full name

    Returns:
        Created author instance

    Raises:
        ValueError: If name is empty
    """
    pass
```

## Linting

### Ruff

```bash
# Check all files
make ruff-check

# Auto-fix issues
uvx ruff check --fix
```

### Mypy

```bash
# Type check
uvx mypy app/
```

### Interrogate

```bash
# Check docstring coverage
uvx interrogate app/
```

## Security

### Bandit

```bash
# SAST scanning
make bandit-scan
```

### Skjold

```bash
# Dependency vulnerability scanning
make skjold-scan
```

## Dead Code Detection

```bash
# Find unused code
make dead-code-scan
```

## Spell Checking

```bash
# Check typos
uvx typos
```

## Pre-commit Hooks

All checks run automatically on commit:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Related

- [Testing Guide](testing.md)
- [Contributing Guide](contributing.md)
