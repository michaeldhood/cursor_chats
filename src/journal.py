"""
Module for generating structured journals from Cursor chat data using templates.
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class JournalTemplate:
    """
    Represents a journal template with customizable sections.
    """
    
    def __init__(self, name: str, sections: List[Dict[str, str]], metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a journal template.
        
        Args:
            name: Template name
            sections: List of section dictionaries with 'title', 'prompt', and optional 'content'
            metadata: Optional template metadata
        """
        self.name = name
        self.sections = sections
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for serialization."""
        return {
            'name': self.name,
            'sections': self.sections,
            'metadata': self.metadata,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JournalTemplate':
        """Create template from dictionary."""
        template = cls(data['name'], data['sections'], data.get('metadata'))
        template.created_at = data.get('created_at', datetime.now().isoformat())
        return template


class Journal:
    """
    Represents a generated journal with content and metadata.
    """
    
    def __init__(self, title: str, template_name: str, source_chats: List[str], 
                 sections: List[Dict[str, Any]], annotations: Optional[List[Dict[str, str]]] = None):
        """
        Initialize a journal instance.
        
        Args:
            title: Journal title
            template_name: Name of template used
            source_chats: List of source chat identifiers
            sections: Journal sections with content
            annotations: Optional user annotations
        """
        self.title = title
        self.template_name = template_name
        self.source_chats = source_chats
        self.sections = sections
        self.annotations = annotations or []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def add_annotation(self, text: str, section_id: Optional[str] = None, tags: Optional[List[str]] = None):
        """
        Add a user annotation to the journal.
        
        Args:
            text: Annotation text
            section_id: Optional section to attach annotation to
            tags: Optional tags for the annotation
        """
        annotation = {
            'text': text,
            'section_id': section_id,
            'tags': tags or [],
            'created_at': datetime.now().isoformat()
        }
        self.annotations.append(annotation)
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert journal to dictionary for serialization."""
        return {
            'title': self.title,
            'template_name': self.template_name,
            'source_chats': self.source_chats,
            'sections': self.sections,
            'annotations': self.annotations,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


def get_default_templates() -> List[JournalTemplate]:
    """
    Get the default journal templates.
    
    Returns:
        List of default JournalTemplate instances
    """
    templates = [
        JournalTemplate(
            name="decision_journal",
            sections=[
                {
                    "id": "what_happened",
                    "title": "What Happened?",
                    "prompt": "Summarize the key events, discussions, or problems addressed in this chat session.",
                    "content": ""
                },
                {
                    "id": "why",
                    "title": "Why?",
                    "prompt": "What were the underlying reasons, motivations, or root causes discussed?",
                    "content": ""
                },
                {
                    "id": "key_insights",
                    "title": "Key Insights",
                    "prompt": "What important insights, learnings, or discoveries emerged from this conversation?",
                    "content": ""
                },
                {
                    "id": "decisions_made",
                    "title": "Decisions Made",
                    "prompt": "What specific decisions were made? Include technical choices, design decisions, or strategic directions.",
                    "content": ""
                },
                {
                    "id": "next_steps",
                    "title": "Next Steps",
                    "prompt": "What are the concrete next actions or follow-up items identified?",
                    "content": ""
                }
            ],
            metadata={
                "description": "A comprehensive template for documenting decisions and their context",
                "use_cases": ["decision tracking", "technical discussions", "project planning"]
            }
        ),
        
        JournalTemplate(
            name="learning_journal",
            sections=[
                {
                    "id": "topic",
                    "title": "Topic & Context",
                    "prompt": "What topic or problem was being explored in this chat?",
                    "content": ""
                },
                {
                    "id": "what_learned",
                    "title": "What I Learned",
                    "prompt": "What new knowledge, techniques, or understanding did you gain?",
                    "content": ""
                },
                {
                    "id": "code_snippets",
                    "title": "Code & Examples",
                    "prompt": "Key code snippets, commands, or examples that were shared or discovered.",
                    "content": ""
                },
                {
                    "id": "challenges",
                    "title": "Challenges Encountered",
                    "prompt": "What difficulties, errors, or obstacles were encountered and how were they resolved?",
                    "content": ""
                },
                {
                    "id": "resources",
                    "title": "Resources & References",
                    "prompt": "Links, documentation, or other resources mentioned or discovered.",
                    "content": ""
                },
                {
                    "id": "follow_up",
                    "title": "Follow-up Questions",
                    "prompt": "What questions remain unanswered or what should be explored further?",
                    "content": ""
                }
            ],
            metadata={
                "description": "Template for capturing learning and knowledge from technical conversations",
                "use_cases": ["learning documentation", "skill development", "research notes"]
            }
        ),
        
        JournalTemplate(
            name="problem_solving",
            sections=[
                {
                    "id": "problem_statement",
                    "title": "Problem Statement",
                    "prompt": "Clearly define the problem or issue that was being addressed.",
                    "content": ""
                },
                {
                    "id": "approaches_tried",
                    "title": "Approaches Tried",
                    "prompt": "What different solutions or approaches were attempted?",
                    "content": ""
                },
                {
                    "id": "solution",
                    "title": "Solution",
                    "prompt": "What was the final solution or approach that worked?",
                    "content": ""
                },
                {
                    "id": "why_it_worked",
                    "title": "Why It Worked",
                    "prompt": "Explain why this solution was effective and what made it successful.",
                    "content": ""
                },
                {
                    "id": "lessons_learned",
                    "title": "Lessons Learned",
                    "prompt": "What insights can be applied to similar problems in the future?",
                    "content": ""
                }
            ],
            metadata={
                "description": "Template focused on problem-solving processes and solutions",
                "use_cases": ["debugging", "troubleshooting", "solution documentation"]
            }
        )
    ]
    
    return templates


def extract_chat_content(df: pd.DataFrame, tab_id: str) -> Dict[str, Any]:
    """
    Extract structured content from a specific chat tab.
    
    Args:
        df: DataFrame containing chat data
        tab_id: Tab ID to extract content for
        
    Returns:
        Dictionary with extracted chat content and metadata
    """
    chat_data = df[df['tabId'] == tab_id].copy()
    
    if chat_data.empty:
        raise ValueError(f"No chat data found for tab_id: {tab_id}")
    
    # Get basic metadata
    chat_title = chat_data['chatTitle'].iloc[0]
    messages = []
    
    # Extract messages in chronological order
    for _, row in chat_data.iterrows():
        message = {
            'type': row['type'],
            'messageType': row.get('messageType', ''),
            'content': row['text'] or row['rawText'] or '',
            'modelType': row.get('modelType', ''),
            'hasCodeBlock': row.get('hasCodeBlock', False),
            'timestamp': row.get('timestamp', '')
        }
        messages.append(message)
    
    # Extract key information
    user_messages = [msg for msg in messages if msg['type'] == 'user']
    ai_messages = [msg for msg in messages if msg['type'] == 'assistant']
    code_blocks = [msg for msg in messages if msg['hasCodeBlock']]
    
    return {
        'tab_id': tab_id,
        'title': chat_title,
        'messages': messages,
        'user_messages': user_messages,
        'ai_messages': ai_messages,
        'code_blocks': code_blocks,
        'message_count': len(messages),
        'has_code': len(code_blocks) > 0
    }


def generate_journal(df: pd.DataFrame, tab_id: str, template: Union[str, JournalTemplate], 
                    output_format: str = 'markdown', auto_fill: bool = True) -> Journal:
    """
    Generate a journal from chat data using a specified template.
    
    Args:
        df: DataFrame containing chat data
        tab_id: Tab ID to generate journal for
        template: Template name (string) or JournalTemplate instance
        output_format: Output format ('markdown', 'json', 'html')
        auto_fill: Whether to automatically fill sections with extracted content
        
    Returns:
        Generated Journal instance
    """
    # Get template
    if isinstance(template, str):
        templates = {t.name: t for t in get_default_templates()}
        if template not in templates:
            raise ValueError(f"Unknown template: {template}. Available: {list(templates.keys())}")
        template_obj = templates[template]
    else:
        template_obj = template
    
    # Extract chat content
    chat_content = extract_chat_content(df, tab_id)
    
    # Initialize journal sections
    sections = []
    for section_template in template_obj.sections:
        section = {
            'id': section_template['id'],
            'title': section_template['title'],
            'prompt': section_template['prompt'],
            'content': section_template.get('content', ''),
            'auto_content': ''
        }
        
        # Auto-fill content if requested
        if auto_fill:
            section['auto_content'] = _auto_fill_section(section, chat_content)
        
        sections.append(section)
    
    # Create journal
    journal = Journal(
        title=f"Journal: {chat_content['title']}",
        template_name=template_obj.name,
        source_chats=[tab_id],
        sections=sections
    )
    
    return journal


def _auto_fill_section(section: Dict[str, str], chat_content: Dict[str, Any]) -> str:
    """
    Auto-fill a journal section with relevant content from the chat.
    
    Args:
        section: Section dictionary with id, title, prompt
        chat_content: Extracted chat content
        
    Returns:
        Auto-generated content for the section
    """
    section_id = section['id']
    messages = chat_content['messages']
    
    # Simple auto-fill logic based on section type
    if section_id == 'what_happened' or section_id == 'topic':
        # Summarize the conversation flow
        user_intents = [msg['content'][:100] for msg in chat_content['user_messages'][:3]]
        return "**Main topics discussed:**\n" + "\n".join(f"- {intent}..." for intent in user_intents)
    
    elif section_id == 'code_snippets' and chat_content['has_code']:
        # Extract code blocks
        code_messages = [msg['content'] for msg in chat_content['code_blocks'][:2]]
        return "**Key code examples:**\n```\n" + "\n\n".join(code_messages) + "\n```"
    
    elif section_id == 'resources':
        # Look for URLs or references in messages
        all_text = " ".join(msg['content'] for msg in messages)
        # Simple URL detection
        import re
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', all_text)
        if urls:
            return "**Referenced URLs:**\n" + "\n".join(f"- {url}" for url in urls[:5])
    
    elif section_id == 'next_steps':
        # Look for action-oriented language
        action_words = ['should', 'need to', 'will', 'todo', 'next', 'implement', 'add', 'fix', 'update']
        relevant_messages = []
        for msg in messages:
            if any(word in msg['content'].lower() for word in action_words):
                relevant_messages.append(msg['content'][:150])
        if relevant_messages:
            return "**Identified action items:**\n" + "\n".join(f"- {msg}..." for msg in relevant_messages[:3])
    
    return "(Auto-fill not available for this section type)"


def export_journal(journal: Journal, output_path: str, format: str = 'markdown') -> str:
    """
    Export a journal to the specified format and path.
    
    Args:
        journal: Journal instance to export
        output_path: Output file path
        format: Export format ('markdown', 'json', 'html')
        
    Returns:
        Path to the exported file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    if format.lower() == 'json':
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(journal.to_dict(), f, indent=2, ensure_ascii=False)
    
    elif format.lower() == 'html':
        html_content = _journal_to_html(journal)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    else:  # Default to markdown
        markdown_content = _journal_to_markdown(journal)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    
    logger.info("Exported journal to %s", output_file)
    return str(output_file)


def _journal_to_markdown(journal: Journal) -> str:
    """Convert journal to markdown format."""
    lines = [
        f"# {journal.title}",
        "",
        f"**Template:** {journal.template_name}",
        f"**Created:** {journal.created_at}",
        f"**Source Chats:** {', '.join(journal.source_chats)}",
        "",
        "---",
        ""
    ]
    
    # Add sections
    for section in journal.sections:
        lines.extend([
            f"## {section['title']}",
            "",
            f"*{section['prompt']}*",
            ""
        ])
        
        # Add auto-content if available
        if section.get('auto_content'):
            lines.extend([
                "### Auto-extracted Content:",
                section['auto_content'],
                ""
            ])
        
        # Add manual content
        if section.get('content'):
            lines.extend([
                "### Notes:",
                section['content'],
                ""
            ])
        else:
            lines.extend([
                "*[Add your notes here]*",
                ""
            ])
        
        lines.append("")
    
    # Add annotations if any
    if journal.annotations:
        lines.extend([
            "---",
            "",
            "## Annotations",
            ""
        ])
        
        for i, annotation in enumerate(journal.annotations, 1):
            lines.extend([
                f"### Annotation {i}",
                f"**Created:** {annotation['created_at']}",
                ""
            ])
            
            if annotation.get('section_id'):
                lines.append(f"**Related to:** {annotation['section_id']}")
            
            if annotation.get('tags'):
                lines.append(f"**Tags:** {', '.join(annotation['tags'])}")
            
            lines.extend([
                "",
                annotation['text'],
                ""
            ])
    
    return "\n".join(lines)


def _journal_to_html(journal: Journal) -> str:
    """Convert journal to HTML format."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{journal.title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .metadata {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .section {{ margin-bottom: 30px; }}
            .prompt {{ font-style: italic; color: #666; margin-bottom: 10px; }}
            .auto-content {{ background: #e8f4f8; padding: 10px; border-left: 4px solid #0066cc; margin: 10px 0; }}
            .annotation {{ background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0; }}
            pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <h1>{journal.title}</h1>
        
        <div class="metadata">
            <p><strong>Template:</strong> {journal.template_name}</p>
            <p><strong>Created:</strong> {journal.created_at}</p>
            <p><strong>Source Chats:</strong> {', '.join(journal.source_chats)}</p>
        </div>
    """
    
    for section in journal.sections:
        html += f"""
        <div class="section">
            <h2>{section['title']}</h2>
            <div class="prompt">{section['prompt']}</div>
        """
        
        if section.get('auto_content'):
            html += f'<div class="auto-content"><strong>Auto-extracted:</strong><br>{section["auto_content"].replace(chr(10), "<br>")}</div>'
        
        if section.get('content'):
            html += f'<div class="content">{section["content"].replace(chr(10), "<br>")}</div>'
        else:
            html += '<div class="content"><em>[Add your notes here]</em></div>'
        
        html += '</div>'
    
    if journal.annotations:
        html += '<hr><h2>Annotations</h2>'
        for i, annotation in enumerate(journal.annotations, 1):
            html += f"""
            <div class="annotation">
                <h3>Annotation {i}</h3>
                <p><strong>Created:</strong> {annotation['created_at']}</p>
                <p>{annotation['text'].replace(chr(10), "<br>")}</p>
            </div>
            """
    
    html += """
    </body>
    </html>
    """
    
    return html


def save_template(template: JournalTemplate, templates_dir: str = 'templates') -> str:
    """
    Save a custom journal template to disk.
    
    Args:
        template: JournalTemplate instance to save
        templates_dir: Directory to save templates in
        
    Returns:
        Path to saved template file
    """
    templates_path = Path(templates_dir)
    templates_path.mkdir(parents=True, exist_ok=True)
    
    template_file = templates_path / f"{template.name}.json"
    
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
    
    logger.info("Saved template to %s", template_file)
    return str(template_file)


def load_template(template_path: str) -> JournalTemplate:
    """
    Load a journal template from disk.
    
    Args:
        template_path: Path to template file
        
    Returns:
        Loaded JournalTemplate instance
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return JournalTemplate.from_dict(data)


def list_templates(templates_dir: str = 'templates') -> List[str]:
    """
    List available journal templates.
    
    Args:
        templates_dir: Directory containing template files
        
    Returns:
        List of template names
    """
    # Default templates
    templates = [t.name for t in get_default_templates()]
    
    # Custom templates
    templates_path = Path(templates_dir)
    if templates_path.exists():
        for template_file in templates_path.glob('*.json'):
            templates.append(template_file.stem)
    
    return templates