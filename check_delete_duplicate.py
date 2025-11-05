import json
import csv
import pandas as pd
from typing import List, Dict, Any, Tuple

# --- CONFIGURATION ---
INPUT_FILE = 'zalando_scripts/scarpe-piatte-donna.json'
# The key used to define uniqueness (e.g., 'url')
DUPLICATE_KEY = 'url'
# The key that holds the unique Supabase ID for deletion (must exist in data)
RECORD_ID_KEY = 'id'
# Define the output file path for the list of unique IDs to be deleted
OUTPUT_ID_CSV_PATH = 'duplicate_record_ids.csv'
# Define the output file path for the final CLEANED JSON data
OUTPUT_UNIQUE_JSON_PATH = 'cleaned_unique_records.json'
# -------------------------


def analyze_and_clean_data(
    file_path: str,
    duplicate_key: str,
    record_id_key: str,
    output_id_csv_path: str,
    output_unique_json_path: str,
    keep_duplicate: str = 'first'
) -> None:
    """
    Analyzes JSON data for duplicates, extracts IDs of duplicate records for deletion,
    and saves the final deduplicated dataset to a new JSON file.
    
    Args:
        file_path: Path to the input JSON file.
        duplicate_key: The key used to check for uniqueness (e.g., 'url').
        record_id_key: The key holding the unique record identifier (e.g., 'id').
        output_id_csv_path: Path to save the list of IDs of duplicate records.
        output_unique_json_path: Path to save the final cleaned JSON data.
        keep_duplicate: Strategy for deduplication ('first' or 'last').
    """
    
    # Load the data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data: List[Dict[str, Any]] = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found. Please check the path.")
        return
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from '{file_path}'. Check file integrity.")
        return
    
    total_records = len(data)

    # 1. Collect all non-null DUPLICATE_KEY values and count their occurrences
    # Also collect records without the record_id_key for metric calculation
    id_counts = {}
    missing_id_count = 0
    
    for product in data:
        if record_id_key not in product or product[record_id_key] is None:
            missing_id_count += 1
            
        product_key_value = product.get(duplicate_key) 
        if product_key_value is not None:
            id_counts[product_key_value] = id_counts.get(product_key_value, 0) + 1

    # 2. Identify duplicate DUPLICATE_KEY values (those appearing more than once)
    duplicate_keys_map = {
        key_value: count 
        for key_value, count in id_counts.items() 
        if count > 1
    }

    # 3. Use Pandas for efficient deduplication and identifying duplicates to remove
    df = pd.DataFrame(data)
    
    # Filter out rows where the DUPLICATE_KEY is null, as they can't cause conflicts
    df_non_null = df[df[duplicate_key].notna()].copy()
    df_null = df[df[duplicate_key].isna()].copy()

    # Identify which records to KEEP (the unique ones) and which to DROP (the duplicates)
    df_unique = df_non_null.drop_duplicates(
        subset=[duplicate_key],
        keep=keep_duplicate  # 'first' or 'last'
    )
    
    # Get the index of the records that were dropped/marked as duplicates
    # This is done by selecting all non-unique records and excluding the unique ones
    df_duplicates_to_drop = df_non_null[~df_non_null.index.isin(df_unique.index)]

    # Combine the cleaned unique data with any records that had a null DUPLICATE_KEY
    df_cleaned = pd.concat([df_unique, df_null], ignore_index=True)

    # Extract the IDs of the records marked for deletion (the ones to be dropped)
    # We only care about records that have a valid Supabase record ID
    duplicates_to_delete = df_duplicates_to_drop[
        df_duplicates_to_drop[record_id_key].notna()
    ][record_id_key].tolist()
    
    # Prepare the data structure for the CSV writer (list of dictionaries with the 'id' key)
    ids_for_csv = [{record_id_key: record_id} for record_id in duplicates_to_delete]
    
    # 4. Save the list of IDs of the duplicate records to a new CSV file
    num_ids_to_save = len(ids_for_csv)
    total_extra_duplicates = len(df_duplicates_to_drop)
    
    if num_ids_to_save > 0:
        fieldnames = [record_id_key]
        try:
            # with open(output_id_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            #     writer.writeheader()
            #     writer.writerows(ids_for_csv) 

            csv_save_message = (
                f"\n✅ Successfully extracted and saved {num_ids_to_save} UNIQUE record IDs "
                f"(which correspond to duplicate '{duplicate_key}' values) to '{output_id_csv_path}'. "
                f"These IDs can be used for bulk deletion in Supabase."
            )
        except Exception as e:
            csv_save_message = f"\n❌ Error saving IDs to CSV: {e}"
    else:
        csv_save_message = "\nNo IDs for deletion were found or saved."

    # 5. Save the final unique records to a new JSON file
    unique_data_list = df_cleaned.to_dict('records')
    with open(output_unique_json_path, 'w', encoding='utf-8') as f:
        json.dump(unique_data_list, f, indent=4)
        
    # --- Print Results ---
    print("-" * 40)
    print(f"Analysis of {file_path} ({total_records} records loaded)")
    print(f"Duplicate check key: '{duplicate_key}' | Keep: '{keep_duplicate}'")
    print("-" * 40)
    print(f"1. Missing '{record_id_key}' count: {missing_id_count} records")
    print(f"2. Unique Non-Null '{duplicate_key}'s: {len(df_unique)}")
    print(f"3. Duplicate '{duplicate_key}'s Found: {len(duplicate_keys_map)} unique values were duplicated.")
    print(f"   -> Total extra duplicate records (rows to remove): {total_extra_duplicates}")
    print("-" * 40)

    # 6. Print Duplicates Example (if any)
    if total_extra_duplicates > 0:
        print(f"Total UNIQUE Supabase Record IDs Extracted for Deletion: {num_ids_to_save}")
        
        # Example of a few IDs saved in the file
        print("Example of IDs saved in the CSV:")
        for item in ids_for_csv[:5]:
            print(f"  - ID: {item[record_id_key]}")
        if len(ids_for_csv) > 5:
            print("  ...")
    else:
        print(f"No duplicate '{duplicate_key}'s found among the non-null records.")

    # Print Save Statuses
    print(csv_save_message)
    print(f"\n✅ Saved {len(unique_data_list)} cleaned records to '{OUTPUT_UNIQUE_JSON_PATH}'.")
    print("-" * 40)


if __name__ == '__main__':
    # Run the analysis and cleaning process
    analyze_and_clean_data(
        file_path=INPUT_FILE,
        duplicate_key=DUPLICATE_KEY,
        record_id_key=RECORD_ID_KEY,
        output_id_csv_path=OUTPUT_ID_CSV_PATH,
        output_unique_json_path=OUTPUT_UNIQUE_JSON_PATH,
        # Change 'first' to 'last' if you want to keep the most recent duplicate!
        keep_duplicate='first'
    )
