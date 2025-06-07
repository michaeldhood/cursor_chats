"""
Task Executor for Task Magic Framework

This module provides sophisticated task execution capabilities including:
- Sequential and parallel task execution
- Dependency management and workflow orchestration
- Progress tracking and reporting
- Error handling and recovery strategies
"""

import asyncio
import concurrent.futures
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

from .core import BaseTask, TaskRegistry, TaskResult, TaskStatus, TaskError
from .config import Config


class ExecutionMode(Enum):
    """Task execution modes."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"


@dataclass
class ExecutionPlan:
    """
    Represents a plan for executing multiple tasks.
    """

    tasks: List[str] = field(default_factory=list)
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_workers: int = 4
    timeout: Optional[float] = None
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_task(
        self, name: str, params: Dict[str, Any] = None, depends_on: List[str] = None
    ):
        """Add a task to the execution plan."""
        if name not in self.tasks:
            self.tasks.append(name)

        if params:
            self.parameters[name] = params

        if depends_on:
            self.dependencies[name] = depends_on

    def validate(self) -> bool:
        """Validate the execution plan for circular dependencies, etc."""

        # Check for circular dependencies using DFS
        def has_cycle(task: str, visited: set, rec_stack: set) -> bool:
            visited.add(task)
            rec_stack.add(task)

            for dependency in self.dependencies.get(task, []):
                if dependency not in visited:
                    if has_cycle(dependency, visited, rec_stack):
                        return True
                elif dependency in rec_stack:
                    return True

            rec_stack.remove(task)
            return False

        visited = set()
        for task in self.tasks:
            if task not in visited:
                if has_cycle(task, visited, set()):
                    raise TaskError(
                        f"Circular dependency detected involving task: {task}"
                    )

        return True


@dataclass
class ExecutionResult:
    """
    Result of executing an execution plan.
    """

    success: bool
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    execution_time: float
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100


class TaskExecutor:
    """
    Sophisticated task executor with support for various execution modes,
    dependency management, and advanced workflow orchestration.
    """

    def __init__(self, config: Config = None):
        self.config = config or Config().load()
        self.logger = logging.getLogger(__name__)
        self.registry = TaskRegistry()

        # Progress tracking
        self.progress_callbacks: List[Callable[[str, float, str], None]] = []
        self._execution_lock = threading.Lock()

    def add_progress_callback(self, callback: Callable[[str, float, str], None]):
        """
        Add a callback function to receive progress updates.

        Callback signature: (task_name: str, progress: float, message: str) -> None
        """
        self.progress_callbacks.append(callback)

    def _notify_progress(self, task_name: str, progress: float, message: str = ""):
        """Notify all registered progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(task_name, progress, message)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")

    def execute_task(self, task_name: str, **kwargs) -> TaskResult:
        """
        Execute a single task by name.

        Args:
            task_name: Name of the task to execute
            **kwargs: Parameters to pass to the task

        Returns:
            TaskResult: The result of the task execution
        """
        try:
            self._notify_progress(task_name, 0.0, "Starting task")

            # Create and run the task
            task = self.registry.create_task(task_name)

            self._notify_progress(task_name, 0.1, "Task created, validating parameters")

            result = task.run(**kwargs)

            progress = 1.0 if result.success else 0.5
            status = "completed successfully" if result.success else "failed"
            self._notify_progress(task_name, progress, f"Task {status}")

            return result

        except Exception as e:
            self.logger.error(f"Failed to execute task {task_name}: {e}")
            self._notify_progress(task_name, 0.0, f"Task failed: {str(e)}")
            return TaskResult(status=TaskStatus.FAILED, error=e, message=str(e))

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute a complete execution plan.

        Args:
            plan: The execution plan to run

        Returns:
            ExecutionResult: Comprehensive results of the execution
        """
        start_time = time.time()

        # Validate the plan
        try:
            plan.validate()
        except TaskError as e:
            return ExecutionResult(
                success=False,
                total_tasks=len(plan.tasks),
                successful_tasks=0,
                failed_tasks=len(plan.tasks),
                execution_time=0.0,
                errors=[str(e)],
            )

        self.logger.info(
            f"Starting execution plan with {len(plan.tasks)} tasks in {plan.mode.value} mode"
        )

        # Choose execution strategy based on mode
        if plan.mode == ExecutionMode.SEQUENTIAL:
            result = self._execute_sequential(plan)
        elif plan.mode == ExecutionMode.PARALLEL:
            result = self._execute_parallel(plan)
        elif plan.mode == ExecutionMode.PIPELINE:
            result = self._execute_pipeline(plan)
        else:
            raise TaskError(f"Unknown execution mode: {plan.mode}")

        result.execution_time = time.time() - start_time

        self.logger.info(
            f"Execution plan completed: {result.successful_tasks}/{result.total_tasks} tasks successful "
            f"({result.success_rate:.1f}%) in {result.execution_time:.2f}s"
        )

        return result

    def _execute_sequential(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute tasks sequentially in dependency order."""
        result = ExecutionResult(
            success=True,
            total_tasks=len(plan.tasks),
            successful_tasks=0,
            failed_tasks=0,
            execution_time=0.0,
        )

        # Resolve execution order based on dependencies
        execution_order = self._resolve_execution_order(plan)

        for i, task_name in enumerate(execution_order):
            self.logger.info(
                f"Executing task {i+1}/{len(execution_order)}: {task_name}"
            )

            # Get task parameters
            task_params = plan.parameters.get(task_name, {})

            # Execute the task
            task_result = self.execute_task(task_name, **task_params)
            result.task_results[task_name] = task_result

            if task_result.success:
                result.successful_tasks += 1
            else:
                result.failed_tasks += 1
                result.errors.append(f"{task_name}: {task_result.message}")

                # In sequential mode, we might want to stop on first failure
                # depending on configuration
                if not self.config.get("execution.continue_on_error", True):
                    result.success = False
                    break

        result.success = result.failed_tasks == 0
        return result

    def _execute_parallel(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute tasks in parallel, respecting dependencies."""
        result = ExecutionResult(
            success=True,
            total_tasks=len(plan.tasks),
            successful_tasks=0,
            failed_tasks=0,
            execution_time=0.0,
        )

        # Group tasks by dependency level
        dependency_levels = self._group_by_dependency_level(plan)

        # Execute each level in parallel
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=plan.max_workers
        ) as executor:
            for level, task_names in dependency_levels.items():
                self.logger.info(
                    f"Executing dependency level {level} with {len(task_names)} tasks"
                )

                # Submit all tasks in this level
                future_to_task = {}
                for task_name in task_names:
                    task_params = plan.parameters.get(task_name, {})
                    future = executor.submit(
                        self.execute_task, task_name, **task_params
                    )
                    future_to_task[future] = task_name

                # Wait for all tasks in this level to complete
                for future in concurrent.futures.as_completed(
                    future_to_task, timeout=plan.timeout
                ):
                    task_name = future_to_task[future]
                    try:
                        task_result = future.result()
                        result.task_results[task_name] = task_result

                        if task_result.success:
                            result.successful_tasks += 1
                        else:
                            result.failed_tasks += 1
                            result.errors.append(f"{task_name}: {task_result.message}")

                    except Exception as e:
                        result.failed_tasks += 1
                        result.errors.append(f"{task_name}: {str(e)}")
                        self.logger.error(f"Task {task_name} raised exception: {e}")

        result.success = result.failed_tasks == 0
        return result

    def _execute_pipeline(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute tasks as a pipeline, passing results between tasks."""
        result = ExecutionResult(
            success=True,
            total_tasks=len(plan.tasks),
            successful_tasks=0,
            failed_tasks=0,
            execution_time=0.0,
        )

        # Resolve execution order
        execution_order = self._resolve_execution_order(plan)

        # Pipeline state to pass between tasks
        pipeline_data = {}

        for i, task_name in enumerate(execution_order):
            self.logger.info(f"Pipeline step {i+1}/{len(execution_order)}: {task_name}")

            # Get task parameters and merge with pipeline data
            task_params = plan.parameters.get(task_name, {}).copy()
            task_params.update(pipeline_data)

            # Execute the task
            task_result = self.execute_task(task_name, **task_params)
            result.task_results[task_name] = task_result

            if task_result.success:
                result.successful_tasks += 1
                # Add task result to pipeline data for next task
                if task_result.data:
                    pipeline_data[f"{task_name}_result"] = task_result.data
            else:
                result.failed_tasks += 1
                result.errors.append(f"{task_name}: {task_result.message}")
                # In pipeline mode, stop on first failure
                result.success = False
                break

        return result

    def _resolve_execution_order(self, plan: ExecutionPlan) -> List[str]:
        """Resolve the order of task execution based on dependencies."""
        # Topological sort using Kahn's algorithm
        in_degree = {task: 0 for task in plan.tasks}

        # Calculate in-degrees
        for task, dependencies in plan.dependencies.items():
            for dependency in dependencies:
                if dependency in in_degree:
                    in_degree[task] += 1

        # Find tasks with no dependencies
        queue = [task for task, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            # Update in-degrees for dependent tasks
            for task, dependencies in plan.dependencies.items():
                if current in dependencies:
                    in_degree[task] -= 1
                    if in_degree[task] == 0:
                        queue.append(task)

        return result

    def _group_by_dependency_level(self, plan: ExecutionPlan) -> Dict[int, List[str]]:
        """Group tasks by their dependency level for parallel execution."""
        levels = {}
        task_levels = {}

        def calculate_level(task: str) -> int:
            if task in task_levels:
                return task_levels[task]

            dependencies = plan.dependencies.get(task, [])
            if not dependencies:
                level = 0
            else:
                level = max(calculate_level(dep) for dep in dependencies) + 1

            task_levels[task] = level
            return level

        # Calculate levels for all tasks
        for task in plan.tasks:
            level = calculate_level(task)
            if level not in levels:
                levels[level] = []
            levels[level].append(task)

        return levels

    def create_plan(self) -> ExecutionPlan:
        """Create a new execution plan."""
        return ExecutionPlan()

    def list_available_tasks(self) -> List[str]:
        """Get a list of all available tasks."""
        return self.registry.list_tasks()

    def get_task_info(self, task_name: str) -> Dict[str, Any]:
        """Get information about a specific task."""
        task_class = self.registry.get_task(task_name)
        if not task_class:
            raise TaskError(f"Task '{task_name}' not found")

        # Create a temporary instance to get parameter info
        temp_task = task_class()

        return {
            "name": task_name,
            "description": temp_task.description,
            "required_params": temp_task.required_params,
            "optional_params": temp_task.optional_params,
            "class_name": task_class.__name__,
        }

    def discover_tasks(self, module_path: str = None):
        """Discover and register tasks from a module path."""
        self.registry.discover_tasks(module_path)
        self.logger.info(f"Discovered {len(self.registry)} tasks")

    def __repr__(self) -> str:
        return f"<TaskExecutor(tasks={len(self.registry)})>"
