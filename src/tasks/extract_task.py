"""
Extract Task for Cursor Chat Extractor

This task handles extracting chat data from Cursor's SQLite database and converting
it to JSON format. It's a modernized version of the original extractor functionality
built using the Task Magic framework.
"""

import json
import sqlite3
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..task_magic import BaseTask, TaskResult, TaskStatus, task
from ..extractor import ChatExtractor  # Import the existing extractor


@task(
    name="extract",
    description="Extract chat data from Cursor's SQLite database",
    required=[],
    optional=["output_dir", "format", "workspace_hash", "verbose"],
)
def extract_cursor_chats(
    output_dir: str = "output",
    format: str = "json",
    workspace_hash: Optional[str] = None,
    verbose: bool = False,
) -> TaskResult:
    """
    Extract chat data from Cursor's SQLite database.

    This task automatically discovers Cursor's database location, extracts all
    chat data, and saves it in the specified format. It handles multiple workspaces
    and provides detailed progress reporting.

    Args:
        output_dir: Directory to save extracted files
        format: Output format ('json', 'csv', 'markdown')
        workspace_hash: Specific workspace to extract (None for all)
        verbose: Enable verbose logging

    Returns:
        TaskResult containing extraction results and file paths
    """
    logger = logging.getLogger(__name__)

    try:
        # Setup output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize the extractor
        extractor = ChatExtractor(verbose=verbose)

        if verbose:
            logger.info("Starting chat extraction from Cursor database")
            logger.info(f"Output directory: {output_path.absolute()}")

        # Discover and extract from all databases
        extracted_files = []
        total_chats = 0

        # Get database paths
        db_paths = extractor.find_cursor_databases()

        if not db_paths:
            return TaskResult(
                status=TaskStatus.FAILED,
                message="No Cursor databases found. Make sure Cursor is installed and has been used.",
            )

        logger.info(f"Found {len(db_paths)} Cursor database(s)")

        for db_path in db_paths:
            try:
                # Extract workspace hash from path
                current_workspace_hash = extractor.get_workspace_hash(db_path)

                # Skip if specific workspace requested and this isn't it
                if workspace_hash and current_workspace_hash != workspace_hash:
                    continue

                if verbose:
                    logger.info(f"Processing database: {db_path}")
                    logger.info(f"Workspace hash: {current_workspace_hash}")

                # Extract chats from this database
                chats = extractor.extract_chats(db_path)

                if not chats:
                    logger.warning(f"No chats found in database: {db_path}")
                    continue

                total_chats += len(chats)

                # Generate output filename
                output_file = (
                    output_path / f"chat_data_{current_workspace_hash}.{format.lower()}"
                )

                # Save in requested format
                if format.lower() == "json":
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(chats, f, indent=2, ensure_ascii=False)

                elif format.lower() == "csv":
                    # Convert to CSV using pandas
                    try:
                        import pandas as pd

                        df = pd.json_normalize(chats)
                        df.to_csv(output_file, index=False)
                    except ImportError:
                        logger.error(
                            "pandas is required for CSV output. Install with: pip install pandas"
                        )
                        continue

                elif format.lower() == "markdown":
                    # Convert to markdown
                    md_content = extractor.convert_to_markdown(chats)
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(md_content)

                else:
                    logger.error(f"Unsupported format: {format}")
                    continue

                extracted_files.append(str(output_file))
                logger.info(f"Extracted {len(chats)} chats to: {output_file}")

            except Exception as e:
                logger.error(f"Error processing database {db_path}: {e}")
                continue

        if not extracted_files:
            return TaskResult(
                status=TaskStatus.FAILED,
                message="No chat data was successfully extracted",
            )

        # Success result
        result_data = {
            "extracted_files": extracted_files,
            "total_chats": total_chats,
            "format": format,
            "output_directory": str(output_path.absolute()),
        }

        message = f"Successfully extracted {total_chats} chats to {len(extracted_files)} file(s)"

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=result_data,
            message=message,
            metadata={
                "extraction_summary": {
                    "databases_processed": len(db_paths),
                    "files_created": len(extracted_files),
                    "total_chats": total_chats,
                    "output_format": format,
                }
            },
        )

    except Exception as e:
        logger.error(f"Extract task failed: {e}")
        return TaskResult(
            status=TaskStatus.FAILED, error=e, message=f"Extraction failed: {str(e)}"
        )


