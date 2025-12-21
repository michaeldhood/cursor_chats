"""
Journal generation CLI commands.

Commands for generating structured journals from chat conversations
and managing journal templates.
"""
import json
import os
from pathlib import Path

import click

from src.journal import JournalGenerator, generate_journal_from_file


@click.group()
def journal():
    """Generate structured journals from chat conversations."""
    pass


@journal.command()
@click.argument('file', type=click.Path(exists=True))
@click.option(
    '--template',
    default='project_journal',
    help='Template to use (default: project_journal)'
)
@click.option(
    '--format',
    type=click.Choice(['markdown', 'html', 'json']),
    default='markdown',
    help='Output format (default: markdown)'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output file path'
)
@click.option(
    '--annotations',
    type=click.Path(exists=True),
    help='JSON file with manual annotations'
)
def generate(file, template, format, output, annotations):
    """Generate journal from chat file."""
    # Load annotations if provided
    annotations_dict = None
    if annotations:
        if os.path.exists(annotations):
            with open(annotations, 'r') as f:
                annotations_dict = json.load(f)
        else:
            click.secho(f"Annotations file not found: {annotations}", fg='yellow', err=True)
    
    # Generate journal
    click.echo(f"Generating journal from {file} using template '{template}'...")
    try:
        journal_result = generate_journal_from_file(
            file,
            template,
            annotations_dict,
            format
        )
        
        # Determine output file
        if output:
            output_file = output
        else:
            basename = os.path.splitext(os.path.basename(file))[0]
            ext = 'md' if format == 'markdown' else format
            output_file = f"journal_{basename}.{ext}"
        
        # Write journal to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(journal_result['content'])
        
        click.secho(f"Journal generated successfully: {output_file}", fg='green')
        click.echo(f"Template: {journal_result['metadata']['template']}")
        click.echo(f"Source chats: {journal_result['metadata']['source_chats']}")
        
    except Exception as e:
        click.secho(f"Error generating journal: {e}", fg='red', err=True)
        raise click.Abort()


@journal.group()
def template():
    """Manage journal templates."""
    pass


@template.command('list')
def template_list():
    """List available templates."""
    generator = JournalGenerator()
    templates = generator.list_templates()
    
    if templates:
        click.echo("Available templates:")
        for template_name in sorted(templates):
            template = generator.get_template(template_name)
            description = template.metadata.get('description', 'No description')
            click.echo(f"  {template_name} - {description}")
    else:
        click.echo("No templates found.")


@template.command('show')
@click.argument('name')
def template_show(name):
    """Show template details."""
    generator = JournalGenerator()
    template = generator.get_template(name)
    
    if not template:
        click.secho(f"Template not found: {name}", fg='red', err=True)
        raise click.Abort()
    
    click.echo(f"\nTemplate: {template.name}")
    click.echo(f"Description: {template.metadata.get('description', 'No description')}")
    click.echo(f"Use case: {template.metadata.get('use_case', 'General')}")
    click.echo("Sections:")
    
    for i, section in enumerate(template.sections, 1):
        click.echo(f"  {i}. {section['title'].replace('#', '').strip()}")
        click.echo(f"     {section['prompt']}")


@template.command('create')
@click.argument('name')
@click.option(
    '--from-file',
    type=click.Path(exists=True),
    help='Create from JSON file'
)
def template_create(name, from_file):
    """Create custom template."""
    generator = JournalGenerator()
    
    if from_file:
        if not os.path.exists(from_file):
            click.secho(f"Template file not found: {from_file}", fg='red', err=True)
            raise click.Abort()
        
        try:
            with open(from_file, 'r') as f:
                template_data = json.load(f)
            
            template = generator.create_custom_template(
                name,
                template_data['sections'],
                template_data.get('metadata', {})
            )
            
            click.secho(f"Created template '{template.name}' from {from_file}", fg='green')
        except Exception as e:
            click.secho(f"Error creating template: {e}", fg='red', err=True)
            raise click.Abort()
    else:
        click.secho("Interactive template creation not yet implemented.", fg='yellow', err=True)
        click.echo("Please use --from-file option with a JSON template file.", err=True)
        raise click.Abort()

