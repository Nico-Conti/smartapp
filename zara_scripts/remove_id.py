import json
with open('zara_catalog/final.json', 'r', encoding='utf-8') as f:
    data  = json.load(f)

for item in data:
    del item['id']

with open('zara_catalog/final.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)