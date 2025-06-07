"""
View Task for Cursor Chat Extractor

This task handles viewing and browsing chat files with various display options
and interactive features.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..task_magic import BaseTask, TaskResult, TaskStatus, task
from ..viewer import ChatViewer  # Import the existing viewer


@task(
    name="view",
    description="View and browse chat files",
    required=[],
    optional=[
        "file_path",
        "directory",
        "format",
        "interactive",
        "limit",
        "search",
        "verbose",
    ],
)
def view_chat_files(
    file_path: Optional[str] = None,
    directory: str = "output",
    format: str = "console",
    interactive: bool = False,
    limit: Optional[int] = None,
    search: Optional[str] = None,
    verbose: bool = False,
) -> TaskResult:
    """
    View and browse chat files with various display options.

    This task can display individual files, browse directories, and provide
    interactive viewing capabilities with search and filtering.

    Args:
        file_path: Specific file to view (optional)
        directory: Directory to browse if no specific file
        format: Display format ('console', 'json', 'summary')
        interactive: Enable interactive browsing mode
        limit: Maximum number of items to display
        search: Search term to filter results
        verbose: Enable verbose output

    Returns:
        TaskResult containing viewing results and displayed content
    """
    logger = logging.getLogger(__name__)

    try:
        # Initialize viewer
        viewer = ChatViewer(verbose=verbose)

        if file_path:
            # View specific file
            file_to_view = Path(file_path)
            if not file_to_view.exists():
                return TaskResult(
                    status=TaskStatus.FAILED, message=f"File not found: {file_path}"
                )

            if verbose:
                logger.info(f"Viewing file: {file_path}")

            # Read and display file content
            content = viewer.display_file(
                file_to_view, format=format, search_term=search, limit=limit
            )

            result_data = {
                "file_path": str(file_to_view.absolute()),
                "format": format,
                "content_preview": (
                    content[:500] + "..." if len(content) > 500 else content
                ),
                "total_length": len(content),
            }

            message = f"Successfully displayed file: {file_to_view.name}"

        else:
            # Browse directory
            browse_dir = Path(directory)
            if not browse_dir.exists():
                return TaskResult(
                    status=TaskStatus.FAILED,
                    message=f"Directory not found: {directory}",
                )

            if verbose:
                logger.info(f"Browsing directory: {directory}")

            # List and optionally filter files
            chat_files = viewer.list_chat_files(
                browse_dir, search_term=search, limit=limit
            )

            if interactive:
                # Start interactive browsing session
                selected_file = viewer.interactive_browse(chat_files)
                if selected_file:
                    content = viewer.display_file(selected_file, format=format)
                    result_data = {
                        "selected_file": str(selected_file),
                        "content_preview": (
                            content[:500] + "..." if len(content) > 500 else content
                        ),
                    }
                    message = f"Interactively viewed: {selected_file.name}"
                else:
                    result_data = {"browsed_files": [str(f) for f in chat_files]}
                    message = "Interactive browsing session completed"
            else:
                # Return file list
                result_data = {
                    "directory": str(browse_dir.absolute()),
                    "files_found": [str(f) for f in chat_files],
                    "total_files": len(chat_files),
                    "format": format,
                }
                message = f"Found {len(chat_files)} chat files in {directory}"

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=result_data,
            message=message,
            metadata={
                "viewing_summary": {
                    "mode": "file" if file_path else "directory",
                    "format": format,
                    "interactive": interactive,
                    "search_applied": search is not None,
                    "limit_applied": limit is not None,
                }
            },
        )

    except Exception as e:
        logger.error(f"View task failed: {e}")
        return TaskResult(
            status=TaskStatus.FAILED, error=e, message=f"Viewing failed: {str(e)}"
        )


class ViewTask(BaseTask):
    """
    Advanced viewing task with rich display options and analysis features.
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="view-advanced",
            description="Advanced chat viewing with analysis and export options",
            **kwargs,
        )
        self.viewer = None

    @property
    def required_params(self) -> List[str]:
        return []

    @property
    def optional_params(self) -> List[str]:
        return [
            "input_files",
            "output_format",
            "analysis_mode",
            "export_results",
            "generate_stats",
            "create_summary",
            "highlight_patterns",
            "verbose",
        ]

    def pre_execute(self, **kwargs) -> Dict[str, Any]:
        """Setup the viewer and validate parameters."""
        super().pre_execute(**kwargs)

        # Initialize viewer
        self.viewer = ChatViewer(verbose=kwargs.get("verbose", False))

        # Validate input files if provided
        input_files = kwargs.get("input_files", [])
        if isinstance(input_files, str):
            input_files = [input_files]

        validated_files = []
        for file_path in input_files:
            path = Path(file_path)
            if path.exists():
                validated_files.append(path)
            else:
                self.logger.warning(f"File not found: {file_path}")

        kwargs["input_files"] = validated_files
        return kwargs

    def execute(self, **kwargs) -> TaskResult:
        """Execute advanced viewing with analysis and export options."""

        input_files = kwargs.get("input_files", [])
        output_format = kwargs.get("output_format", "console")
        analysis_mode = kwargs.get("analysis_mode", False)
        export_results = kwargs.get("export_results", False)
        generate_stats = kwargs.get("generate_stats", False)
        create_summary = kwargs.get("create_summary", False)
        highlight_patterns = kwargs.get("highlight_patterns", [])

        try:
            if not input_files:
                # Auto-discover files in current directory
                input_files = list(Path.cwd().glob("*.json")) + list(
                    Path.cwd().glob("output/*.json")
                )

            if not input_files:
                return TaskResult(
                    status=TaskStatus.FAILED, message="No input files found to view"
                )

            results = {}
            all_stats = {}

            # Process each file
            for file_path in input_files:
                self.logger.info(f"Processing {file_path}")

                try:
                    # Load file content
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    file_results = {
                        "file_path": str(file_path),
                        "total_chats": len(data) if isinstance(data, list) else 1,
                    }

                    # Generate statistics if requested
                    if generate_stats:
                        stats = self._generate_statistics(data)
                        file_results["statistics"] = stats
                        all_stats[str(file_path)] = stats

                    # Create summary if requested
                    if create_summary:
                        summary = self._create_summary(data)
                        file_results["summary"] = summary

                    # Perform analysis if requested
                    if analysis_mode:
                        analysis = self._perform_analysis(data, highlight_patterns)
                        file_results["analysis"] = analysis

                    results[str(file_path)] = file_results

                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")
                    results[str(file_path)] = {"error": str(e)}

            # Export results if requested
            exported_files = []
            if export_results:
                exported_files = self._export_results(results, output_format)

            # Generate overall statistics
            overall_stats = None
            if generate_stats and all_stats:
                overall_stats = self._combine_statistics(all_stats)

            result_data = {
                "processed_files": list(results.keys()),
                "results": results,
                "overall_statistics": overall_stats,
                "exported_files": exported_files,
                "total_files": len(input_files),
            }

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data=result_data,
                message=f"Successfully processed {len(input_files)} files with advanced viewing",
            )

        except Exception as e:
            return TaskResult(status=TaskStatus.FAILED, error=e, message=str(e))

    def _generate_statistics(self, data: Union[List[Dict], Dict]) -> Dict[str, Any]:
        """Generate comprehensive statistics from chat data."""
        if not isinstance(data, list):
            data = [data]

        stats = {
            "total_chats": len(data),
            "total_messages": 0,
            "unique_workspaces": set(),
            "date_range": {"earliest": None, "latest": None},
            "message_types": {},
            "avg_messages_per_chat": 0,
        }

        for chat in data:
            if isinstance(chat, dict):
                # Count messages
                messages = chat.get("messages", [])
                stats["total_messages"] += len(messages)

                # Track workspace
                workspace = chat.get("workspace_hash")
                if workspace:
                    stats["unique_workspaces"].add(workspace)

                # Track message types
                for msg in messages:
                    msg_type = msg.get("type", "unknown")
                    stats["message_types"][msg_type] = (
                        stats["message_types"].get(msg_type, 0) + 1
                    )

                # Track dates (simplified)
                created_at = chat.get("created_at")
                if created_at:
                    if not stats["date_range"]["earliest"]:
                        stats["date_range"]["earliest"] = created_at
                    if not stats["date_range"]["latest"]:
                        stats["date_range"]["latest"] = created_at

        # Convert sets to lists for JSON serialization
        stats["unique_workspaces"] = list(stats["unique_workspaces"])

        # Calculate averages
        if stats["total_chats"] > 0:
            stats["avg_messages_per_chat"] = (
                stats["total_messages"] / stats["total_chats"]
            )

        return stats

    def _create_summary(self, data: Union[List[Dict], Dict]) -> str:
        """Create a human-readable summary of the chat data."""
        if not isinstance(data, list):
            data = [data]

        total_chats = len(data)
        total_messages = sum(
            len(chat.get("messages", [])) for chat in data if isinstance(chat, dict)
        )

        summary_lines = [
            f"Chat Data Summary",
            f"=" * 20,
            f"Total Chats: {total_chats}",
            f"Total Messages: {total_messages}",
            f"Average Messages per Chat: {total_messages / total_chats if total_chats > 0 else 0:.1f}",
        ]

        # Add workspace information
        workspaces = set()
        for chat in data:
            if isinstance(chat, dict) and chat.get("workspace_hash"):
                workspaces.add(chat["workspace_hash"])

        if workspaces:
            summary_lines.extend(
                [
                    f"Unique Workspaces: {len(workspaces)}",
                    f"Workspace IDs: {', '.join(list(workspaces)[:3])}{'...' if len(workspaces) > 3 else ''}",
                ]
            )

        return "\n".join(summary_lines)

    def _perform_analysis(
        self, data: Union[List[Dict], Dict], patterns: List[str]
    ) -> Dict[str, Any]:
        """Perform advanced analysis on the chat data."""
        if not isinstance(data, list):
            data = [data]

        analysis = {
            "pattern_matches": {},
            "conversation_lengths": [],
            "activity_distribution": {},
            "insights": [],
        }

        # Pattern matching
        for pattern in patterns:
            matches = 0
            for chat in data:
                if isinstance(chat, dict):
                    messages = chat.get("messages", [])
                    for msg in messages:
                        content = str(msg.get("content", "")).lower()
                        if pattern.lower() in content:
                            matches += 1
            analysis["pattern_matches"][pattern] = matches

        # Conversation length analysis
        for chat in data:
            if isinstance(chat, dict):
                msg_count = len(chat.get("messages", []))
                analysis["conversation_lengths"].append(msg_count)

        # Generate insights
        if analysis["conversation_lengths"]:
            avg_length = sum(analysis["conversation_lengths"]) / len(
                analysis["conversation_lengths"]
            )
            max_length = max(analysis["conversation_lengths"])
            min_length = min(analysis["conversation_lengths"])

            analysis["insights"].extend(
                [
                    f"Average conversation length: {avg_length:.1f} messages",
                    f"Longest conversation: {max_length} messages",
                    f"Shortest conversation: {min_length} messages",
                ]
            )

        return analysis

    def _combine_statistics(self, all_stats: Dict[str, Dict]) -> Dict[str, Any]:
        """Combine statistics from multiple files."""
        combined = {
            "total_files": len(all_stats),
            "total_chats": 0,
            "total_messages": 0,
            "all_workspaces": set(),
            "file_breakdown": {},
        }

        for file_path, stats in all_stats.items():
            combined["total_chats"] += stats.get("total_chats", 0)
            combined["total_messages"] += stats.get("total_messages", 0)
            combined["all_workspaces"].update(stats.get("unique_workspaces", []))
            combined["file_breakdown"][file_path] = {
                "chats": stats.get("total_chats", 0),
                "messages": stats.get("total_messages", 0),
            }

        combined["all_workspaces"] = list(combined["all_workspaces"])
        return combined

    def _export_results(self, results: Dict, format: str) -> List[str]:
        """Export viewing results to files."""
        output_dir = Path("output/view_results")
        output_dir.mkdir(parents=True, exist_ok=True)

        exported_files = []

        if format == "json":
            output_file = output_dir / "view_results.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            exported_files.append(str(output_file))

        elif format == "summary":
            output_file = output_dir / "view_summary.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("Chat Viewing Results Summary\n")
                f.write("=" * 40 + "\n\n")

                for file_path, file_results in results.items():
                    f.write(f"File: {file_path}\n")
                    f.write(f"Chats: {file_results.get('total_chats', 'N/A')}\n")
                    if "summary" in file_results:
                        f.write(f"Summary: {file_results['summary']}\n")
                    f.write("\n")

            exported_files.append(str(output_file))

        return exported_files


# Register the class-based task
from ..task_magic import TaskRegistry

TaskRegistry.register(ViewTask)
