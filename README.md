# Cursor Chat Extractor

A collection of tools for extracting, processing, and viewing chat logs from the Cursor AI editor.

## Overview

This project provides utilities to extract chat data from Cursor's SQLite database, convert it to various formats (CSV, JSON, Markdown), and view the contents of chat files. The goal is to make your Cursor chat history more accessible, portable, and analyzable.

## Features

- **Chat Data Extraction**: Extract chat data directly from Cursor's SQLite database
- **Multiple Output Formats**: Convert your chats to CSV, JSON, or Markdown formats
- **Chat Viewer**: Browse and view your chat files with a simple command-line interface
- **Cross-Platform Support**: Works on Windows, macOS, and Linux (including WSL)
- **Smart Tagging System**: Automatically tag chats by programming language, framework, and topic
- **Tag Management**: Add, remove, search, and organize chats with hierarchical tags

## Project Components

- **extractor.py**: Handles the extraction of chat data from Cursor's SQLite database
- **parser.py**: Processes the extracted data and converts it to different formats
- **main.py**: Command-line interface for interacting with the extraction and conversion tools
- **view_chats.py**: A utility script for browsing and viewing chat files

## Usage

Add `--verbose` to any command to see detailed logging output.

### Extracting Chat Data

To extract chat data from your Cursor installation:

```bash
python -m src extract
python -m src extract --verbose  # detailed logging

# Extract to a custom directory
python -m src extract --output-dir ./my_extracts

# Use a custom filename pattern
python -m src extract --filename-pattern "cursor_{workspace}_backup.json"

# Combine options
python -m src extract -o ./backups --filename-pattern "{workspace}_chats.json"
```

This will create JSON files containing your chat data.

### Converting to CSV

To convert an extracted JSON file to CSV format:

```bash
python -m src convert chat_data_[hash].json

# Save to a custom directory
python -m src convert chat_data_[hash].json --output-dir ./csv_exports

# Use a custom output filename
python -m src convert chat_data_[hash].json --output-file my_chats.csv

# Combine options
python -m src convert chat_data_[hash].json -o ./exports --output-file cursor_backup.csv
```

### Converting to Markdown

To convert an extracted JSON file to Markdown format:

```bash
python -m src convert chat_data_[hash].json --format markdown --output-dir markdown_chats
```

### Viewing Chat Files

To browse and view your chat files:

```bash
python -m src view                   # List all chat files
python -m src view chat_filename.md  # View a specific chat file
```

### Managing Tags

The tagging system helps organize and categorize your chat conversations:

```bash
# Auto-tag chats from a JSON file
python -m src tag auto chat_data_[hash].json

# Manually add tags to a chat
python -m src tag add [chat_id] python api testing

# Remove tags from a chat
python -m src tag remove [chat_id] testing

# List all tags with usage counts
python -m src tag list --all

# List tags for a specific chat
python -m src tag list [chat_id]

# Find chats by tag (supports wildcards)
python -m src tag find "language/python"
python -m src tag find "topic/*"
python -m src tag find "*/api"

# Use a custom tags file
python -m src tag auto chat_data.json --tags-file my_tags.json
```

Tags are hierarchical and normalized (lowercase, spaces become hyphens). The auto-tagger recognizes:
- **Languages**: Python, JavaScript, TypeScript, Java, C++, Rust, Go, Ruby, PHP, Swift
- **Frameworks**: React, Vue, Angular, Django, Flask, Express, Spring, Rails, FastAPI, Next.js
- **Topics**: API/REST, databases, testing, Docker/Kubernetes, Git, CI/CD, security, performance, debugging
- **AI/ML**: Machine learning, LLMs, NLP, computer vision

### Batch Processing

Process multiple files at once with the `--all` flag or use the `batch` command:

```bash
# Convert all JSON files to markdown
python -m src convert --all --format markdown

# Convert all files matching a pattern
python -m src convert --all --pattern "chat_data_2024*.json" --format csv

# Auto-tag all JSON files
python -m src tag auto --all

# Run complete pipeline: extract, convert to markdown, and tag
python -m src batch

# Run specific batch operations
python -m src batch --convert --tag  # Skip extraction
python -m src batch --extract --convert --format csv  # Extract and convert to CSV

# Specify output directory for batch operations
python -m src batch --output-dir ./my_exports
```

## File Naming Convention

The exported files follow these naming conventions:
- **JSON extraction**: `chat_data_[workspace_hash].json`
- **Markdown files**: `chat_[workspace_hash]_[id].md`
- **CSV files**: `chat_data_[hash].csv`

## Installation

No special installation required. Just make sure you have Python installed with the following libraries:
- pandas
- sqlite3 (usually built-in with Python)

```bash
pip install pandas
```

## Development

This project evolved from a simple script to extract Cursor chat logs to a more robust set of tools for working with chat data. Contributions and improvements are welcome!

## Notes

- The extraction process does not modify your original Cursor database
- Cursor stores chat data in SQLite databases which may change format in future versions 
