"""
Task Magic Framework

A sophisticated task-based architecture for building modular, extensible applications.
This framework provides a clean abstraction for defining, registering, and executing tasks
with built-in configuration management, logging, and error handling.
"""

__version__ = "1.0.0"
__author__ = "Cursor Code Architect"

from .core import TaskRegistry, BaseTask, TaskError
from .config import Config
from .executor import TaskExecutor
from .decorators import task, requires, optional

__all__ = [
    "TaskRegistry",
    "BaseTask",
    "TaskError",
    "Config",
    "TaskExecutor",
    "task",
    "requires",
    "optional",
]
