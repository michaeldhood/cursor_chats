"""
Module for parsing and converting Cursor chat data to various formats.
"""
import os
import json
from typing import List, Dict, Any, Optional
import pandas as pd
from pathlib import Path

def parse_chat_json(file_path: str) -> pd.DataFrame:
    """
    Parse a Cursor chat JSON file and convert it to a DataFrame.
    
    Args:
        file_path: Path to the JSON file containing chat data
        
    Returns:
        DataFrame containing structured chat data
        
    Raises:
        FileNotFoundError: If the specified file doesn't exist
        json.JSONDecodeError: If the file isn't valid JSON
        KeyError: If the expected data structure isn't found
    """
    # Read the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Find the chat data in the JSON structure
    chat_data = None
    for item in data:
        if 'data' in item and 'tabs' in item.get('data', {}):
            chat_data = item['data']['tabs']
            break
    
    if chat_data is None:
        raise KeyError("Could not find chat data in the JSON file")
    
    # List to store all bubble data
    rows = []
    
    # Iterate through each tab
    for tab in chat_data:
        tab_id = tab.get('tabId', '')
        chat_title = tab.get('chatTitle', 'Untitled Chat')
        
        # Iterate through bubbles
        for bubble in tab.get('bubbles', []):
            row = {
                'tabId': tab_id,
                'chatTitle': chat_title,
                'type': bubble.get('type'),
                'messageType': bubble.get('messageType'),
                'id': bubble.get('id'),
                'requestId': bubble.get('requestId'),
                'text': bubble.get('text'),
                'rawText': bubble.get('rawText'),
                'modelType': bubble.get('modelType'),  # This will only exist for AI responses
                'hasCodeBlock': bubble.get('hasCodeBlock', False),  # This will only exist for AI responses
                'timestamp': bubble.get('timestamp')
            }
            rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    return df


def export_chats_to_markdown(chats_data: List[Dict[str, Any]], output_dir: str = '.') -> List[str]:
    """
    Export chat data to markdown files.
    
    Args:
        chats_data: A list of chat data dictionaries, each containing 'id', 'title', and 'messages'
        output_dir: Directory where markdown files will be saved
    
    Returns:
        List of generated file paths
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
    
    generated_files = []
    
    for chat in chats_data:
        # Create filename based on chat ID
        workspace_id = Path(output_dir).name if output_dir != '.' else ''
        filename = f"chat_{workspace_id}_{chat['id']}.md"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write chat title
            f.write(f"# {chat['title']}\n\n")
            
            # Write each message
            for message in chat['messages']:
                role = message.get('type', 'Unknown')
                content = message.get('content', '')
                f.write(f"## {role}\n\n{content}\n\n")
        
        generated_files.append(str(filepath))
        print(f"Exported chat to {filepath}")
    
    return generated_files


def convert_df_to_markdown(df: pd.DataFrame, output_dir: str = '.') -> List[str]:
    """
    Convert a DataFrame of chat messages to markdown files.
    
    Args:
        df: DataFrame with chat messages
        output_dir: Directory where markdown files will be saved
    
    Returns:
        List of generated file paths
    """
    # Group the DataFrame by tabId and chatTitle
    grouped = df.groupby(['tabId', 'chatTitle'])
    
    chats_data = []
    
    for (tab_id, chat_title), group in grouped:
        messages = []
        
        # Convert each row to a message format
        for _, row in group.iterrows():
            message = {
                'type': row['type'],
                'content': row['text'] or row['rawText'] or ''
            }
            messages.append(message)
        
        chats_data.append({
            'id': tab_id,
            'title': chat_title,
            'messages': messages
        })
    
    return export_chats_to_markdown(chats_data, output_dir)


def export_to_csv(df: pd.DataFrame, output_file: str) -> str:
    """
    Export a DataFrame to a CSV file.
    
    Args:
        df: DataFrame to export
        output_file: Path to the output CSV file
        
    Returns:
        Path to the created CSV file
    """
    df.to_csv(output_file, index=False)
    print(f"Exported data to {output_file}")
    return output_file 