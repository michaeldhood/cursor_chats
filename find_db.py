from src.extractor import get_cursor_chat_path, get_project_name
import os

def find_vscdb_files():
    base_path = get_cursor_chat_path()
    print(f"Cursor workspace directory: {base_path}")
    
    if not os.path.exists(base_path):
        print(f"Directory not found: {base_path}")
        return
    
    # Print directory structure with tree
    print(f"Directory structure:")
    for root, dirs, files in os.walk(base_path):
        level = root.replace(base_path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        for file in files:
            print(f"{indent}  {file}")

    workspaces = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    print(f"Found {len(workspaces)} workspaces")
    
    for workspace in workspaces:
        workspace_path = os.path.join(base_path, workspace)
        print(f"\nChecking workspace: {workspace}")
        
        # Look for workspace.json to get project name
        workspace_json_path = os.path.join(workspace_path, 'workspace.json')
        if os.path.exists(workspace_json_path):
            project_name = get_project_name(workspace_json_path)
            print(f"Project name: {project_name}")
        else:
            # Search for workspace.json in subdirectories
            for root, dirs, files in os.walk(workspace_path):
                if 'workspace.json' in files:
                    workspace_json_path = os.path.join(root, 'workspace.json')
                    project_name = get_project_name(workspace_json_path)
                    print(f"Project name: {project_name}")
                    print(f"Workspace JSON path: {workspace_json_path}")
                    break
        
        # Look for state.vscdb
        found = False
        for root, dirs, files in os.walk(workspace_path):
            if 'state.vscdb' in files:
                db_path = os.path.join(root, 'state.vscdb')
                print(f"✓ Found state.vscdb: {db_path}")
                found = True
        
        if not found:
            print("No state.vscdb files found in this workspace")

if __name__ == "__main__":
    find_vscdb_files() 