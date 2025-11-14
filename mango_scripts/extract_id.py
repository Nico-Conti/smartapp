import json

with open('mango_catalog/final.json', 'r', encoding='utf-8') as f:
    data  = json.load(f)

for entry in data:
    entry['id']