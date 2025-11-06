import json
import regex as re

group = 't-shirt-donna'

with open(f'zalando_catalog/donna/{group}.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

new_data = []

for item in data:
    for images in item['images']:
        match = re.search(r'packshot', images, re.IGNORECASE)
        if match:
            new_data.append(item)
            break

with open(f'zalando_scripts/{group}.json', 'w', encoding = 'utf-8') as f:
    json.dump(new_data, f, ensure_ascii=False, indent=4)