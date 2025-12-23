# Contributing Guide

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Run tests and linting
6. Submit a pull request

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-new-feature develop
```

### 2. Make Changes

Follow [Code Quality](code-quality.md) guidelines.

### 3. Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: Add new feature"
```

Use conventional commit format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test changes

### 5. Push and Create PR

```bash
git push origin feature/my-new-feature
```

Then create a pull request on GitHub.

## Code Review

Pull requests require:
- ✅ All tests passing
- ✅ Code coverage maintained
- ✅ Linting checks passing
- ✅ Documentation updated
- ✅ Reviewer approval

## Related

- [Testing Guide](testing.md)
- [Code Quality](code-quality.md)
