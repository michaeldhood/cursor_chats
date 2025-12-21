"""
Test cases for customizable output paths feature (CUR-1).
"""
import os
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Import from old CLI file (deprecated but needed for tests)
import importlib.util
import pathlib
old_cli_path = pathlib.Path(__file__).parent.parent / 'src' / 'cli.py'
spec = importlib.util.spec_from_file_location('old_cli', old_cli_path)
old_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_cli)
create_parser = old_cli.create_parser
extract_command = old_cli.extract_command
convert_command = old_cli.convert_command
from src.extractor import analyze_workspace


class TestCustomizablePaths:
    """Test customizable output paths for extract and convert commands."""
    
    def test_extract_custom_output_dir(self, tmp_path):
        """Test extract command with custom output directory."""
        parser = create_parser()
        
        # Create a custom output directory
        custom_dir = tmp_path / "custom_output"
        
        args = parser.parse_args(['extract', '--output-dir', str(custom_dir)])
        
        # Mock the extract_chats function to avoid actual extraction
        with patch('src.extractor.extract_chats') as mock_extract:
            mock_extract.return_value = ['file1.json', 'file2.json']
            
            result = extract_command(args)
            
            # Check that directory was created
            assert custom_dir.exists()
            
            # Check that extract_chats was called with correct parameters
            mock_extract.assert_called_once_with(str(custom_dir), 'chat_data_{workspace}.json')
            
            assert result == 0
    
    def test_extract_custom_filename_pattern(self):
        """Test extract command with custom filename pattern."""
        parser = create_parser()
        
        args = parser.parse_args(['extract', '--filename-pattern', 'workspace_{workspace}_chats.json'])
        
        with patch('src.extractor.extract_chats') as mock_extract:
            mock_extract.return_value = ['file1.json']
            
            extract_command(args)
            
            # Check that extract_chats was called with custom pattern
            mock_extract.assert_called_once_with('.', 'workspace_{workspace}_chats.json')
    
    def test_convert_csv_custom_output_file(self, tmp_path):
        """Test convert command with custom output file for CSV."""
        parser = create_parser()
        
        # Create a dummy JSON file
        json_file = tmp_path / "test.json"
        json_file.write_text('[]')
        
        custom_output = "my_custom_output.csv"
        
        args = parser.parse_args([
            'convert', 
            str(json_file), 
            '--format', 'csv',
            '--output-file', custom_output,
            '--output-dir', str(tmp_path)
        ])
        
        with patch('src.parser.parse_chat_json') as mock_parse, \
             patch('src.parser.export_to_csv') as mock_export:
            
            mock_parse.return_value = MagicMock()
            
            result = convert_command(args)
            
            expected_path = os.path.join(str(tmp_path), custom_output)
            mock_export.assert_called_once_with(mock_parse.return_value, expected_path)
            
            assert result == 0
    
    def test_convert_csv_default_output_in_custom_dir(self, tmp_path):
        """Test convert command puts default CSV in custom directory."""
        parser = create_parser()
        
        # Create a dummy JSON file
        json_file = tmp_path / "test_data.json"
        json_file.write_text('[]')
        
        custom_dir = tmp_path / "csv_output"
        
        args = parser.parse_args([
            'convert', 
            str(json_file), 
            '--format', 'csv',
            '--output-dir', str(custom_dir)
        ])
        
        with patch('src.parser.parse_chat_json') as mock_parse, \
             patch('src.parser.export_to_csv') as mock_export:
            
            mock_parse.return_value = MagicMock()
            
            result = convert_command(args)
            
            expected_path = os.path.join(str(custom_dir), "test_data.csv")
            mock_export.assert_called_once_with(mock_parse.return_value, expected_path)
            
            assert result == 0
    
    def test_analyze_workspace_custom_output(self, tmp_path):
        """Test analyze_workspace with custom output parameters."""
        # Create a mock workspace structure
        workspace_path = tmp_path / "test_workspace"
        workspace_path.mkdir()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        with patch('src.extractor.read_sqlite_db') as mock_read:
            mock_read.return_value = [{'key': 'test', 'data': {}}]
            
            # Create a fake state.vscdb file
            (workspace_path / "state.vscdb").touch()
            
            result = analyze_workspace(
                str(workspace_path),
                str(output_dir),
                "custom_{workspace}.json"
            )
            
            assert result is not None
            assert result == str(output_dir / "custom_test_workspace.json")
            assert Path(result).exists()
    
    def test_extract_creates_nested_directories(self, tmp_path):
        """Test that extract creates nested directories if needed."""
        parser = create_parser()
        
        # Create a nested custom output directory path
        nested_dir = tmp_path / "level1" / "level2" / "output"
        
        args = parser.parse_args(['extract', '--output-dir', str(nested_dir)])
        
        with patch('src.extractor.extract_chats') as mock_extract:
            mock_extract.return_value = ['file1.json']
            
            result = extract_command(args)
            
            # Check that nested directory was created
            assert nested_dir.exists()
            assert result == 0