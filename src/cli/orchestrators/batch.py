"""
Batch operations orchestrator.

Coordinates extract, convert, and tag operations for batch processing.
Handles the complexity of working with both JSON files and database.
"""
import glob
import os
from pathlib import Path
from typing import List, Dict, Optional, Any

from src.extractor import extract_chats
from src.parser import parse_chat_json, convert_df_to_markdown, export_to_csv
from src.services.legacy_importer import LegacyChatImporter


class BatchOrchestrator:
    """Orchestrates batch operations: extract, convert, and tag."""

    def __init__(self, db=None):
        """
        Initialize batch orchestrator.

        Parameters
        ----
        db : ChatDatabase, optional
            Database instance for tagging operations. If None, tagging will be skipped.
        """
        self.db = db

    def run_batch(
        self,
        extract: bool = False,
        convert: bool = False,
        tag: bool = False,
        format: str = 'markdown',
        output_dir: str = 'chat_exports',
        filename_pattern: str = 'chat_data_{workspace}.json',
    ) -> Dict[str, Any]:
        """
        Run batch operations.

        Parameters
        ----
        extract : bool
            Whether to extract chats from Cursor database
        convert : bool
            Whether to convert extracted JSON files
        tag : bool
            Whether to tag chats (requires database)
        format : str
            Output format for conversion ('csv' or 'markdown')
        output_dir : str
            Output directory for extracted/converted files
        filename_pattern : str
            Filename pattern for extraction

        Returns
        ----
        dict
            Statistics about the batch operation
        """
        stats = {
            'extracted_files': [],
            'converted_count': 0,
            'tagged_count': 0,
            'errors': []
        }

        # Default to all operations if none specified
        if not any([extract, convert, tag]):
            extract = convert = tag = True

        extracted_files = []

        # Step 1: Extract if requested
        if extract:
            extract_dir = "." if convert else output_dir
            extracted_files = extract_chats(extract_dir, filename_pattern)
            if not extracted_files:
                stats['errors'].append("No files were extracted")
            else:
                stats['extracted_files'] = extracted_files
        else:
            # Find existing JSON files
            extracted_files = glob.glob('chat_data_*.json')

        if not extracted_files:
            stats['errors'].append("No JSON files to process")
            return stats

        # Step 2: Convert if requested
        if convert:
            success_count = 0
            for file_path in extracted_files:
                try:
                    df = parse_chat_json(file_path)

                    if format == 'markdown':
                        # Create subdirectory per workspace
                        basename = os.path.basename(os.path.splitext(file_path)[0])
                        workspace_dir = os.path.join(output_dir, basename)
                        os.makedirs(workspace_dir, exist_ok=True)

                        files = convert_df_to_markdown(df, workspace_dir)
                        success_count += 1

                    elif format == 'csv':
                        basename = os.path.basename(os.path.splitext(file_path)[0])
                        output_file = os.path.join(output_dir, basename + ".csv")
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)

                        export_to_csv(df, output_file)
                        success_count += 1

                except Exception as e:
                    stats['errors'].append(f"Error converting {file_path}: {str(e)}")

            stats['converted_count'] = success_count

        # Step 3: Tag if requested (requires database)
        if tag:
            if not self.db:
                stats['errors'].append("Database required for tagging. Tagging skipped.")
            else:
                # Import JSON files to database first
                importer = LegacyChatImporter(self.db)
                imported_chat_ids = []

                for file_path in extracted_files:
                    try:
                        # Import file to database
                        count = importer.import_file(Path(file_path))
                        # Note: import_file returns count, but we need chat IDs
                        # For now, we'll use auto-tag-all after import
                        imported_chat_ids.append(file_path)
                    except Exception as e:
                        stats['errors'].append(f"Error importing {file_path}: {str(e)}")

                # Auto-tag all imported chats
                if imported_chat_ids:
                    from src.tagger import TagManager
                    tag_manager = TagManager(db=self.db)

                    # Get all chats from database
                    all_chats = self.db.list_chats(limit=100000, offset=0)
                    tagged_count = 0

                    for chat in all_chats:
                        chat_id = chat['id']
                        existing_tags = tag_manager.get_tags(chat_id)
                        if existing_tags:
                            continue  # Skip if already tagged

                        # Get chat metadata for auto-tagging
                        chat_mode = chat.get('mode')
                        file_paths = self.db.get_chat_files(chat_id)
                        file_extensions = []
                        for path in file_paths:
                            if '.' in path:
                                ext = '.' + path.split('.')[-1]
                                file_extensions.append(ext)

                        # Get message content
                        chat_detail = self.db.get_chat(chat_id)
                        if not chat_detail:
                            continue

                        messages = chat_detail.get('messages', [])
                        content_parts = []
                        for msg in messages:
                            text = msg.get('text', '') or msg.get('rich_text', '')
                            if text:
                                content_parts.append(text)

                        content = ' '.join(content_parts)

                        # Auto-tag
                        auto_tags = tag_manager.auto_tag(
                            content=content,
                            file_extensions=file_extensions if file_extensions else None,
                            chat_mode=chat_mode
                        )

                        if auto_tags:
                            tag_manager.add_tags(chat_id, list(auto_tags))
                            tagged_count += 1

                    stats['tagged_count'] = tagged_count

        return stats

