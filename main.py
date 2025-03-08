from extractor import get_cursor_chat_path, get_workspace_path, get_project_name, extract_chats
from parser import parse_chat_json, convert_df_to_markdown
import os
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description='Extract and process Cursor chat data')
    parser.add_argument('--extract', action='store_true', help='Extract chat data from Cursor database')
    parser.add_argument('--convert', metavar='FILE', help='Convert a JSON chat file to CSV')
    parser.add_argument('--to-markdown', metavar='FILE', help='Convert a JSON chat file to markdown')
    parser.add_argument('--output-dir', metavar='DIR', default='chat_exports', help='Output directory for markdown files')
    
    args = parser.parse_args()
    
    if args.extract:
        print("Extracting chats from Cursor database...")
        extract_chats()
        print("Extraction completed.")
    
    if args.convert:
        if not os.path.exists(args.convert):
            print(f"Error: File {args.convert} not found")
            return
        
        print(f"Converting {args.convert} to CSV...")
        df = parse_chat_json(args.convert)
        
        output_file = os.path.splitext(args.convert)[0] + ".csv"
        df.to_csv(output_file, index=False)
        print(f"Conversion completed. Output saved to {output_file}")
    
    if args.to_markdown:
        if not os.path.exists(args.to_markdown):
            print(f"Error: File {args.to_markdown} not found")
            return
        
        print(f"Converting {args.to_markdown} to markdown files...")
        df = parse_chat_json(args.to_markdown)
        
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
        
        files = convert_df_to_markdown(df, args.output_dir)
        print(f"Conversion completed. {len(files)} markdown files created in {args.output_dir}")
    
    # If no arguments were provided, show basic info
    if not (args.extract or args.convert or args.to_markdown):
        cursor_path = get_cursor_chat_path()
        print(f"Cursor chat path: {cursor_path}")
        print("Use --help to see available commands")

if __name__ == "__main__":
    main()