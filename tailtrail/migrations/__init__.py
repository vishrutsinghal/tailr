"""Versioned package migration namespace; no migrations are required for 0.6."""

MIGRATION_API_VERSION = 1
CURRENT_PACKAGED_STATE = 1


def required_migrations(source_version: int, target_version: int = CURRENT_PACKAGED_STATE) -> tuple[int, ...]:
    """Return ordered packaged-state migrations, rejecting unsafe directions."""
    if isinstance(source_version, bool) or not isinstance(source_version, int) or source_version < 1:
        raise ValueError("source_version must be a positive integer")
    if isinstance(target_version, bool) or not isinstance(target_version, int) or target_version < 1:
        raise ValueError("target_version must be a positive integer")
    if source_version > target_version:
        raise ValueError("packaged-state downgrade is not supported")
    if target_version > CURRENT_PACKAGED_STATE:
        raise ValueError("target packaged-state version is not supported")
    return tuple(range(source_version + 1, target_version + 1))


__all__ = ["CURRENT_PACKAGED_STATE", "MIGRATION_API_VERSION", "required_migrations"]
