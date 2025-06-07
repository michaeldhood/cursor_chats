"""
Magical CLI for Task Magic Framework

This is a sophisticated command-line interface that showcases the full power
and elegance of the Task Magic framework. It provides intuitive commands,
beautiful output, and powerful orchestration capabilities.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import colorama
from colorama import Fore, Back, Style

from .task_magic import TaskExecutor, Config, ExecutionPlan, ExecutionMode
from .task_magic.core import TaskStatus

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)


class MagicalCLI:
    """
    The Magical CLI - A sophisticated command-line interface for the Task Magic framework.

    This CLI provides an elegant and powerful way to interact with tasks, create execution
    plans, and orchestrate complex workflows with beautiful output and intuitive commands.
    """

    def __init__(self):
        self.config = Config().load()
        self.executor = TaskExecutor(self.config)
        self.setup_logging()

        # Discover available tasks
        self.executor.discover_tasks()

        # Setup progress tracking
        self.executor.add_progress_callback(self._progress_callback)

    def setup_logging(self):
        """Setup beautiful logging configuration."""
        log_level = getattr(logging, self.config.get("logging.level", "INFO").upper())
        log_format = self.config.get(
            "logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)],
        )

        # Reduce noise from external libraries
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

    def _progress_callback(self, task_name: str, progress: float, message: str):
        """Beautiful progress callback with colored output."""
        if progress == 0.0:
            self._print_status("info", f"🚀 Starting {task_name}")
        elif progress == 1.0:
            self._print_status("success", f"✅ Completed {task_name}")
        elif progress == 0.5:
            self._print_status("warning", f"⚠️  {task_name} encountered issues")

        if message:
            print(f"    {Fore.CYAN}└─ {message}{Style.RESET_ALL}")

    def _print_banner(self):
        """Print a beautiful banner for the CLI."""
        banner = f"""
{Fore.MAGENTA}{Style.BRIGHT}
╔══════════════════════════════════════════════════════════════╗
║                     ✨ TASK MAGIC ✨                        ║
║              Sophisticated Task Orchestration                ║
║                                                              ║
║  Transform your workflows into elegant, powerful pipelines   ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
        print(banner)

    def _print_status(self, level: str, message: str):
        """Print colored status messages."""
        colors = {
            "info": Fore.CYAN,
            "success": Fore.GREEN,
            "warning": Fore.YELLOW,
            "error": Fore.RED,
            "highlight": Fore.MAGENTA,
        }

        color = colors.get(level, Fore.WHITE)
        print(f"{color}{message}{Style.RESET_ALL}")

    def _print_task_list(self):
        """Display available tasks in a beautiful format."""
        tasks = self.executor.list_available_tasks()

        if not tasks:
            self._print_status(
                "warning",
                "No tasks available. Make sure tasks are properly registered.",
            )
            return

        self._print_status("highlight", f"\n📋 Available Tasks ({len(tasks)} total):")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

        for task_name in sorted(tasks):
            try:
                task_info = self.executor.get_task_info(task_name)
                print(f"{Fore.GREEN}▶ {task_name}{Style.RESET_ALL}")
                print(
                    f"  {Fore.CYAN}Description:{Style.RESET_ALL} {task_info['description']}"
                )

                if task_info["required_params"]:
                    params = ", ".join(task_info["required_params"])
                    print(f"  {Fore.YELLOW}Required:{Style.RESET_ALL} {params}")

                if task_info["optional_params"]:
                    params = ", ".join(task_info["optional_params"][:3])
                    if len(task_info["optional_params"]) > 3:
                        params += f" (+{len(task_info['optional_params']) - 3} more)"
                    print(f"  {Fore.BLUE}Optional:{Style.RESET_ALL} {params}")

                print()

            except Exception as e:
                print(f"  {Fore.RED}Error getting info: {e}{Style.RESET_ALL}")

    def _create_execution_plan_interactive(self) -> Optional[ExecutionPlan]:
        """Create an execution plan interactively."""
        self._print_status("highlight", "\n🎯 Creating Execution Plan")

        plan = self.executor.create_plan()

        # Choose execution mode
        print(f"\n{Fore.CYAN}Execution Modes:{Style.RESET_ALL}")
        modes = ["sequential", "parallel", "pipeline"]
        for i, mode in enumerate(modes, 1):
            print(f"  {i}. {mode.title()}")

        try:
            mode_choice = input(
                f"\n{Fore.YELLOW}Choose execution mode (1-3, default 1): {Style.RESET_ALL}"
            )
            if mode_choice.strip():
                mode_idx = int(mode_choice) - 1
                if 0 <= mode_idx < len(modes):
                    plan.mode = ExecutionMode(modes[mode_idx])
        except (ValueError, IndexError):
            pass

        self._print_status("info", f"Selected mode: {plan.mode.value}")

        # Add tasks to plan
        available_tasks = self.executor.list_available_tasks()

        while True:
            print(f"\n{Fore.CYAN}Available tasks:{Style.RESET_ALL}")
            for i, task in enumerate(available_tasks, 1):
                print(f"  {i}. {task}")

            task_choice = input(
                f"\n{Fore.YELLOW}Add task (number or name, 'done' to finish): {Style.RESET_ALL}"
            )

            if task_choice.lower() in ["done", "finish", "exit", ""]:
                break

            # Parse task choice
            task_name = None
            try:
                task_idx = int(task_choice) - 1
                if 0 <= task_idx < len(available_tasks):
                    task_name = available_tasks[task_idx]
            except ValueError:
                if task_choice in available_tasks:
                    task_name = task_choice

            if not task_name:
                self._print_status("error", "Invalid task selection")
                continue

            # Get task parameters
            try:
                task_info = self.executor.get_task_info(task_name)
                params = {}

                # Required parameters
                for param in task_info["required_params"]:
                    value = input(
                        f"  {Fore.YELLOW}{param} (required): {Style.RESET_ALL}"
                    )
                    if value.strip():
                        params[param] = value.strip()

                # Optional parameters
                if task_info["optional_params"]:
                    print(
                        f"  {Fore.BLUE}Optional parameters (press Enter to skip):{Style.RESET_ALL}"
                    )
                    for param in task_info["optional_params"]:
                        value = input(f"    {param}: ")
                        if value.strip():
                            # Try to parse as JSON for complex types
                            try:
                                params[param] = json.loads(value)
                            except:
                                params[param] = value.strip()

                # Dependencies
                if len(plan.tasks) > 0:
                    deps_input = input(
                        f"  {Fore.CYAN}Dependencies (comma-separated task names): {Style.RESET_ALL}"
                    )
                    dependencies = []
                    if deps_input.strip():
                        dependencies = [
                            dep.strip()
                            for dep in deps_input.split(",")
                            if dep.strip() in plan.tasks
                        ]

                plan.add_task(
                    task_name,
                    params,
                    dependencies if "dependencies" in locals() else None,
                )
                self._print_status("success", f"Added task: {task_name}")

            except Exception as e:
                self._print_status("error", f"Error adding task: {e}")

        if not plan.tasks:
            self._print_status("warning", "No tasks added to plan")
            return None

        return plan

    def run_task(self, args):
        """Execute a single task."""
        task_name = args.task

        if task_name not in self.executor.list_available_tasks():
            self._print_status("error", f"Task '{task_name}' not found")
            self._print_task_list()
            return 1

        self._print_status("highlight", f"\n🎯 Executing Task: {task_name}")

        # Build parameters from command line arguments
        params = {}
        if hasattr(args, "params") and args.params:
            for param_str in args.params:
                if "=" in param_str:
                    key, value = param_str.split("=", 1)
                    # Try to parse as JSON, fallback to string
                    try:
                        params[key] = json.loads(value)
                    except:
                        params[key] = value

        # Add common parameters
        if hasattr(args, "verbose") and args.verbose:
            params["verbose"] = True
        if hasattr(args, "output_dir") and args.output_dir:
            params["output_dir"] = args.output_dir

        # Execute the task
        result = self.executor.execute_task(task_name, **params)

        # Display results
        self._display_task_result(task_name, result)

        return 0 if result.success else 1

    def run_plan(self, args):
        """Execute an execution plan."""
        if args.file:
            # Load plan from file
            plan_file = Path(args.file)
            if not plan_file.exists():
                self._print_status("error", f"Plan file not found: {args.file}")
                return 1

            try:
                with open(plan_file, "r") as f:
                    plan_data = json.load(f)

                plan = ExecutionPlan(**plan_data)
                self._print_status("success", f"Loaded plan from: {args.file}")

            except Exception as e:
                self._print_status("error", f"Error loading plan: {e}")
                return 1

        elif args.interactive:
            # Create plan interactively
            plan = self._create_execution_plan_interactive()
            if not plan:
                return 1

        else:
            self._print_status(
                "error", "Either --file or --interactive must be specified"
            )
            return 1

        # Display plan summary
        self._display_plan_summary(plan)

        # Confirm execution
        if not args.yes:
            confirm = input(
                f"\n{Fore.YELLOW}Execute this plan? (y/N): {Style.RESET_ALL}"
            )
            if confirm.lower() not in ["y", "yes"]:
                self._print_status("info", "Execution cancelled")
                return 0

        # Execute the plan
        self._print_status("highlight", f"\n🚀 Executing Plan ({plan.mode.value} mode)")
        start_time = time.time()

        result = self.executor.execute_plan(plan)

        # Display results
        self._display_plan_result(result, time.time() - start_time)

        return 0 if result.success else 1

    def list_tasks(self, args):
        """List all available tasks."""
        self._print_task_list()
        return 0

    def show_config(self, args):
        """Display current configuration."""
        self._print_status("highlight", "\n⚙️  Current Configuration")

        config_dict = self.config.to_dict()

        # Pretty print configuration
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print(f"{'  ' * indent}{Fore.CYAN}{key}:{Style.RESET_ALL}")
                    print_dict(value, indent + 1)
                else:
                    print(f"{'  ' * indent}{Fore.GREEN}{key}:{Style.RESET_ALL} {value}")

        print_dict(config_dict)

        # Show configuration sources
        print(f"\n{Fore.CYAN}Configuration Sources:{Style.RESET_ALL}")
        for source in self.config.sources:
            print(f"  {source.priority:2d}. {source.name} ({source.source_type})")

        return 0

    def _display_task_result(self, task_name: str, result):
        """Display the result of a task execution."""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

        if result.success:
            self._print_status(
                "success", f"✅ Task '{task_name}' completed successfully!"
            )
        else:
            self._print_status("error", f"❌ Task '{task_name}' failed!")

        print(
            f"\n{Fore.YELLOW}Execution Time:{Style.RESET_ALL} {result.execution_time:.2f}s"
        )
        print(f"{Fore.YELLOW}Status:{Style.RESET_ALL} {result.status.value}")
        print(f"{Fore.YELLOW}Message:{Style.RESET_ALL} {result.message}")

        if result.data:
            print(f"\n{Fore.CYAN}Result Data:{Style.RESET_ALL}")
            if isinstance(result.data, dict):
                for key, value in result.data.items():
                    print(f"  {Fore.GREEN}{key}:{Style.RESET_ALL} {value}")
            else:
                print(f"  {result.data}")

        if result.metadata:
            print(f"\n{Fore.BLUE}Metadata:{Style.RESET_ALL}")
            for key, value in result.metadata.items():
                print(f"  {Fore.GREEN}{key}:{Style.RESET_ALL} {value}")

        if result.error:
            print(f"\n{Fore.RED}Error Details:{Style.RESET_ALL}")
            print(f"  {result.error}")

    def _display_plan_summary(self, plan: ExecutionPlan):
        """Display a summary of the execution plan."""
        self._print_status("highlight", f"\n📋 Execution Plan Summary")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

        print(f"{Fore.YELLOW}Mode:{Style.RESET_ALL} {plan.mode.value}")
        print(f"{Fore.YELLOW}Total Tasks:{Style.RESET_ALL} {len(plan.tasks)}")
        print(f"{Fore.YELLOW}Max Workers:{Style.RESET_ALL} {plan.max_workers}")

        if plan.timeout:
            print(f"{Fore.YELLOW}Timeout:{Style.RESET_ALL} {plan.timeout}s")

        print(f"\n{Fore.CYAN}Tasks:{Style.RESET_ALL}")
        for i, task_name in enumerate(plan.tasks, 1):
            params = plan.parameters.get(task_name, {})
            deps = plan.dependencies.get(task_name, [])

            print(f"  {i}. {Fore.GREEN}{task_name}{Style.RESET_ALL}")
            if params:
                print(
                    f"     {Fore.BLUE}Parameters:{Style.RESET_ALL} {list(params.keys())}"
                )
            if deps:
                print(
                    f"     {Fore.YELLOW}Depends on:{Style.RESET_ALL} {', '.join(deps)}"
                )

    def _display_plan_result(self, result, execution_time: float):
        """Display the result of plan execution."""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

        if result.success:
            self._print_status("success", "🎉 Execution Plan Completed Successfully!")
        else:
            self._print_status("error", "💥 Execution Plan Failed!")

        print(f"\n{Fore.YELLOW}Summary:{Style.RESET_ALL}")
        print(f"  Total Tasks: {result.total_tasks}")
        print(f"  Successful: {Fore.GREEN}{result.successful_tasks}{Style.RESET_ALL}")
        print(f"  Failed: {Fore.RED}{result.failed_tasks}{Style.RESET_ALL}")
        print(f"  Success Rate: {Fore.CYAN}{result.success_rate:.1f}%{Style.RESET_ALL}")
        print(f"  Execution Time: {execution_time:.2f}s")

        if result.errors:
            print(f"\n{Fore.RED}Errors:{Style.RESET_ALL}")
            for error in result.errors:
                print(f"  • {error}")

        # Show individual task results
        if result.task_results:
            print(f"\n{Fore.CYAN}Task Results:{Style.RESET_ALL}")
            for task_name, task_result in result.task_results.items():
                status_icon = "✅" if task_result.success else "❌"
                status_color = Fore.GREEN if task_result.success else Fore.RED
                print(
                    f"  {status_icon} {status_color}{task_name}{Style.RESET_ALL} ({task_result.execution_time:.2f}s)"
                )

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the sophisticated argument parser."""
        parser = argparse.ArgumentParser(
            prog="task-magic",
            description="🌟 Task Magic - Sophisticated Task Orchestration Framework",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  task-magic list                           # List all available tasks
  task-magic run extract --verbose         # Run extract task with verbose output
  task-magic run convert input.json --format=markdown
  task-magic plan --interactive            # Create and run plan interactively
  task-magic plan --file my_plan.json      # Run predefined plan
  task-magic config                        # Show current configuration

For more information, visit: https://github.com/cursor-ai/task-magic
            """,
        )

        parser.add_argument("--version", action="version", version="Task Magic v1.0.0")

        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose output"
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # List command
        list_parser = subparsers.add_parser("list", help="List all available tasks")

        # Run command
        run_parser = subparsers.add_parser("run", help="Execute a single task")
        run_parser.add_argument("task", help="Name of the task to execute")
        run_parser.add_argument(
            "params", nargs="*", help="Task parameters in key=value format"
        )
        run_parser.add_argument(
            "--output-dir", "-o", help="Output directory for task results"
        )

        # Plan command
        plan_parser = subparsers.add_parser("plan", help="Execute an execution plan")
        plan_group = plan_parser.add_mutually_exclusive_group(required=True)
        plan_group.add_argument(
            "--file", "-f", help="Load execution plan from JSON file"
        )
        plan_group.add_argument(
            "--interactive",
            "-i",
            action="store_true",
            help="Create execution plan interactively",
        )
        plan_parser.add_argument(
            "--yes", "-y", action="store_true", help="Skip confirmation prompt"
        )

        # Config command
        config_parser = subparsers.add_parser(
            "config", help="Show current configuration"
        )

        return parser

    def run(self, args: Optional[List[str]] = None):
        """Main entry point for the CLI."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        # Setup verbose logging if requested
        if parsed_args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # Show banner for interactive commands
        if not parsed_args.command or parsed_args.command in ["plan", "config"]:
            self._print_banner()

        # Route to appropriate handler
        try:
            if parsed_args.command == "list":
                return self.list_tasks(parsed_args)
            elif parsed_args.command == "run":
                return self.run_task(parsed_args)
            elif parsed_args.command == "plan":
                return self.run_plan(parsed_args)
            elif parsed_args.command == "config":
                return self.show_config(parsed_args)
            else:
                self._print_banner()
                parser.print_help()
                return 0

        except KeyboardInterrupt:
            self._print_status("warning", "\n\n⚠️  Operation interrupted by user")
            return 130
        except Exception as e:
            self._print_status("error", f"💥 Unexpected error: {e}")
            if parsed_args.verbose:
                import traceback

                traceback.print_exc()
            return 1


def main():
    """Entry point for the command line interface."""
    cli = MagicalCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
