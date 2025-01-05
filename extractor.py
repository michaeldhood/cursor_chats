import os
import json
import platform
import sqlite3

def get_cursor_chat_path():
    """Get the path to Cursor chat data based on the operating system."""
    system = platform.system()
    home = os.path.expanduser('~')
    
    if system == 'Linux' and os.path.exists('/proc/version'):
        # Check if running in WSL
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                # Get Windows user profile path from WSL
                windows_home = os.popen('cd /mnt/c && cmd.exe /c echo %USERPROFILE%').read().strip()
                # Convert Windows path to WSL path
                wsl_path = os.popen(f'wslpath "{windows_home}"').read().strip()
                windows_cursor_path = os.path.join(windows_home, 'AppData', 'Roaming', 'Cursor', 'User', 'workspaceStorage')
                return os.popen(f'wslpath "{windows_cursor_path}"').read().strip()
    
    if system == 'Windows':
        return os.path.join(home, 'AppData', 'Roaming', 'Cursor', 'User', 'workspaceStorage')
    else:
        raise OSError(f"Unsupported operating system: {system}")

def read_sqlite_db(db_path):
    """Read and extract chat data from the SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, let's see what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\nTables in database: {[table[0] for table in tables]}")
        
        # Try to find chat-related data in the ItemTable
        cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%chat%' OR key LIKE '%conversation%';")
        rows = cursor.fetchall()
        
        chat_data = []
        for key, value in rows:
            try:
                # Try to parse the value as JSON
                parsed_value = json.loads(value)
                chat_data.append({
                    'key': key,
                    'data': parsed_value
                })
                print(f"Found chat data with key: {key}")
            except json.JSONDecodeError:
                print(f"Non-JSON data found for key: {key}")
        
        conn.close()
        return chat_data
        
    except sqlite3.Error as e:
        print(f"SQLite error: {str(e)}")
        return None

def get_project_name(workspace_path):
    """Get the project name from the workspace.json file."""
    with open(workspace_path, 'r', encoding='utf-8') as f:
        workspace_data = json.load(f)
        return workspace_data.get('folder', '')

def analyze_workspace(workspace_path):
    """Analyze the contents of a workspace folder."""
    print(f"\nAnalyzing workspace: {os.path.basename(workspace_path)}")
    
    # Look specifically for state.vscdb files
    for root, dirs, files in os.walk(workspace_path):
        if 'workspace.json' in files:
            workspace_path = os.path.join(root, 'workspace.json')
            print(f"Found workspace.json at: {os.path.relpath(workspace_path, workspace_path)}")
            project_name = get_project_name(workspace_path)
            print(f"Project name: {project_name}")
        
        if 'state.vscdb' in files:
            db_path = os.path.join(root, 'state.vscdb')
            print(f"Found state.vscdb at: {os.path.relpath(db_path, workspace_path)}")
            
            # Read and analyze the database
            chat_data = read_sqlite_db(db_path)
            
            if chat_data:
                # Save extracted chat data to a JSON file
                output_file = f"chat_data_{os.path.basename(workspace_path)}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(chat_data, f, indent=2)
                print(f"Saved chat data to {output_file}")

def extract_chats():
    """Extract and analyze chat data from Cursor workspaces."""
    base_path = get_cursor_chat_path()
    
    if not os.path.exists(base_path):
        print(f"Workspace directory not found at: {base_path}")
        return
    
    print(f"Found Cursor workspace directory at: {base_path}")
    
    # Analyze each workspace folder
    workspaces = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    
    if not workspaces:
        print("No workspace folders found")
        return
    
    print(f"Found {len(workspaces)} workspace folders")
    
    for workspace in workspaces:
        workspace_path = os.path.join(base_path, workspace)
        analyze_workspace(workspace_path)