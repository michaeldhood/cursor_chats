"""
Test cases for journal generation functionality (CUR-7/CUR-8).
"""
import json
import tempfile
import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.journal import JournalTemplate, JournalGenerator, generate_journal_from_file
# Import from old CLI file (deprecated but needed for tests)
import importlib.util
import pathlib
old_cli_path = pathlib.Path(__file__).parent.parent / 'src' / 'cli.py'
spec = importlib.util.spec_from_file_location('old_cli', old_cli_path)
old_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_cli)
create_parser = old_cli.create_parser
journal_command = old_cli.journal_command


class TestJournalTemplate:
    """Test the JournalTemplate class."""
    
    def test_template_creation(self):
        """Test basic template creation."""
        sections = [
            {"title": "## Overview", "prompt": "What happened?"},
            {"title": "## Next steps", "prompt": "What's next?"}
        ]
        
        template = JournalTemplate("test_template", sections)
        
        assert template.name == "test_template"
        assert len(template.sections) == 2
        assert template.sections[0]["title"] == "## Overview"
    
    def test_template_from_dict(self):
        """Test creating template from dictionary."""
        data = {
            "name": "test_template",
            "sections": [
                {"title": "## Overview", "prompt": "What happened?"}
            ],
            "metadata": {"description": "Test template"}
        }
        
        template = JournalTemplate.from_dict(data)
        
        assert template.name == "test_template"
        assert template.metadata["description"] == "Test template"
    
    def test_template_to_dict(self):
        """Test converting template to dictionary."""
        sections = [{"title": "## Overview", "prompt": "What happened?"}]
        template = JournalTemplate("test", sections, {"desc": "test"})
        
        data = template.to_dict()
        
        assert data["name"] == "test"
        assert data["sections"] == sections
        assert data["metadata"]["desc"] == "test"
        assert "created_at" in data
    
    def test_variable_substitution(self):
        """Test template variable substitution."""
        template = JournalTemplate("test", [])
        
        text = "Journal for {chat_title} on {date}"
        variables = {"chat_title": "Test Chat", "date": "2024-01-01"}
        
        result = template.substitute_variables(text, variables)
        
        assert result == "Journal for Test Chat on 2024-01-01"


class TestJournalGenerator:
    """Test the JournalGenerator class."""
    
    def test_default_templates_loaded(self):
        """Test that default templates are loaded."""
        generator = JournalGenerator()
        
        templates = generator.list_templates()
        
        assert "project_journal" in templates
        assert "technical_journal" in templates
        assert "meeting_notes" in templates
    
    def test_get_template(self):
        """Test getting template by name."""
        generator = JournalGenerator()
        
        template = generator.get_template("project_journal")
        
        assert template is not None
        assert template.name == "project_journal"
        assert len(template.sections) > 0
    
    def test_create_custom_template(self, tmp_path):
        """Test creating custom template."""
        generator = JournalGenerator(str(tmp_path))
        
        sections = [
            {"title": "## Custom Section", "prompt": "Custom prompt"}
        ]
        
        template = generator.create_custom_template(
            "custom_template", 
            sections, 
            {"description": "Custom test template"}
        )
        
        assert template.name == "custom_template"
        assert "custom_template" in generator.list_templates()
        
        # Check if template was saved
        template_file = tmp_path / "custom_template.json"
        assert template_file.exists()
    
    def test_generate_journal_from_dataframe(self):
        """Test journal generation from DataFrame."""
        generator = JournalGenerator()
        
        # Create sample DataFrame
        df = pd.DataFrame([
            {
                "chatTitle": "Test Chat",
                "tabId": "tab1",
                "text": "Hello world",
                "type": "user"
            }
        ])
        
        result = generator.generate_journal(df, "project_journal")
        
        assert "content" in result
        assert "metadata" in result
        assert "Test Chat" in result["content"]
        assert result["metadata"]["template"] == "project_journal"
    
    def test_generate_journal_with_annotations(self):
        """Test journal generation with manual annotations."""
        generator = JournalGenerator()
        
        df = pd.DataFrame([{"chatTitle": "Test", "tabId": "tab1"}])
        annotations = {
            "what_happened": "We discussed the project requirements",
            "key_insights": "The main challenge is performance"
        }
        
        result = generator.generate_journal(df, "project_journal", annotations)
        
        assert "We discussed the project requirements" in result["content"]
        assert "The main challenge is performance" in result["content"]
    
    def test_different_output_formats(self):
        """Test different output formats."""
        generator = JournalGenerator()
        df = pd.DataFrame([{"chatTitle": "Test", "tabId": "tab1"}])
        
        # Test Markdown
        md_result = generator.generate_journal(df, "project_journal", output_format="markdown")
        assert md_result["metadata"]["format"] == "markdown"
        assert "# Journal: Test" in md_result["content"]
        
        # Test HTML
        html_result = generator.generate_journal(df, "project_journal", output_format="html")
        assert html_result["metadata"]["format"] == "html"
        assert "<h1>Journal: Test</h1>" in html_result["content"]
        
        # Test JSON
        json_result = generator.generate_journal(df, "project_journal", output_format="json")
        assert json_result["metadata"]["format"] == "json"
        parsed_content = json.loads(json_result["content"])
        assert "title" in parsed_content
    
    def test_load_custom_templates(self, tmp_path):
        """Test loading custom templates from directory."""
        # Create a custom template file
        template_data = {
            "name": "loaded_template",
            "sections": [
                {"title": "## Test Section", "prompt": "Test prompt"}
            ],
            "metadata": {"description": "Loaded from file"}
        }
        
        template_file = tmp_path / "loaded_template.json"
        with open(template_file, 'w') as f:
            json.dump(template_data, f)
        
        # Create generator with custom templates directory
        generator = JournalGenerator(str(tmp_path))
        
        assert "loaded_template" in generator.list_templates()
        template = generator.get_template("loaded_template")
        assert template.metadata["description"] == "Loaded from file"


