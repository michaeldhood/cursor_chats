"""
Elegant Decorators for Task Magic Framework

This module provides beautiful and powerful decorators that make task definition
and registration feel truly magical. These decorators handle all the boilerplate
while maintaining clean, readable code.
"""

import functools
import inspect
from typing import Any, Callable, List, Optional, Type, Union

from .core import BaseTask, TaskRegistry, TaskResult, TaskStatus


def task(
    name: str = None,
    description: str = None,
    required: List[str] = None,
    optional: List[str] = None,
):
    """
    Magical decorator that transforms a function into a registered task.

    This decorator automatically creates a task class, registers it, and handles
    parameter validation. It's the most elegant way to create tasks.

    Args:
        name: Optional custom name for the task
        description: Optional description of what the task does
        required: List of required parameter names
        optional: List of optional parameter names

    Example:
        @task(name="extract_chats", required=["output_dir"])
        def extract_cursor_chats(output_dir: str, format: str = "json"):
            # Your task implementation here
            return TaskResult(status=TaskStatus.SUCCESS, data={"extracted": True})
    """

    def decorator(func: Callable) -> Type[BaseTask]:
        # Get function signature for automatic parameter detection
        sig = inspect.signature(func)

        # Auto-detect required and optional parameters from function signature
        auto_required = []
        auto_optional = []

        for param_name, param in sig.parameters.items():
            if param.default == inspect.Parameter.empty:
                auto_required.append(param_name)
            else:
                auto_optional.append(param_name)

        # Use provided parameters or auto-detected ones
        final_required = required if required is not None else auto_required
        final_optional = optional if optional is not None else auto_optional
        final_name = name or func.__name__.replace("_", "-")
        final_description = description or func.__doc__ or f"Task: {func.__name__}"

        # Create a dynamic task class
        class DecoratedTask(BaseTask):
            def __init__(self, **kwargs):
                super().__init__(
                    name=final_name, description=final_description, **kwargs
                )
                self._func = func

            @property
            def required_params(self) -> List[str]:
                return final_required

            @property
            def optional_params(self) -> List[str]:
                return final_optional

            def execute(self, **kwargs) -> TaskResult:
                # Call the original function with the parameters
                try:
                    result = self._func(**kwargs)

                    # If the function returns a TaskResult, use it directly
                    if isinstance(result, TaskResult):
                        return result

                    # Otherwise, wrap the result in a TaskResult
                    return TaskResult(
                        status=TaskStatus.SUCCESS,
                        data=result,
                        message=f"Task {self.name} completed successfully",
                    )

                except Exception as e:
                    return TaskResult(status=TaskStatus.FAILED, error=e, message=str(e))

        # Set a better class name
        DecoratedTask.__name__ = f"{func.__name__.title()}Task"
        DecoratedTask.__qualname__ = DecoratedTask.__name__

        # Register the task
        registered_class = TaskRegistry.register(DecoratedTask, final_name)

        # Return the registered class (allows for further decoration)
        return registered_class

    return decorator


def requires(*params: str):
    """
    Decorator to specify required parameters for a task.

    This can be used in combination with @task or on existing task classes.

    Args:
        *params: Names of required parameters

    Example:
        @requires("input_file", "output_dir")
        @task
        def process_file(input_file: str, output_dir: str, verbose: bool = False):
            pass
    """

    def decorator(cls_or_func):
        if inspect.isclass(cls_or_func) and issubclass(cls_or_func, BaseTask):
            # Applied to a task class
            original_required = cls_or_func.required_params
            cls_or_func.required_params = property(lambda self: list(params))
            return cls_or_func
        else:
            # Applied to a function (probably used with @task)
            cls_or_func._required_params = list(params)
            return cls_or_func

    return decorator


def optional(*params: str):
    """
    Decorator to specify optional parameters for a task.

    Args:
        *params: Names of optional parameters

    Example:
        @optional("verbose", "format")
        @requires("input_file")
        @task
        def process_file(input_file: str, verbose: bool = False, format: str = "json"):
            pass
    """

    def decorator(cls_or_func):
        if inspect.isclass(cls_or_func) and issubclass(cls_or_func, BaseTask):
            # Applied to a task class
            cls_or_func.optional_params = property(lambda self: list(params))
            return cls_or_func
        else:
            # Applied to a function
            cls_or_func._optional_params = list(params)
            return cls_or_func

    return decorator


