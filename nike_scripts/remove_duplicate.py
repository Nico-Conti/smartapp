import json
import pandas as pd
from typing import List, Dict, Any
from pathlib import Path

# --- CONFIGURATION ---
# The specific file path to deduplicate
SINGLE_FILE_PATH = Path('nike_catalog/final.json') 
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
    
    # Filter out records where the unique key is NaN/None (they can't be duplicates of valid IDs)
    df_non_null = df[df[unique_check_key].notna()].copy()
    df_null = df[df[unique_check_key].isna()].copy()

    # Perform the deduplication on records with non-missing unique keys
    df_unique = df_non_null.drop_duplicates(
        subset=[unique_check_key],
        keep=keep_strategy
    )
    
    # Combine the cleaned unique data with any records that had a null key
    # NOTE: Records with null keys will remain in the output as they are not compared for duplicates.
    df_cleaned = pd.concat([df_unique, df_null], ignore_index=True)
    
    # 3. Convert back to a list of dictionaries
    unique_data_list = df_cleaned.to_dict('records')
    records_removed = total_records - len(unique_data_list)
    
    # 4. Save the final unique records, OVERWRITING the original file
    try:
        # Note: Using file_path directly ensures the original file is overwritten.
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(unique_data_list, f, indent=4)
        
        # --- Print Results ---
        print(f"\n✨ **DEDUPLICATION COMPLETE** on '{file_path.name}'")
        print(f"   - Initial Records: {total_records}")
        print(f"   - Records Removed: **{records_removed}**")
        print(f"   - Final Unique Records: {len(unique_data_list)}")
        print("-" * 40)

    except Exception as e:
        print(f"❌ Error saving cleaned JSON to '{file_path.name}': {e}")


if __name__ == '__main__':
    
    # The dedicated call for the single file
    deduplicate_json_file(
        file_path=SINGLE_FILE_PATH,
        unique_check_key=UNIQUE_CHECK_KEY,
        keep_strategy=KEEP_STRATEGY
    )