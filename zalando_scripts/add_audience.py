import json
import regex as re

group = 't-shirt-donna'

with open(f'zalando_scripts/{group}.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    item['audience'] = 'donna'

with open(f'zalando_scripts/{group}.json', 'w', encoding = 'utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)