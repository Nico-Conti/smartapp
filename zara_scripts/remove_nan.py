import os 
import sys
import json
import math # Needed to correctly check for float('nan')
from typing import List, Dict, Any

# Setup is correct for resolving paths
abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(abs_path)

# --- CONFIGURATION ---
INPUT_FILE = 'zara_catalog/final.json'
# Define the critical fields that MUST have a valid value
CRITICAL_FIELDS = ['id', 'material', 'brand', 'price', 'audience']

# --- Helper Function for Robust Missing Value Check ---
def is_missing_or_invalid(value: Any) -> bool:
    """
    Checks if a value is None, an empty string, or a float NaN.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False

# --- Main Script Execution ---

try:
    with open(INPUT_FILE, 'r', encoding='utf-8') as f: 
        data: List[Dict[str, Any]] = json.load(f)
except Exception as e:
    print(f"❌ Error loading data: {e}")
    sys.exit(1)

initial_count = len(data)
final_cleaned: List[Dict[str, Any]] = []
removed_count = 0

print(f"🔍 Starting multi-field filtering on {initial_count} records...")

for item in data:
    item_is_valid = True
    missing_fields = []
    
    # Check each critical field
    for field in CRITICAL_FIELDS:
        # 1. Check if the key is missing entirely
        if field not in item:
            item_is_valid = False
            missing_fields.append(f"MISSING_KEY: {field}")
            continue
            
        # 2. Check the value using the helper function
        if is_missing_or_invalid(item[field]):
            item_is_valid = False
            missing_fields.append(f"{field}='{item[field]}'")

    # --- Final Logic ---
    if item_is_valid:
        final_cleaned.append(item)
    else:
        removed_count += 1
        title = item.get('title', 'Unknown Title')
        # Join the list of missing fields for a clear log message
        print(f"Removed item '{title}' due to invalid/missing fields: [{', '.join(missing_fields)}]")
   
# --- Summary and Save ---
print("\n--- Cleaning Summary ---")
print(f"Initial total records: {initial_count}")
print(f"Records kept (all critical fields valid): {len(final_cleaned)}")
print(f"Records removed (incomplete data): **{removed_count}**")

# Save the final cleaned list
try:
    with open(INPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_cleaned, f, indent=4)
    print(f"✅ Successfully saved {len(final_cleaned)} cleaned records back to **{INPUT_FILE}**")
except Exception as e:
    print(f"❌ Error saving output file: {e}")