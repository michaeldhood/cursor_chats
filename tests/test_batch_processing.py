"""
Test cases for batch processing functionality (CUR-11).
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, call

from src.cli import create_parser, convert_command, tag_command, batch_command
from src.tagger import TagManager


class TestBatchProcessing:
    """Test batch processing with --all flag."""
    
    def test_convert_all_flag(self, tmp_path):
        """Test convert command with --all flag."""
        parser = create_parser()
        
        # Create multiple test JSON files
        test_files = []
        for i in range(3):
            json_file = tmp_path / f"chat_data_{i}.json"
            json_file.write_text(json.dumps([{
                'data': {
                    'tabs': [{
                        'tabId': f'tab{i}',
                        'chatTitle': f'Chat {i}',
                        'bubbles': []
                    }]
                }
            }]))
            test_files.append(json_file)
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            args = parser.parse_args([
                'convert',
                '--all',
                '--format', 'csv',
                '--output-dir', 'csv_output'
            ])
            
            result = convert_command(args)
            
            # Check that all files were converted
            assert result == 0
            assert (tmp_path / 'csv_output').exists()
            for i in range(3):
                assert (tmp_path / 'csv_output' / f'chat_data_{i}.csv').exists()
                
        finally:
            os.chdir(original_cwd)
    
    def test_convert_all_with_pattern(self, tmp_path):
        """Test convert --all with custom pattern."""
        parser = create_parser()
        
        # Create files with different patterns
        (tmp_path / "chat_data_1.json").write_text('[]')
        (tmp_path / "other_data_1.json").write_text('[]')
        (tmp_path / "chat_data_2.json").write_text('[]')
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            args = parser.parse_args([
                'convert',
                '--all',
                '--pattern', 'other_*.json',
                '--format', 'csv'
            ])
            
            with patch('src.cli.parse_chat_json') as mock_parse, \
                 patch('src.cli.export_to_csv') as mock_export:
                
                mock_parse.return_value = MagicMock()
                result = convert_command(args)
                
                # Should only process files matching pattern
                assert mock_parse.call_count == 1
                assert result == 0
                
        finally:
            os.chdir(original_cwd)
    
    def test_tag_auto_all_flag(self, tmp_path):
        """Test tag auto command with --all flag."""
        parser = create_parser()
        
        # Create test files
        for i in range(2):
            json_file = tmp_path / f"chat_data_{i}.json"
            json_file.write_text(json.dumps([{
                'data': {
                    'tabs': [{
                        'tabId': f'tab{i}',
                        'chatTitle': f'Python {i}',
                        'bubbles': [{
                            'type': 'user',
                            'text': 'Help me with Python programming'
                        }]
                    }]
                }
            }]))
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            tags_file = tmp_path / "test_tags.json"
            args = parser.parse_args([
                'tag', 'auto',
                '--all',
                '--tags-file', str(tags_file)
            ])
            
            result = tag_command(args)
            
            assert result == 0
            # Check tags were created
            assert tags_file.exists()
            
            tag_manager = TagManager(str(tags_file))
            assert len(tag_manager.get_all_tags()) > 0
            
        finally:
            os.chdir(original_cwd)
    
    def test_batch_command_all_operations(self, tmp_path):
        """Test batch command running all operations."""
        parser = create_parser()
        
        args = parser.parse_args([
            'batch',
            '--output-dir', str(tmp_path / 'output'),
            '--tags-file', str(tmp_path / 'tags.json')
        ])
        
        with patch('src.cli.extract_chats') as mock_extract, \
             patch('src.cli.parse_chat_json') as mock_parse, \
             patch('src.cli.convert_df_to_markdown') as mock_convert, \
             patch('src.cli.TagManager') as mock_tag_manager:
            
            # Mock extract returning files
            mock_extract.return_value = ['chat_1.json', 'chat_2.json']
            
            # Mock parse returning DataFrame
            mock_df = MagicMock()
            mock_df.__getitem__.return_value.apply.return_value.unique.return_value = ['tab1']
            mock_parse.return_value = mock_df
            
            # Mock convert
            mock_convert.return_value = ['file1.md', 'file2.md']
            
            result = batch_command(args)
            
            assert result == 0
            # Verify all operations were called
            assert mock_extract.called
            assert mock_parse.call_count == 4  # 2 for convert, 2 for tag
            assert mock_convert.call_count == 2
    
    def test_batch_command_selective_operations(self, tmp_path):
        """Test batch command with selective operations."""
        parser = create_parser()
        
        # Only convert and tag, not extract
        args = parser.parse_args([
            'batch',
            '--convert',
            '--tag',
            '--output-dir', str(tmp_path)
        ])
        
        # Create existing JSON file
        json_file = tmp_path / "chat_data_test.json"
        json_file.write_text(json.dumps([{
            'data': {
                'tabs': [{
                    'tabId': 'tab1',
                    'chatTitle': 'Test',
                    'bubbles': []
                }]
            }
        }]))
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            with patch('src.cli.extract_chats') as mock_extract:
                result = batch_command(args)
                
                # Extract should not be called
                assert not mock_extract.called
                assert result == 0
                
        finally:
            os.chdir(original_cwd)
    
    def test_convert_all_error_handling(self, tmp_path):
        """Test convert --all handles errors gracefully."""
        parser = create_parser()
        
        # Create one valid and one invalid file
        (tmp_path / "chat_data_good.json").write_text(json.dumps([{
            'data': {'tabs': []}
        }]))
        (tmp_path / "chat_data_bad.json").write_text("invalid json")
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            args = parser.parse_args([
                'convert',
                '--all',
                '--format', 'csv'
            ])
            
            result = convert_command(args)
            
            # Should return error code but process valid files
            assert result == 1
            
        finally:
            os.chdir(original_cwd)
    
    def test_no_files_found_error(self, tmp_path):
        """Test appropriate error when no files match pattern."""
        parser = create_parser()
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            args = parser.parse_args([
                'convert',
                '--all',
                '--pattern', 'nonexistent_*.json'
            ])
            
            result = convert_command(args)
            
            assert result == 1
            
        finally:
            os.chdir(original_cwd)