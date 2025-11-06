import json

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import supabase_queries as supa

with open('zalando_scripts/felpe-donna.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

supabase_client = supa.setup_supabase_client()

# db_ids = supa.load_table(supabase_client, 'product_data')

for item in data:
    id_value = item['id']
    exists = supa.check_if_value_exists_in_colum(supabase_client, 'product_data', id_value, 'id')
    if  exists:
        # print(f"ID {id_value} not found in database.")
    # else:
        print(f"ID {id_value} already exists in database.")