# Cursor Chat Extractor

A collection of tools for extracting, processing, and viewing chat logs from the Cursor AI editor.

## Overview

This project provides utilities to extract chat data from Cursor's SQLite database, convert it to various formats (CSV, JSON, Markdown), and view the contents of chat files. The goal is to make your Cursor chat history more accessible, portable, and analyzable.

## Features

- **Chat Data Extraction**: Extract chat data directly from Cursor's SQLite database
- **Multiple Output Formats**: Convert your chats to CSV, JSON, or Markdown formats
- **Chat Viewer**: Browse and view your chat files with a simple command-line interface
- **Cross-Platform Support**: Works on Windows, macOS, and Linux (including WSL)

## Project Components

- **extractor.py**: Handles the extraction of chat data from Cursor's SQLite database
- **parser.py**: Processes the extracted data and converts it to different formats
- **main.py**: Command-line interface for interacting with the extraction and conversion tools
- **view_chats.py**: A utility script for browsing and viewing chat files

## Usage

### Extracting Chat Data

To extract chat data from your Cursor installation:

```bash
python main.py --extract
```

This will create JSON files containing your chat data.

### Converting to CSV

To convert an extracted JSON file to CSV format:

```bash
python main.py --convert chat_data_[hash].json
```

### Converting to Markdown

To convert an extracted JSON file to Markdown format:

```bash
python main.py --to-markdown chat_data_[hash].json --output-dir markdown_chats
```

### Viewing Chat Files

To browse and view your chat files:

```bash
python view_chats.py                   # List all chat files
python view_chats.py chat_filename.md  # View a specific chat file
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