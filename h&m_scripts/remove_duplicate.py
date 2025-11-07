import json
import pandas as pd
from typing import List, Dict, Any
from pathlib import Path

# --- CONFIGURATION ---
# The folder containing the JSON files you want to clean.
FOLDER_PATH = Path('h&m_scripts/processed_json/') 
# The key used to define uniqueness (e.g., 'id' or 'url').
UNIQUE_CHECK_KEY = 'id'
# Strategy for deduplication ('first' keeps the first record, 'last' keeps the last).
KEEP_STRATEGY = 'first'
# -------------------------


def deduplicate_json_file(
    file_path: Path,
    unique_check_key: str,
    keep_strategy: str
) -> None:
    """
    Loads a JSON file, deduplicates the list of records based on a key,
    and overwrites the original file with the cleaned, unique data.
    
    Args:
        file_path: Path to the input JSON file (as a pathlib.Path object).
        unique_check_key: The key used to check for uniqueness (e.g., 'id').
        keep_strategy: Strategy for deduplication ('first' or 'last').
    """
    
    # 1. Load the data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data: List[Dict[str, Any]] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error loading/decoding JSON from '{file_path.name}': {e}. Skipping.")
        return
    
    total_records = len(data)

    # 2. Convert to DataFrame for quick deduplication
    df = pd.DataFrame(data)
    
    # Filter out records where the unique key is missing (they can't be duplicates)
    df_non_null = df[df[unique_check_key].notna()].copy()
    df_null = df[df[unique_check_key].isna()].copy()

    # Perform the deduplication: Keep only one record per unique_check_key value
    df_unique = df_non_null.drop_duplicates(
        subset=[unique_check_key],
        keep=keep_strategy
    )
    
    # Combine the cleaned unique data with any records that had a null key
    df_cleaned = pd.concat([df_unique, df_null], ignore_index=True)
    
    # 3. Convert back to a list of dictionaries
    unique_data_list = df_cleaned.to_dict('records')
    records_removed = total_records - len(unique_data_list)
    
    # 4. Save the final unique records, OVERWRITING the original file
    try:
        with open(f'h&m_scripts/deduplicated/{file_path.name}', 'w', encoding='utf-8') as f:
            json.dump(unique_data_list, f, indent=4)
        
        # --- Print Results ---
        print(f"✅ Cleaned '{file_path.name}'")
        print(f"   - Initial Records: {total_records}")
        print(f"   - Records Removed: **{records_removed}**")
        print(f"   - Final Unique Records: {len(unique_data_list)}")
        print("-" * 30)

    except Exception as e:
        print(f"❌ Error saving cleaned JSON to '{file_path.name}': {e}")


if __name__ == '__main__':
    
    print("-" * 40)
    print(f"Starting Deduplication on folder: {FOLDER_PATH}")
    print(f"Uniqueness Check Key: '{UNIQUE_CHECK_KEY}' | Keep: '{KEEP_STRATEGY}'")
    print("-" * 40)
    
    # Check if the folder exists
    if not FOLDER_PATH.is_dir():
        print(f"Error: The folder path '{FOLDER_PATH}' does not exist or is not a directory.")
    else:
        # Iterate over all files ending with '.json' in the folder
        json_files = list(FOLDER_PATH.glob('*.json'))
        
        if not json_files:
            print(f"No JSON files found in the directory: {FOLDER_PATH}")
        else:
            for file_path in json_files:
                # Run the cleaning process, overwriting the file with unique records
                    deduplicate_json_file(
                        file_path=file_path,
                        unique_check_key=UNIQUE_CHECK_KEY,
                        keep_strategy=KEEP_STRATEGY
                )
            print("\n✨ **Batch processing complete!** All original JSON files have been overwritten with their deduplicated versions.")
            print("-" * 40)