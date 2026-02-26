"""
Unified cache key generation.

Provides a single factory for all cache key patterns across the application,
ensuring consistent SHA-256 hashing and key format.
"""

import hashlib
import json


class CacheKeyFactory:
    """Factory for generating consistent, deterministic cache keys."""

    @staticmethod
    def generate(
        prefix: str,
        *parts: str | int,
        hash_dict: dict[str, object] | None = None,
    ) -> str:
        """
        Generate a cache key from a prefix and optional parts or dict hash.

        If hash_dict is provided, its JSON-serialised representation (sorted keys)
        is SHA-256 hashed and appended.  If no hash_dict is given, parts are
        joined with ":" and appended directly.

        Args:
            prefix: Key namespace prefix (e.g. "pagination:count").
            *parts: Additional string/int segments joined with ":".
            hash_dict: Optional dict whose contents are hashed into the key.

        Returns:
            Cache key string.

        Examples:
            >>> CacheKeyFactory.generate("pagination:count", "Author")
            'pagination:count:Author'
            >>> CacheKeyFactory.generate(
            ...     "pagination:count",
            ...     "Author",
            ...     hash_dict={"status": "active"},
            ... )
            'pagination:count:Author:<sha256>'
        """
        base = ":".join([prefix, *[str(p) for p in parts]])

        if hash_dict is None:
            return base

        serialised = json.dumps(hash_dict, sort_keys=True)
        digest = hashlib.sha256(serialised.encode()).hexdigest()
        return f"{base}:{digest}"

    @staticmethod
    def generate_with_hash(prefix: str, value: str) -> str:
        """
        Generate a cache key by hashing a sensitive value (e.g. a JWT token).

        The raw value is never included in the key — only its SHA-256 digest.

        Args:
            prefix: Key namespace prefix (e.g. "token:claims").
            value: Sensitive string to hash.

        Returns:
            Cache key string.

        Example:
            >>> CacheKeyFactory.generate_with_hash("token:claims", jwt_token)
            'token:claims:<sha256>'
        """
        digest = hashlib.sha256(value.encode()).hexdigest()
        return f"{prefix}:{digest}"
