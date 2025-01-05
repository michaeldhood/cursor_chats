import pandas as pd
import json
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