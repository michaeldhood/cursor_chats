from extractor import get_cursor_chat_path, get_workspace_path, get_project_name
from parser import parse_chat_json
import os

cursor_path = get_cursor_chat_path()
print(f"Cursor chat path: {cursor_path}")

df = parse_chat_json('chat_data_9c67664fc9d2aaabd85b7c230db06ff9.json')

df.to_csv('chat_data.csv', index=False)