"""
CLI context and configuration management.

Provides shared context for Click commands with database lifecycle management.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import logging

from src.core.db import ChatDatabase
from src.core.config import get_default_db_path

logger = logging.getLogger(__name__)


@dataclass
class CLIContext:
    """
    Shared context for CLI commands.

    Manages global CLI state including verbosity, database connections,
    and other shared resources. Follows the pattern from core/models.py.

    Attributes:
        verbose: Enable verbose logging output
        db_path: Optional path to database file (uses OS-specific default if None)
        _db: Internal database connection (lazy-initialized)
    """
    verbose: bool = False
    db_path: Optional[Path] = None
    _db: Optional[ChatDatabase] = field(default=None, repr=False, init=False)

    def get_db(self) -> ChatDatabase:
        """
        Get or create database connection (lazy initialization).

        Uses WAL mode for concurrent access between daemon and web server.
        Database connection is cached and reused across commands.

        Returns:
            ChatDatabase instance
        """
        if self._db is None:
            path = self.db_path or get_default_db_path()
            if self.verbose:
                logger.info("Opening database: %s", path)
            self._db = ChatDatabase(path)
        return self._db

    def close(self):
        """
        Clean up resources (close database connection).

        Called automatically via Click's result_callback after command execution.
        Important for WAL mode to ensure write-ahead log is checkpointed.
        """
        if self._db is not None:
            if self.verbose:
                logger.debug("Closing database connection")
            self._db.close()
            self._db = None