class ExtractTask(BaseTask):
    """
    Advanced extraction task with fine-grained control.

    This is the class-based version that provides more control over the extraction
    process and can be used when the decorator approach is not sufficient.
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="extract-advanced",
            description="Advanced chat extraction with fine-grained control",
            **kwargs,
        )
        self.extractor = None

    @property
    def required_params(self) -> List[str]:
        return []

    @property
    def optional_params(self) -> List[str]:
        return [
            "output_dir",
            "format",
            "workspace_hash",
            "verbose",
            "database_path",
            "backup_database",
            "filter_by_date",
            "include_system_messages",
            "export_attachments",
        ]

    def pre_execute(self, **kwargs) -> Dict[str, Any]:
        """Setup the extractor and validate parameters."""
        super().pre_execute(**kwargs)

        # Initialize extractor with configuration
        self.extractor = ChatExtractor(verbose=kwargs.get("verbose", False))

        # Validate output format
        format_val = kwargs.get("format", "json").lower()
        if format_val not in ["json", "csv", "markdown"]:
            raise ValueError(f"Unsupported format: {format_val}")

        kwargs["format"] = format_val
        return kwargs

    def execute(self, **kwargs) -> TaskResult:
        """Execute the advanced extraction with all options."""

        output_dir = kwargs.get("output_dir", "output")
        format_val = kwargs.get("format", "json")
        workspace_hash = kwargs.get("workspace_hash")
        database_path = kwargs.get("database_path")
        backup_database = kwargs.get("backup_database", False)
        filter_by_date = kwargs.get("filter_by_date")
        include_system_messages = kwargs.get("include_system_messages", True)
        export_attachments = kwargs.get("export_attachments", False)

        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Determine database paths
            if database_path:
                db_paths = [Path(database_path)]
            else:
                db_paths = self.extractor.find_cursor_databases()

            if not db_paths:
                raise ValueError("No databases found to extract from")

            extracted_data = []

            for db_path in db_paths:
                # Backup database if requested
                if backup_database:
                    backup_path = output_path / f"{db_path.name}.backup"
                    self.logger.info(f"Backing up database to: {backup_path}")
                    backup_path.write_bytes(db_path.read_bytes())

                # Extract chats with filters
                chats = self.extractor.extract_chats(
                    db_path,
                    include_system_messages=include_system_messages,
                    date_filter=filter_by_date,
                )

                if workspace_hash:
                    current_hash = self.extractor.get_workspace_hash(db_path)
                    if current_hash != workspace_hash:
                        continue

                extracted_data.extend(chats)

            if not extracted_data:
                return TaskResult(
                    status=TaskStatus.FAILED, message="No matching chat data found"
                )

            # Generate output file
            timestamp = int(time.time())
            output_file = output_path / f"chat_extract_{timestamp}.{format_val}"

            # Export data
            self._export_data(extracted_data, output_file, format_val)

            # Export attachments if requested
            attachment_dir = None
            if export_attachments:
                attachment_dir = output_path / "attachments"
                attachment_dir.mkdir(exist_ok=True)
                self._export_attachments(extracted_data, attachment_dir)

            result_data = {
                "output_file": str(output_file),
                "total_chats": len(extracted_data),
                "format": format_val,
                "attachment_directory": str(attachment_dir) if attachment_dir else None,
            }

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data=result_data,
                message=f"Extracted {len(extracted_data)} chats to {output_file}",
            )

        except Exception as e:
            return TaskResult(status=TaskStatus.FAILED, error=e, message=str(e))

    def _export_data(self, data: List[Dict], output_file: Path, format_val: str):
        """Export data in the specified format."""
        if format_val == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format_val == "csv":
            import pandas as pd

            df = pd.json_normalize(data)
            df.to_csv(output_file, index=False)

        elif format_val == "markdown":
            md_content = self.extractor.convert_to_markdown(data)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(md_content)

    def _export_attachments(self, data: List[Dict], attachment_dir: Path):
        """Export any attachments found in the chat data."""
        # This would implement attachment extraction
        # For now, just log that it would be implemented
        self.logger.info(
            f"Attachment export not yet implemented. Would save to: {attachment_dir}"
        )


# Register the class-based task
from ..task_magic import TaskRegistry

TaskRegistry.register(ExtractTask)