def validate_types(**type_hints):
    """
    Decorator to add runtime type validation to task parameters.

    Args:
        **type_hints: Parameter names mapped to expected types

    Example:
        @validate_types(count=int, name=str, active=bool)
        @task
        def create_items(count: int, name: str, active: bool = True):
            pass
    """

    def decorator(task_class: Type[BaseTask]) -> Type[BaseTask]:
        original_validate = task_class.validate_params

        def enhanced_validate(self, params):
            # First run the original validation
            original_validate(self, params)

            # Then check types
            for param_name, expected_type in type_hints.items():
                if param_name in params:
                    value = params[param_name]
                    if not isinstance(value, expected_type):
                        raise TypeError(
                            f"Parameter '{param_name}' must be of type {expected_type.__name__}, "
                            f"got {type(value).__name__}"
                        )

            return True

        task_class.validate_params = enhanced_validate
        return task_class

    return decorator


def cache_result(ttl: int = 300):
    """
    Decorator to cache task results for a specified time.

    Args:
        ttl: Time to live in seconds

    Example:
        @cache_result(ttl=600)  # Cache for 10 minutes
        @task
        def expensive_computation():
            # This will be cached
            pass
    """

    def decorator(task_class: Type[BaseTask]) -> Type[BaseTask]:
        import time
        import hashlib
        import pickle

        # Simple in-memory cache
        cache = {}

        original_execute = task_class.execute

        def cached_execute(self, **kwargs):
            # Create cache key from parameters
            cache_key = hashlib.md5(pickle.dumps(sorted(kwargs.items()))).hexdigest()
            current_time = time.time()

            # Check if we have a valid cached result
            if cache_key in cache:
                cached_result, timestamp = cache[cache_key]
                if current_time - timestamp < ttl:
                    self.logger.info(f"Returning cached result for task {self.name}")
                    return cached_result

            # Execute the task and cache the result
            result = original_execute(self, **kwargs)
            if result.success:  # Only cache successful results
                cache[cache_key] = (result, current_time)

            return result

        task_class.execute = cached_execute
        return task_class

    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to add retry logic to task execution.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry

    Example:
        @retry(max_attempts=3, delay=2.0, backoff=2.0)
        @task
        def unreliable_task():
            # This will be retried up to 3 times with exponential backoff
            pass
    """

    def decorator(task_class: Type[BaseTask]) -> Type[BaseTask]:
        import time

        original_execute = task_class.execute

        def retry_execute(self, **kwargs):
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    result = original_execute(self, **kwargs)

                    if result.success or attempt == max_attempts - 1:
                        if attempt > 0:
                            self.logger.info(
                                f"Task {self.name} succeeded on attempt {attempt + 1}"
                            )
                        return result

                    # If failed and we have more attempts, log and wait
                    self.logger.warning(
                        f"Task {self.name} failed on attempt {attempt + 1}, "
                        f"retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

                except Exception as e:
                    if attempt == max_attempts - 1:
                        # Last attempt failed, return the error
                        return TaskResult(
                            status=TaskStatus.FAILED,
                            error=e,
                            message=f"Task failed after {max_attempts} attempts: {str(e)}",
                        )

                    self.logger.warning(
                        f"Task {self.name} raised exception on attempt {attempt + 1}: {e}, "
                        f"retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            # Should never reach here, but just in case
            return TaskResult(
                status=TaskStatus.FAILED,
                message=f"Task failed after {max_attempts} attempts",
            )

        task_class.execute = retry_execute
        return task_class

    return decorator


def timeout(seconds: float):
    """
    Decorator to add timeout functionality to task execution.

    Args:
        seconds: Maximum execution time in seconds

    Example:
        @timeout(30.0)  # 30 second timeout
        @task
        def long_running_task():
            pass
    """

    def decorator(task_class: Type[BaseTask]) -> Type[BaseTask]:
        import signal
        import threading

        original_execute = task_class.execute

        def timeout_execute(self, **kwargs):
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = original_execute(self, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                # Task is still running, it timed out
                self.logger.error(f"Task {self.name} timed out after {seconds} seconds")
                return TaskResult(
                    status=TaskStatus.FAILED,
                    message=f"Task timed out after {seconds} seconds",
                )

            if exception[0]:
                raise exception[0]

            return result[0]

        task_class.execute = timeout_execute
        return task_class

    return decorator
