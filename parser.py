import pandas as pd
import json
import os
from extractor import get_cursor_chat_path


WORKSPACE_PATH = get_cursor_chat_path()

def parse_chat_json(file_path):
    # Read the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get the chat data from the specific key
    chat_data = data[1]['data']['tabs']  # Index 1 contains the chat data
    
    # List to store all bubble data
    rows = []
    
    # Iterate through each tab
    for tab in chat_data:
        tab_id = tab['tabId']
        chat_title = tab['chatTitle']
        
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
                'hasCodeBlock': bubble.get('hasCodeBlock', False)  # This will only exist for AI responses
            }
            rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    return df

def export_chats_to_markdown(chats_data, output_dir='.'):
    """
    Export chat data to markdown files.
    
    Args:
        chats_data: A list of chat data dictionaries, each containing 'id', 'title', and 'messages'
        output_dir: Directory where markdown files will be saved
    
    Returns:
        List of generated file paths
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    generated_files = []
    
    for chat in chats_data:
        # Create filename based on chat ID
        workspace_id = os.path.basename(os.path.dirname(output_dir)) if output_dir != '.' else ''
        filename = f"chat_{workspace_id}_{chat['id']}.md"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write chat title
            f.write(f"# {chat['title']}\n\n")
            
            # Write each message
            for message in chat['messages']:
                role = message.get('type', 'Unknown')
                content = message.get('content', '')
                f.write(f"## {role}\n\n{content}\n\n")
        
        generated_files.append(filepath)
        print(f"Exported chat to {filepath}")
    
    return generated_files

def convert_df_to_markdown(df, output_dir='.'):
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