"""
Core Task Magic Framework

This module provides the fundamental building blocks for the task-based architecture:
- BaseTask: Abstract base class for all tasks
- TaskRegistry: Central registry for task discovery and management
- TaskError: Custom exception handling for task-related errors
"""

import abc
import inspect
import logging
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Enumeration of possible task execution states."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskError(Exception):
    """Custom exception for task-related errors."""

    def __init__(self, message: str, task_name: str = None, cause: Exception = None):
        self.task_name = task_name
        self.cause = cause
        super().__init__(message)


@dataclass
class TaskResult:
    """Encapsulates the result of a task execution."""

    status: TaskStatus
    data: Any = None
    message: str = ""
    error: Optional[Exception] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if the task completed successfully."""
        return self.status == TaskStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """Check if the task failed."""
        return self.status == TaskStatus.FAILED


class BaseTask(abc.ABC):
    """
    Abstract base class for all tasks in the Task Magic framework.

    This class provides the essential structure and lifecycle methods that all tasks
    must implement. It enforces a consistent interface while allowing for flexible
    task implementations.
    """

    def __init__(self, name: str = None, description: str = "", **kwargs):
        self.name = name or self.__class__.__name__.lower().replace("task", "")
        self.description = description or self.__doc__ or "No description provided"
        self.config = kwargs
        self.logger = logging.getLogger(f"{__module__}.{self.__class__.__name__}")

    @property
    @abc.abstractmethod
    def required_params(self) -> List[str]:
        """List of required parameters for this task."""
        pass

    @property
    def optional_params(self) -> List[str]:
        """List of optional parameters for this task."""
        return []

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate that all required parameters are present.

        Args:
            params: Dictionary of parameters to validate

        Returns:
            True if validation passes

        Raises:
            TaskError: If required parameters are missing
        """
        missing = [param for param in self.required_params if param not in params]
        if missing:
            raise TaskError(
                f"Missing required parameters: {', '.join(missing)}",
                task_name=self.name,
            )
        return True

    @abc.abstractmethod
    def execute(self, **kwargs) -> TaskResult:
        """
        Execute the task with the given parameters.

        This is the main entry point for task execution and must be implemented
        by all concrete task classes.

        Args:
            **kwargs: Task parameters

        Returns:
            TaskResult: The result of the task execution
        """
        pass

    def pre_execute(self, **kwargs) -> Dict[str, Any]:
        """
        Hook called before task execution.

        Override this method to perform any setup or preprocessing needed
        before the main task execution.

        Args:
            **kwargs: Task parameters

        Returns:
            Dictionary of processed parameters to pass to execute()
        """
        self.validate_params(kwargs)
        self.logger.info(f"Starting task: {self.name}")
        return kwargs

    def post_execute(self, result: TaskResult, **kwargs) -> TaskResult:
        """
        Hook called after task execution.

        Override this method to perform any cleanup or post-processing
        after the main task execution.

        Args:
            result: The result from the execute() method
            **kwargs: Original task parameters

        Returns:
            TaskResult: The final task result (may be modified)
        """
        status_msg = "completed successfully" if result.success else "failed"
        self.logger.info(f"Task {self.name} {status_msg}")
        return result

    def run(self, **kwargs) -> TaskResult:
        """
        Full task execution pipeline with lifecycle hooks.

        This method orchestrates the complete task execution including
        pre/post hooks and error handling.

        Args:
            **kwargs: Task parameters

        Returns:
            TaskResult: The final task result
        """
        import time

        start_time = time.time()

        try:
            # Pre-execution hook
            processed_kwargs = self.pre_execute(**kwargs)

            # Main execution
            result = self.execute(**processed_kwargs)

            # Post-execution hook
            result = self.post_execute(result, **processed_kwargs)

        except Exception as e:
            # Error handling
            self.logger.error(f"Task {self.name} failed: {str(e)}")
            result = TaskResult(status=TaskStatus.FAILED, error=e, message=str(e))

        # Set execution time
        result.execution_time = time.time() - start_time
        return result

    def __str__(self) -> str:
        return f"Task({self.name}): {self.description}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"


class TaskRegistry:
    """
    Central registry for task discovery, registration, and management.

    This singleton class maintains a registry of all available tasks and provides
    methods for task discovery, validation, and execution orchestration.
    """

    _instance = None
    _tasks: Dict[str, Type[BaseTask]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, task_class: Type[BaseTask], name: str = None) -> Type[BaseTask]:
        """
        Register a task class in the registry.

        Args:
            task_class: The task class to register
            name: Optional custom name for the task

        Returns:
            The registered task class (for use as decorator)
        """
        if not issubclass(task_class, BaseTask):
            raise TaskError(f"Task class {task_class.__name__} must extend BaseTask")

        task_name = name or task_class.__name__.lower().replace("task", "")
        cls._tasks[task_name] = task_class

        logger.info(f"Registered task: {task_name} -> {task_class.__name__}")
        return task_class

    @classmethod
    def get_task(cls, name: str) -> Optional[Type[BaseTask]]:
        """Get a task class by name."""
        return cls._tasks.get(name)

    @classmethod
    def list_tasks(cls) -> List[str]:
        """Get a list of all registered task names."""
        return list(cls._tasks.keys())

    @classmethod
    def create_task(cls, name: str, **kwargs) -> BaseTask:
        """
        Create an instance of a registered task.

        Args:
            name: Name of the task to create
            **kwargs: Parameters to pass to the task constructor

        Returns:
            An instance of the requested task

        Raises:
            TaskError: If the task is not found
        """
        task_class = cls.get_task(name)
        if task_class is None:
            raise TaskError(
                f"Task '{name}' not found. Available tasks: {', '.join(cls.list_tasks())}"
            )

        return task_class(name=name, **kwargs)

    @classmethod
    def discover_tasks(cls, module_path: str = None):
        """
        Automatically discover and register tasks from a module path.

        Args:
            module_path: Python module path to search for tasks
        """
        import importlib
        import pkgutil

        if module_path is None:
            module_path = "src.tasks"

        try:
            # Import the tasks module
            tasks_module = importlib.import_module(module_path)

            # Walk through all modules in the package
            for importer, modname, ispkg in pkgutil.iter_modules(tasks_module.__path__):
                full_module_name = f"{module_path}.{modname}"

                try:
                    module = importlib.import_module(full_module_name)

                    # Find all task classes in the module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, BaseTask)
                            and obj is not BaseTask
                            and obj.__module__ == full_module_name
                        ):

                            cls.register(obj)

                except ImportError as e:
                    logger.warning(
                        f"Could not import task module {full_module_name}: {e}"
                    )

        except ImportError as e:
            logger.warning(f"Could not import tasks package {module_path}: {e}")

    @classmethod
    def clear(cls):
        """Clear all registered tasks (mainly for testing)."""
        cls._tasks.clear()

    def __len__(self) -> int:
        return len(self._tasks)

    def __contains__(self, name: str) -> bool:
        return name in self._tasks

    def __iter__(self):
        return iter(self._tasks.items())
