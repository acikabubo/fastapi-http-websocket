# Database Migrations - Quick Reference

## Common Commands

| Command | Description |
|---------|-------------|
| `make migrate` | Apply all pending migrations |
| `make migration msg="description"` | Generate new migration |
| `make rollback` | Rollback last migration |
| `make migration-history` | View migration history |
| `make migration-current` | Check current version |
| `make migration-stamp rev="head"` | Stamp DB at revision |

## Typical Workflow

### 1. Modify Model
```python
# app/models/author.py
class Author(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str | None = None  # NEW FIELD
```

### 2. Generate Migration
```bash
make migration msg="Add email field to Author"
```

### 3. Review Generated File
Check `app/storage/migrations/versions/` for new migration file.

### 4. Apply Migration
```bash
make migrate
```

### 5. If Issues Occur
```bash
make rollback
```

## First Time Setup

### New Project
```bash
uv sync                # Install dependencies
make start             # Start services
make migrate           # Apply migrations
```

### Existing Database
```bash
uv sync                          # Install dependencies
make migration-stamp rev="001"   # Mark as already migrated
```

## Adding New Models

1. Create model in `app/models/`
2. Import in `app/storage/migrations/env.py`:
   ```python
   from app.models.book import Book  # noqa: F401
   ```
3. Generate migration: `make migration msg="Add Book model"`
4. Apply: `make migrate`

## Common Operations

### Add Column
```python
# Model: Add field
email: str | None = None
```
```bash
make migration msg="Add email to Author"
make migrate
```

### Remove Column
```python
# Model: Remove field (delete the line)
```
```bash
make migration msg="Remove bio from Author"
# ⚠️ REVIEW: This will drop the column!
make migrate
```

### Rename Column (Manual)
```bash
uv run alembic revision -m "Rename name to full_name"
```
```python
# Edit migration file:
def upgrade():
    op.alter_column('author', 'name', new_column_name='full_name')

def downgrade():
    op.alter_column('author', 'full_name', new_column_name='name')
```
```bash
make migrate
```

### Add Index
```python
# Model: Add index
name: str = Field(index=True)
```
```bash
make migration msg="Add index on author name"
make migrate
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No module named 'alembic'" | `uv sync` |
| "Target database is not up to date" | `make migrate` |
| "Multiple head revisions" | `uv run alembic merge heads -m "Merge"` |
| Migration file deleted | Restore from git or regenerate |

## Safety Checklist

Before applying migrations:

- [ ] Reviewed generated migration file
- [ ] Tested on development database
- [ ] Backed up production database (if production)
- [ ] Verified no data loss operations
- [ ] Checked nullable constraints
- [ ] Informed team members

## Emergency Rollback

```bash
# Development
make rollback

# Production (use with extreme caution!)
# 1. Backup database first
# 2. Test rollback on staging
# 3. Run rollback:
make rollback
# 4. Verify application functionality
```

## Resources

- **Full Guide:** [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md)
- **Implementation Summary:** [../ALEMBIC_IMPLEMENTATION_SUMMARY.md](../ALEMBIC_IMPLEMENTATION_SUMMARY.md)
- **Project Guide:** [../CLAUDE.md](../CLAUDE.md#database-migrations)
- **Alembic Docs:** https://alembic.sqlalchemy.org/

## Best Practices

✅ **Do:**
- Review generated migrations
- Test before production
- Backup production DB
- Use descriptive messages
- Keep migrations small

❌ **Don't:**
- Edit applied migrations
- Delete migration files
- Skip reviews
- Use rollback in prod without caution

---

**Need Help?** See [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md) for detailed guide.
