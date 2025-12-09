class BackupError(Exception):
    """Failed to create a new backup or delete an old one."""


class CleanupError(Exception):
    """Failed to delete an old backup."""
