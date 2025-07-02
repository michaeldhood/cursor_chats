"""
Tests for the journal generation functionality.
"""
import pytest
import pandas as pd
from pathlib import Path

from src.journal import (
    generate_journal, get_default_templates, export_journal,
    JournalTemplate, Journal, extract_chat_content
)
from src.parser import parse_chat_json


def test_get_default_templates():
    """Test that default templates are available and properly structured."""
    templates = get_default_templates()
    
    assert len(templates) == 3
    template_names = [t.name for t in templates]
    
    assert 'decision_journal' in template_names
    assert 'learning_journal' in template_names
    assert 'problem_solving' in template_names
    
    # Check structure of decision_journal template
    decision_template = next(t for t in templates if t.name == 'decision_journal')
    assert len(decision_template.sections) == 5
    assert decision_template.sections[0]['title'] == 'What Happened?'
    assert 'prompt' in decision_template.sections[0]


def test_journal_template_creation():
    """Test creating custom journal templates."""
    sections = [
        {
            "id": "test_section",
            "title": "Test Section",
            "prompt": "This is a test prompt",
            "content": ""
        }
    ]
    
    template = JournalTemplate("test_template", sections)
    
    assert template.name == "test_template"
    assert len(template.sections) == 1
    assert template.sections[0]['id'] == 'test_section'
    assert template.created_at is not None
    
    # Test serialization
    template_dict = template.to_dict()
    assert template_dict['name'] == "test_template"
    assert template_dict['sections'] == sections
    
    # Test deserialization
    restored_template = JournalTemplate.from_dict(template_dict)
    assert restored_template.name == template.name
    assert restored_template.sections == template.sections


@pytest.mark.skipif(
    not Path('examples/chat_data_de5562f3e8c437246be75a12e9e89d4d.json').exists(),
    reason="Example chat data file not found"
)
def test_journal_generation_with_example_data():
    """Test journal generation using example chat data."""
    chat_file = 'examples/chat_data_de5562f3e8c437246be75a12e9e89d4d.json'
    
    # Parse the chat data
    df = parse_chat_json(chat_file)
    
    # Get first available tab_id
    tab_id = df['tabId'].iloc[0]
    
    # Generate journal
    journal = generate_journal(
        df=df,
        tab_id=tab_id,
        template='decision_journal',
        auto_fill=True
    )
    
    assert journal.title.startswith('Journal:')
    assert journal.template_name == 'decision_journal'
    assert len(journal.sections) == 5
    assert tab_id in journal.source_chats
    
    # Check that auto-fill worked for at least one section
    auto_filled_sections = [s for s in journal.sections if s.get('auto_content')]
    assert len(auto_filled_sections) > 0


def test_journal_export_formats():
    """Test exporting journals in different formats."""
    # Create a simple journal for testing
    sections = [
        {
            'id': 'test_section',
            'title': 'Test Section',
            'prompt': 'Test prompt',
            'content': 'Test content',
            'auto_content': 'Auto content'
        }
    ]
    
    journal = Journal(
        title="Test Journal",
        template_name="test_template",
        source_chats=["test-tab-id"],
        sections=sections
    )
    
    # Test markdown export
    md_path = export_journal(journal, 'test_journal.md', 'markdown')
    assert Path(md_path).exists()
    
    with open(md_path, 'r') as f:
        content = f.read()
        assert 'Test Journal' in content
        assert 'Test Section' in content
        assert 'Test prompt' in content
    
    # Test HTML export  
    html_path = export_journal(journal, 'test_journal.html', 'html')
    assert Path(html_path).exists()
    
    with open(html_path, 'r') as f:
        content = f.read()
        assert '<title>Test Journal</title>' in content
        assert '<h2>Test Section</h2>' in content
    
    # Test JSON export
    json_path = export_journal(journal, 'test_journal.json', 'json')
    assert Path(json_path).exists()
    
    # Cleanup
    Path(md_path).unlink(missing_ok=True)
    Path(html_path).unlink(missing_ok=True)
    Path(json_path).unlink(missing_ok=True)


def test_journal_annotations():
    """Test adding annotations to journals."""
    journal = Journal(
        title="Test Journal",
        template_name="test_template", 
        source_chats=["test-tab-id"],
        sections=[]
    )
    
    # Add annotation
    journal.add_annotation(
        text="This is a test annotation",
        section_id="test_section",
        tags=["test", "annotation"]
    )
    
    assert len(journal.annotations) == 1
    annotation = journal.annotations[0]
    assert annotation['text'] == "This is a test annotation"
    assert annotation['section_id'] == "test_section"
    assert annotation['tags'] == ["test", "annotation"]
    assert 'created_at' in annotation


@pytest.mark.skipif(
    not Path('examples/chat_data_de5562f3e8c437246be75a12e9e89d4d.json').exists(),
    reason="Example chat data file not found"
)
def test_extract_chat_content():
    """Test extracting structured content from chat data."""
    chat_file = 'examples/chat_data_de5562f3e8c437246be75a12e9e89d4d.json'
    df = parse_chat_json(chat_file)
    
    # Get first available tab_id
    tab_id = df['tabId'].iloc[0]
    
    # Extract content
    content = extract_chat_content(df, tab_id)
    
    assert content['tab_id'] == tab_id
    assert 'title' in content
    assert 'messages' in content
    assert 'user_messages' in content
    assert 'ai_messages' in content
    assert content['message_count'] > 0
    assert isinstance(content['has_code'], bool)