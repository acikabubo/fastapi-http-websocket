"""
Examples of pagination cache invalidation in CRUD operations.

This module demonstrates best practices for invalidating pagination count
cache after data modifications to prevent stale counts in list endpoints.

Related:
- app/utils/pagination_cache.py - Cache implementation
- CLAUDE.md - Documentation on pagination caching
"""

from app.models.author import Author
from app.repositories.author_repository import AuthorRepository
from app.storage.db import async_session
from app.utils.pagination_cache import invalidate_count_cache


# Example 1: Simple CREATE with cache invalidation
async def create_author_example(name: str, email: str) -> Author:
    """
    Create a new author and invalidate pagination cache.

    Cache invalidation is required because:
    - Total author count has changed
    - List endpoints will show stale totals without invalidation
    """
    async with async_session() as session:
        repo = AuthorRepository(session)
        author = Author(name=name, email=email)
        result = await repo.create(author)

        # Invalidate all Author counts (all filter combinations)
        await invalidate_count_cache("Author")

        return result


# Example 2: DELETE with cache invalidation
async def delete_author_example(author_id: int) -> None:
    """
    Delete an author and invalidate pagination cache.

    Cache invalidation is required because:
    - Total author count has decreased
    - Any filtered counts may also have changed
    """
    async with async_session() as session:
        repo = AuthorRepository(session)
        await repo.delete(author_id)

        # Invalidate all Author counts
        await invalidate_count_cache("Author")


# Example 3: UPDATE with conditional invalidation based on filter
async def update_author_status_example(
    author_id: int, new_status: str
) -> Author:
    """
    Update author status with granular cache invalidation.

    Cache invalidation strategy:
    - Invalidate counts for old status filter
    - Invalidate counts for new status filter
    - Total count remains the same (no need to invalidate all)
    """
    async with async_session() as session:
        repo = AuthorRepository(session)
        author = await repo.get_by_id(author_id)

        if not author:
            raise ValueError(f"Author {author_id} not found")

        old_status = author.status
        author.status = new_status
        result = await repo.update(author)

        # Invalidate counts for both old and new status filters
        await invalidate_count_cache("Author", filters={"status": old_status})
        await invalidate_count_cache("Author", filters={"status": new_status})

        return result


# Example 4: Batch operations - invalidate once at the end
async def batch_delete_inactive_authors() -> int:
    """
    Delete multiple inactive authors with single cache invalidation.

    Performance optimization:
    - Invalidate once after batch, not per record
    - Reduces Redis operations from N to 1
    """
    async with async_session() as session:
        repo = AuthorRepository(session)

        # Get all inactive authors
        inactive_authors = await repo.get_all(is_active=False)
        deleted_count = 0

        # Delete in batch
        for author in inactive_authors:
            await repo.delete(author.id)
            deleted_count += 1

        # Invalidate once after batch operation
        await invalidate_count_cache("Author")
        await invalidate_count_cache("Author", filters={"is_active": False})

        return deleted_count


# Example 5: UPDATE that doesn't affect common filters (skip invalidation)
async def update_author_bio_example(author_id: int, bio: str) -> Author:
    """
    Update author bio without cache invalidation.

    Cache invalidation is NOT needed because:
    - Bio field is not used in pagination filters
    - Total count hasn't changed
    - Common filter fields (status, is_active) unchanged

    Note: Only skip invalidation if you're certain the field
    is never used in filters!
    """
    async with async_session() as session:
        repo = AuthorRepository(session)
        author = await repo.get_by_id(author_id)

        if not author:
            raise ValueError(f"Author {author_id} not found")

        author.bio = bio
        result = await repo.update(author)

        # No cache invalidation needed for bio updates
        # (bio is not used in any pagination filters)

        return result


# Example 6: Batch CREATE with filter-aware invalidation
async def batch_create_authors_by_status(
    authors_by_status: dict[str, list[Author]],
) -> dict[str, int]:
    """
    Batch create authors grouped by status with granular invalidation.

    Cache invalidation strategy:
    - Invalidate total count once
    - Invalidate each status filter separately
    """
    created_counts = {}

    async with async_session() as session:
        repo = AuthorRepository(session)

        for status, authors in authors_by_status.items():
            count = 0
            for author in authors:
                author.status = status
                await repo.create(author)
                count += 1
            created_counts[status] = count

        # Invalidate total count
        await invalidate_count_cache("Author")

        # Invalidate each status filter
        for status in authors_by_status.keys():
            await invalidate_count_cache("Author", filters={"status": status})

        return created_counts


# Example 7: High-frequency writes - use skip_count instead
async def get_authors_realtime_example(page: int = 1, per_page: int = 20):
    """
    Get authors for real-time feed (frequent writes).

    For models with very frequent writes:
    - Don't use count caching (data changes too often)
    - Use skip_count=True to avoid expensive COUNT queries
    - Return pagination without total count
    """
    from app.storage.db import get_paginated_results

    # Skip count for real-time data
    authors, meta = await get_paginated_results(
        Author,
        page=page,
        per_page=per_page,
        skip_count=True,  # No COUNT query
    )

    # meta.total will be 0, meta.pages will be 0
    return authors, meta


# Example 8: Complex filter invalidation
async def update_author_multi_field_example(
    author_id: int, is_active: bool, status: str
) -> Author:
    """
    Update multiple filter fields with comprehensive invalidation.

    When updating multiple fields that might be in filters:
    - Invalidate old filter combinations
    - Invalidate new filter combinations
    - Invalidate total count
    """
    async with async_session() as session:
        repo = AuthorRepository(session)
        author = await repo.get_by_id(author_id)

        if not author:
            raise ValueError(f"Author {author_id} not found")

        old_is_active = author.is_active
        old_status = author.status

        # Update multiple fields
        author.is_active = is_active
        author.status = status
        result = await repo.update(author)

        # Invalidate all affected filter combinations
        await invalidate_count_cache("Author")  # Total count
        await invalidate_count_cache(
            "Author", filters={"is_active": old_is_active}
        )
        await invalidate_count_cache(
            "Author", filters={"is_active": is_active}
        )
        await invalidate_count_cache("Author", filters={"status": old_status})
        await invalidate_count_cache("Author", filters={"status": status})

        # Could also invalidate combined filters if commonly used
        await invalidate_count_cache(
            "Author", filters={"is_active": is_active, "status": status}
        )

        return result


# Best Practices Summary:
# 1. Always invalidate after INSERT/DELETE (total count changes)
# 2. Conditionally invalidate after UPDATE (if filter fields change)
# 3. Never invalidate after SELECT/GET (read-only operations)
# 4. Batch operations: invalidate once at the end
# 5. High-frequency writes: use skip_count=True instead of caching
# 6. Granular invalidation: only invalidate affected filter combinations
# 7. When in doubt: invalidate all (safe but less efficient)
