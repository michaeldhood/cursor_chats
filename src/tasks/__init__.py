"""
Tasks Package for Cursor Chat Extractor

This package contains all the tasks that can be executed by the Task Magic framework.
Tasks are automatically discovered and registered when this package is imported.
"""

import logging
from ..task_magic import TaskRegistry

logger = logging.getLogger(__name__)

# Automatically discover and register all tasks in this package
TaskRegistry.discover_tasks("src.tasks")

logger.info(f"Tasks package loaded with {len(TaskRegistry())} registered tasks")
