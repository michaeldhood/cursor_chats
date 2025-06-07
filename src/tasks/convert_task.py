"""
Convert Task for Cursor Chat Extractor

This task handles converting chat data between different formats (JSON, CSV, Markdown).
It provides sophisticated conversion capabilities with customizable options.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..task_magic import BaseTask, TaskResult, TaskStatus, task
from ..parser import ChatParser  # Import the existing parser


@task(
    name="convert",
    description="Convert chat data between different formats",
    required=["input_file"],
    optional=["output_file", "format", "output_dir", "template", "verbose"],
)
def convert_chat_data(
    input_file: str,
    output_file: Optional[str] = None,
    format: str = "markdown",
    output_dir: str = "output",
    template: Optional[str] = None,
    verbose: bool = False,
) -> TaskResult:
    """
    Convert chat data from one format to another.

    This task can convert between JSON, CSV, and Markdown formats with
    customizable templates and output options.

    Args:
        input_file: Path to input file (JSON, CSV, or Markdown)
        output_file: Output filename (auto-generated if not provided)
        format: Target format ('json', 'csv', 'markdown')
        output_dir: Directory for output file
        template: Custom template for markdown output
        verbose: Enable verbose logging

    Returns:
        TaskResult containing conversion results and output file path
    """
    logger = logging.getLogger(__name__)

    try:
        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            return TaskResult(
                status=TaskStatus.FAILED, message=f"Input file not found: {input_file}"
            )

        # Setup output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize parser
        parser = ChatParser(verbose=verbose)

        if verbose:
            logger.info(f"Converting {input_file} to {format} format")

        # Load input data
        if input_path.suffix.lower() == ".json":
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif input_path.suffix.lower() == ".csv":
            try:
                import pandas as pd

                df = pd.read_csv(input_path)
                data = df.to_dict("records")
            except ImportError:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    message="pandas is required for CSV input. Install with: pip install pandas",
                )
        else:
            return TaskResult(
                status=TaskStatus.FAILED,
                message=f"Unsupported input format: {input_path.suffix}",
            )

        # Generate output filename if not provided
        if not output_file:
            base_name = input_path.stem
            output_file = f"{base_name}.{format.lower()}"

        output_file_path = output_path / output_file

        # Convert to target format
        if format.lower() == "json":
            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format.lower() == "csv":
            try:
                import pandas as pd

                df = pd.json_normalize(data)
                df.to_csv(output_file_path, index=False)
            except ImportError:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    message="pandas is required for CSV output. Install with: pip install pandas",
                )

        elif format.lower() == "markdown":
            # Use custom template if provided
            if template:
                md_content = parser.convert_to_markdown_with_template(data, template)
            else:
                md_content = parser.convert_to_markdown(data)

            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

        else:
            return TaskResult(
                status=TaskStatus.FAILED, message=f"Unsupported output format: {format}"
            )

        # Success result
        result_data = {
            "input_file": str(input_path.absolute()),
            "output_file": str(output_file_path.absolute()),
            "input_format": input_path.suffix.lower().lstrip("."),
            "output_format": format.lower(),
            "records_processed": len(data) if isinstance(data, list) else 1,
        }

        message = f"Successfully converted {len(data) if isinstance(data, list) else 1} records to {format} format"

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=result_data,
            message=message,
            metadata={
                "conversion_summary": {
                    "input_file": str(input_path),
                    "output_file": str(output_file_path),
                    "format_conversion": f"{input_path.suffix.lower()} → {format.lower()}",
                    "size_before": input_path.stat().st_size,
                    "size_after": output_file_path.stat().st_size,
                }
            },
        )

    except Exception as e:
        logger.error(f"Convert task failed: {e}")
        return TaskResult(
            status=TaskStatus.FAILED, error=e, message=f"Conversion failed: {str(e)}"
        )


class ConvertTask(BaseTask):
    """
    Advanced conversion task with batch processing and templating support.
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="convert-advanced",
            description="Advanced format conversion with batch processing and templates",
            **kwargs,
        )
        self.parser = None

    @property
    def required_params(self) -> List[str]:
        return ["input_files"]

    @property
    def optional_params(self) -> List[str]:
        return [
            "output_dir",
            "format",
            "template",
            "batch_mode",
            "verbose",
            "split_by_workspace",
            "merge_files",
            "custom_filters",
        ]

    def pre_execute(self, **kwargs) -> Dict[str, Any]:
        """Setup the parser and validate parameters."""
        super().pre_execute(**kwargs)

        # Initialize parser
        self.parser = ChatParser(verbose=kwargs.get("verbose", False))

        # Validate input files
        input_files = kwargs.get("input_files", [])
        if isinstance(input_files, str):
            input_files = [input_files]

        validated_files = []
        for file_path in input_files:
            path = Path(file_path)
            if not path.exists():
                raise ValueError(f"Input file not found: {file_path}")
            validated_files.append(path)

        kwargs["input_files"] = validated_files

        # Validate format
        format_val = kwargs.get("format", "markdown").lower()
        if format_val not in ["json", "csv", "markdown"]:
            raise ValueError(f"Unsupported format: {format_val}")
        kwargs["format"] = format_val

        return kwargs

    def execute(self, **kwargs) -> TaskResult:
        """Execute the advanced conversion with all options."""

        input_files = kwargs.get("input_files", [])
        output_dir = kwargs.get("output_dir", "output")
        format_val = kwargs.get("format", "markdown")
        template = kwargs.get("template")
        batch_mode = kwargs.get("batch_mode", True)
        split_by_workspace = kwargs.get("split_by_workspace", False)
        merge_files = kwargs.get("merge_files", False)
        custom_filters = kwargs.get("custom_filters", {})

        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            all_data = []
            processed_files = []

            # Process each input file
            for input_file in input_files:
                self.logger.info(f"Processing {input_file}")

                # Load data
                data = self._load_file_data(input_file)

                # Apply custom filters
                if custom_filters:
                    data = self._apply_filters(data, custom_filters)

                if merge_files:
                    all_data.extend(data if isinstance(data, list) else [data])
                else:
                    # Process individual file
                    output_file = self._generate_output_filename(
                        input_file, output_path, format_val
                    )
                    self._convert_and_save(data, output_file, format_val, template)
                    processed_files.append(output_file)

            # Handle merged output
            if merge_files and all_data:
                merged_output = output_path / f"merged_chats.{format_val}"
                self._convert_and_save(all_data, merged_output, format_val, template)
                processed_files.append(merged_output)

            # Handle workspace splitting
            if split_by_workspace and not merge_files:
                processed_files = self._split_by_workspace(
                    all_data, output_path, format_val, template
                )

            if not processed_files:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    message="No files were successfully processed",
                )

            result_data = {
                "processed_files": [str(f) for f in processed_files],
                "total_input_files": len(input_files),
                "total_output_files": len(processed_files),
                "format": format_val,
                "batch_mode": batch_mode,
            }

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data=result_data,
                message=f"Successfully converted {len(input_files)} files to {len(processed_files)} output files",
            )

        except Exception as e:
            return TaskResult(status=TaskStatus.FAILED, error=e, message=str(e))

    def _load_file_data(self, file_path: Path) -> Any:
        """Load data from a file based on its format."""
        if file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif file_path.suffix.lower() == ".csv":
            import pandas as pd

            df = pd.read_csv(file_path)
            return df.to_dict("records")
        else:
            raise ValueError(f"Unsupported input format: {file_path.suffix}")

    def _apply_filters(self, data: Any, filters: Dict[str, Any]) -> Any:
        """Apply custom filters to the data."""
        if not isinstance(data, list):
            return data

        filtered_data = data

        # Date range filter
        if "date_range" in filters:
            start_date = filters["date_range"].get("start")
            end_date = filters["date_range"].get("end")
            # Implementation would filter by date range

        # Content filter
        if "content_contains" in filters:
            search_term = filters["content_contains"]
            filtered_data = [
                item
                for item in filtered_data
                if any(
                    search_term.lower() in str(value).lower()
                    for value in item.values()
                    if isinstance(value, str)
                )
            ]

        # Workspace filter
        if "workspace" in filters:
            workspace = filters["workspace"]
            filtered_data = [
                item
                for item in filtered_data
                if item.get("workspace_hash") == workspace
            ]

        return filtered_data

    def _generate_output_filename(
        self, input_file: Path, output_dir: Path, format_val: str
    ) -> Path:
        """Generate output filename based on input file."""
        base_name = input_file.stem
        return output_dir / f"{base_name}.{format_val}"

    def _convert_and_save(
        self, data: Any, output_file: Path, format_val: str, template: Optional[str]
    ):
        """Convert data and save to file."""
        if format_val == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format_val == "csv":
            import pandas as pd

            df = pd.json_normalize(data)
            df.to_csv(output_file, index=False)

        elif format_val == "markdown":
            if template:
                md_content = self.parser.convert_to_markdown_with_template(
                    data, template
                )
            else:
                md_content = self.parser.convert_to_markdown(data)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(md_content)

    def _split_by_workspace(
        self,
        data: List[Dict],
        output_dir: Path,
        format_val: str,
        template: Optional[str],
    ) -> List[Path]:
        """Split data by workspace and save separate files."""
        workspace_data = {}

        # Group by workspace
        for item in data:
            workspace = item.get("workspace_hash", "unknown")
            if workspace not in workspace_data:
                workspace_data[workspace] = []
            workspace_data[workspace].append(item)

        # Save each workspace separately
        output_files = []
        for workspace, items in workspace_data.items():
            output_file = output_dir / f"workspace_{workspace}.{format_val}"
            self._convert_and_save(items, output_file, format_val, template)
            output_files.append(output_file)

        return output_files


# Register the class-based task
from ..task_magic import TaskRegistry

TaskRegistry.register(ConvertTask)
