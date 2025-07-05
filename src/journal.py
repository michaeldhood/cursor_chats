"""
Module for generating structured journals from chat conversations.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class JournalTemplate:
    """Manages journal templates with configurable sections."""

    def __init__(
        self, name: str, sections: List[Dict[str, str]], metadata: Optional[Dict] = None
    ):
        """
        Initialize a journal template.

        Args:
            name: Template name
            sections: List of section dictionaries with 'title' and 'prompt' keys
            metadata: Optional metadata about the template
        """
        self.name = name
        self.sections = sections
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JournalTemplate":
        """Create template from dictionary."""
        return cls(
            name=data["name"],
            sections=data["sections"],
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "name": self.name,
            "sections": self.sections,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def substitute_variables(self, text: str, variables: Dict[str, str]) -> str:
        """
        Substitute template variables in text.

        Args:
            text: Text containing variables like {chat_title}
            variables: Dictionary of variable names to values

        Returns:
            Text with variables substituted
        """
        for var_name, var_value in variables.items():
            text = text.replace(f"{{{var_name}}}", str(var_value))
        return text


class JournalGenerator:
    """Generates structured journals from chat data."""

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the journal generator.

        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir or "journal_templates"
        self.templates: Dict[str, JournalTemplate] = {}
        self._load_default_templates()

        if os.path.exists(self.templates_dir):
            self._load_custom_templates()

    def _load_default_templates(self) -> None:
        """Load built-in default templates."""
        # Default project journal template
        project_template = JournalTemplate(
            name="project_journal",
            sections=[
                {
                    "title": "## What happened?",
                    "prompt": "Summarize the key activities, decisions, and outcomes from this chat session.",
                },
                {
                    "title": "## Why?",
                    "prompt": "Explain the reasoning behind decisions, the problems being solved, and context.",
                },
                {
                    "title": "## Key insights",
                    "prompt": "Document important discoveries, learnings, and patterns identified.",
                },
                {
                    "title": "## Next steps",
                    "prompt": "List actionable items, follow-up tasks, and future considerations.",
                },
            ],
            metadata={
                "description": "Standard project journal for documenting chat sessions",
                "use_case": "Project management and decision tracking",
            },
        )

        # Technical problem-solving template
        technical_template = JournalTemplate(
            name="technical_journal",
            sections=[
                {
                    "title": "## Problem statement",
                    "prompt": "Describe the technical challenge or issue being addressed.",
                },
                {
                    "title": "## Solution approach",
                    "prompt": "Document the approach taken, alternatives considered, and implementation details.",
                },
                {
                    "title": "## Code snippets & examples",
                    "prompt": "Include relevant code examples, configurations, or technical details.",
                },
                {
                    "title": "## Lessons learned",
                    "prompt": "Note what worked well, what didn't, and knowledge for future reference.",
                },
                {
                    "title": "## References & resources",
                    "prompt": "List helpful documentation, links, or resources discovered.",
                },
            ],
            metadata={
                "description": "Template for technical problem-solving sessions",
                "use_case": "Development and troubleshooting",
            },
        )

        # Quick meeting notes template
        meeting_template = JournalTemplate(
            name="meeting_notes",
            sections=[
                {
                    "title": "## Attendees & context",
                    "prompt": "Who was involved and what was the context or purpose?",
                },
                {
                    "title": "## Discussion points",
                    "prompt": "Key topics discussed and perspectives shared.",
                },
                {
                    "title": "## Decisions made",
                    "prompt": "Concrete decisions reached and their rationale.",
                },
                {
                    "title": "## Action items",
                    "prompt": "Tasks assigned, deadlines, and responsibilities.",
                },
            ],
            metadata={
                "description": "Template for meeting and discussion documentation",
                "use_case": "Team meetings and collaborative sessions",
            },
        )

        self.templates = {
            "project_journal": project_template,
            "technical_journal": technical_template,
            "meeting_notes": meeting_template,
        }

    def _load_custom_templates(self) -> None:
        """Load custom templates from templates directory."""
        templates_path = Path(self.templates_dir)
        for template_file in templates_path.glob("*.json"):
            try:
                with open(template_file, "r") as f:
                    template_data = json.load(f)
                    template = JournalTemplate.from_dict(template_data)
                    self.templates[template.name] = template
                    logger.debug("Loaded custom template: %s", template.name)
            except Exception as e:
                logger.error("Error loading template %s: %s", template_file, e)

    def get_template(self, name: str) -> Optional[JournalTemplate]:
        """Get a template by name."""
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self.templates.keys())

    def create_custom_template(
        self,
        name: str,
        sections: List[Dict[str, str]],
        metadata: Optional[Dict] = None,
        save: bool = True,
    ) -> JournalTemplate:
        """
        Create a new custom template.

        Args:
            name: Template name
            sections: List of section dictionaries
            metadata: Optional template metadata
            save: Whether to save template to disk

        Returns:
            Created template
        """
        template = JournalTemplate(name, sections, metadata)
        self.templates[name] = template

        if save:
            self._save_template(template)

        return template

    def _save_template(self, template: JournalTemplate) -> None:
        """Save template to disk."""
        os.makedirs(self.templates_dir, exist_ok=True)
        template_path = Path(self.templates_dir) / f"{template.name}.json"

        with open(template_path, "w") as f:
            json.dump(template.to_dict(), f, indent=2)

        logger.info("Saved template to %s", template_path)

    def generate_journal(
        self,
        chat_data: Union[pd.DataFrame, Dict[str, Any]],
        template_name: str = "project_journal",
        annotations: Optional[Dict[str, str]] = None,
        output_format: str = "markdown",
    ) -> Dict[str, Any]:
        """
        Generate a journal from chat data.

        Args:
            chat_data: Chat DataFrame or conversation data
            template_name: Name of template to use
            annotations: Manual annotations to include
            output_format: Output format (markdown, html, json)

        Returns:
            Dictionary containing journal content and metadata
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # Extract variables from chat data
        variables = self._extract_variables(chat_data)

        # Generate journal content
        journal_content = self._generate_content(
            template, chat_data, variables, annotations
        )

        # Format output
        if output_format == "markdown":
            formatted_content = self._format_as_markdown(
                journal_content, template, variables
            )
        elif output_format == "html":
            formatted_content = self._format_as_html(
                journal_content, template, variables
            )
        elif output_format == "json":
            formatted_content = json.dumps(journal_content, indent=2)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        return {
            "content": formatted_content,
            "metadata": {
                "template": template_name,
                "generated_at": datetime.now().isoformat(),
                "format": output_format,
                "source_chats": variables.get("chat_count", 0),
                "tags": variables.get("tags", []),
            },
        }

    def _extract_variables(
        self, chat_data: Union[pd.DataFrame, Dict[str, Any]]
    ) -> Dict[str, str]:
        """Extract variables from chat data for template substitution."""
        variables = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
        }

        if isinstance(chat_data, pd.DataFrame):
            # Extract from DataFrame
            if not chat_data.empty:
                variables["chat_title"] = chat_data.iloc[0].get(
                    "chatTitle", "Untitled Chat"
                )
                variables["chat_count"] = str(
                    len(chat_data["tabId"].unique())
                    if "tabId" in chat_data.columns
                    else 1
                )

                # Extract tags if available
                if "tags" in chat_data.columns:
                    all_tags = []
                    for tags_list in chat_data["tags"].dropna():
                        if isinstance(tags_list, list):
                            all_tags.extend(tags_list)
                    variables["tags"] = list(set(all_tags))
                else:
                    variables["tags"] = []

        elif isinstance(chat_data, dict):
            # Extract from dictionary
            variables["chat_title"] = chat_data.get("title", "Untitled Chat")
            variables["chat_count"] = "1"
            variables["tags"] = chat_data.get("tags", [])

        return variables

    def _generate_content(
        self,
        template: JournalTemplate,
        chat_data: Any,
        variables: Dict[str, str],
        annotations: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Generate the main journal content."""
        content = {
            "title": template.substitute_variables("Journal: {chat_title}", variables),
            "sections": [],
        }

        for section in template.sections:
            section_content = {
                "title": template.substitute_variables(section["title"], variables),
                "prompt": template.substitute_variables(section["prompt"], variables),
                "content": "",  # Placeholder for user content
            }

            # Normalize section title to create a stable key (lowercase, words joined with underscores,
            # remove any characters that are not alphanumeric or underscore). This ensures that
            # annotation dictionaries can use simple keys like "what_happened" regardless of extra
            # punctuation (e.g., question marks) or Markdown heading symbols.
            section_key = re.sub(r"[^a-z0-9_]+", "_", section["title"].lower()).strip(
                "_"
            )

            # Add annotation if provided for this section
            if annotations and section_key in annotations:
                section_content["content"] = annotations[section_key]

            content["sections"].append(section_content)

        return content

    def _format_as_markdown(
        self,
        content: Dict[str, Any],
        template: JournalTemplate,
        variables: Dict[str, str],
    ) -> str:
        """Format journal content as Markdown."""
        lines = [
            f"# {content['title']}",
            "",
            f"**Generated:** {variables['timestamp']}",
            f"**Template:** {template.name}",
            "",
        ]

        # Add tags if available
        if variables.get("tags"):
            tags_str = ", ".join(f"`{tag}`" for tag in variables["tags"])
            lines.extend([f"**Tags:** {tags_str}", ""])

        # Add sections
        for section in content["sections"]:
            lines.append(section["title"])
            lines.append("")
            lines.append(f"*{section['prompt']}*")
            lines.append("")

            if section["content"]:
                lines.append(section["content"])
            else:
                lines.append("<!-- Add your content here -->")

            lines.append("")

        return "\n".join(lines)

    def _format_as_html(
        self,
        content: Dict[str, Any],
        template: JournalTemplate,
        variables: Dict[str, str],
    ) -> str:
        """Format journal content as HTML."""
        html_parts = [
            "<html><head><title>{}</title></head><body>".format(content["title"]),
            f"<h1>{content['title']}</h1>",
            f"<p><strong>Generated:</strong> {variables['timestamp']}</p>",
            f"<p><strong>Template:</strong> {template.name}</p>",
        ]

        # Add tags if available
        if variables.get("tags"):
            tags_html = ", ".join(f"<code>{tag}</code>" for tag in variables["tags"])
            html_parts.append(f"<p><strong>Tags:</strong> {tags_html}</p>")

        # Add sections
        for section in content["sections"]:
            title = section["title"].replace("##", "").strip()
            html_parts.extend(
                [f"<h2>{title}</h2>", f"<p><em>{section['prompt']}</em></p>"]
            )

            if section["content"]:
                html_parts.append(f"<div>{section['content']}</div>")
            else:
                html_parts.append("<div><!-- Add your content here --></div>")

        html_parts.append("</body></html>")
        return "\n".join(html_parts)


def generate_journal_from_file(
    file_path: str,
    template_name: str = "project_journal",
    annotations: Optional[Dict[str, str]] = None,
    output_format: str = "markdown",
) -> Dict[str, Any]:
    """
    Generate a journal from a chat JSON file.

    Args:
        file_path: Path to the chat JSON file
        template_name: Name of template to use
        annotations: Manual annotations to include
        output_format: Output format (markdown, html, json)

    Returns:
        Dictionary containing journal content and metadata
    """
    from src.parser import parse_chat_json

    # Parse the chat file
    df = parse_chat_json(file_path)

    # Generate journal
    generator = JournalGenerator()
    return generator.generate_journal(df, template_name, annotations, output_format)