class TestJournalCLI:
    """Test journal CLI commands."""
    
    def test_journal_template_list(self):
        """Test journal template list command."""
        parser = create_parser()
        args = parser.parse_args(['journal', 'template', 'list'])
        
        result = journal_command(args)
        
        assert result == 0
    
    def test_journal_template_show(self):
        """Test journal template show command."""
        parser = create_parser()
        args = parser.parse_args(['journal', 'template', 'show', 'project_journal'])
        
        result = journal_command(args)
        
        assert result == 0
    
    def test_journal_template_show_nonexistent(self):
        """Test showing nonexistent template."""
        parser = create_parser()
        args = parser.parse_args(['journal', 'template', 'show', 'nonexistent'])
        
        result = journal_command(args)
        
        assert result == 1
    
    def test_journal_generate_command(self, tmp_path):
        """Test journal generate command."""
        parser = create_parser()
        
        # Create a test JSON file
        test_data = [{
            'data': {
                'tabs': [{
                    'tabId': 'tab1',
                    'chatTitle': 'Test Chat',
                    'bubbles': [{
                        'type': 'user',
                        'text': 'Hello world'
                    }]
                }]
            }
        }]
        
        json_file = tmp_path / "test_chat.json"
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        output_file = tmp_path / "test_journal.md"
        
        args = parser.parse_args([
            'journal', 'generate', 
            str(json_file),
            '--output', str(output_file),
            '--template', 'project_journal'
        ])
        
        result = journal_command(args)
        
        assert result == 0
        assert output_file.exists()
        
        # Check journal content
        with open(output_file, 'r') as f:
            content = f.read()
            assert "Journal: Test Chat" in content
            assert "What happened?" in content
    
    def test_journal_generate_with_annotations(self, tmp_path):
        """Test journal generate with annotations file."""
        parser = create_parser()
        
        # Create test files
        test_data = [{'data': {'tabs': [{'tabId': 'tab1', 'chatTitle': 'Test', 'bubbles': []}]}}]
        json_file = tmp_path / "test_chat.json"
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        # Create annotations file
        annotations = {
            "what_happened": "We implemented a new feature",
            "why": "To improve user experience"
        }
        annotations_file = tmp_path / "annotations.json"
        with open(annotations_file, 'w') as f:
            json.dump(annotations, f)
        
        output_file = tmp_path / "test_journal.md"
        
        args = parser.parse_args([
            'journal', 'generate',
            str(json_file),
            '--output', str(output_file),
            '--annotations', str(annotations_file)
        ])
        
        result = journal_command(args)
        
        assert result == 0
        
        # Check that annotations were included
        with open(output_file, 'r') as f:
            content = f.read()
            assert "We implemented a new feature" in content
            assert "To improve user experience" in content
    
    def test_journal_generate_file_not_found(self):
        """Test journal generate with nonexistent file."""
        parser = create_parser()
        args = parser.parse_args(['journal', 'generate', 'nonexistent.json'])
        
        result = journal_command(args)
        
        assert result == 1
    
    def test_journal_template_create_from_file(self, tmp_path):
        """Test creating template from file."""
        parser = create_parser()
        
        # Create template definition file
        template_def = {
            "sections": [
                {"title": "## Custom", "prompt": "Custom prompt"}
            ],
            "metadata": {"description": "Custom template"}
        }
        
        template_file = tmp_path / "custom_template.json"
        with open(template_file, 'w') as f:
            json.dump(template_def, f)
        
        args = parser.parse_args([
            'journal', 'template', 'create',
            'my_custom_template',
            '--from-file', str(template_file)
        ])
        
        # Mock _save_template to prevent filesystem writes during test
        with patch('src.journal.JournalGenerator._save_template'):
            result = journal_command(args)
        
        assert result == 0


class TestJournalIntegration:
    """Integration tests for journal functionality."""
    
    def test_generate_journal_from_file_function(self, tmp_path):
        """Test the generate_journal_from_file function."""
        # Create test chat file
        test_data = [{
            'data': {
                'tabs': [{
                    'tabId': 'tab1',
                    'chatTitle': 'Integration Test',
                    'bubbles': [{
                        'type': 'user',
                        'text': 'Test message'
                    }]
                }]
            }
        }]
        
        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        # Generate journal
        result = generate_journal_from_file(str(json_file))
        
        assert "content" in result
        assert "metadata" in result
        assert "Integration Test" in result["content"]
        assert result["metadata"]["template"] == "project_journal"
    
    def test_full_workflow(self, tmp_path):
        """Test complete workflow from extraction to journal."""
        # This would test the full pipeline but requires mocking
        # the extraction process or having test data
        pass