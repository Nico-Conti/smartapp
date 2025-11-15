import json
import pandas as pd
from typing import List, Dict, Any
from pathlib import Path

# --- CONFIGURATION ---
FOLDER_PATH = Path('adidas_catalog/final/') 

final_json: List[Dict[str, Any]] = []

if __name__ == '__main__':

    if not FOLDER_PATH.is_dir():
        print(f"❌ Error: The folder path '{FOLDER_PATH}' does not exist or is not a directory.")
    else:
        json_files = list(FOLDER_PATH.glob('*.json'))
        
        if not json_files:
            print(f"⚠️ No JSON files found in the directory: {FOLDER_PATH}")
        else:
            print(f"Starting aggregation of {len(json_files)} files...")
            
            for file_path in json_files:
                
                print(f"Processing file: {file_path.name}") # Added for clear tracing
                
                try:
                    # 1. Load the JSON data
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 2. Extend the final_json list
                    if isinstance(data, list):
                        final_json.extend(data)
                        print(f"   -> Success: Loaded {len(data)} records.")
                    else:
                        final_json.append(data)
                        print(f"   -> Success: Loaded 1 record (non-list JSON).")
                        
                except json.JSONDecodeError as e:
                    # Specific handler for the JSON syntax error
                    print(f"   ❌ **CRITICAL ERROR** in file {file_path.name}: JSONDecodeError: {e}")
                    print("   ⚠️ This file will be skipped. Please manually check and fix the syntax.")
                except Exception as e:
                    # General handler for other unexpected I/O or file errors
                    print(f"   ❌ An unexpected error occurred while processing {file_path.name}: {e}")

        # 3. Save the combined records into a single JSON file
        output_path = Path('adidas_catalog/final.json')
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_json, f, indent=4)
            print(f"\n--- Aggregation Complete ---")
            print(f"Total unique records saved: **{len(final_json)}** to {output_path.name}")
        except Exception as e:
            print(f"❌ Error saving the final combined file: {e}")