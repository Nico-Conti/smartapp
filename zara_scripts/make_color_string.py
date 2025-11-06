import json
import regex as re

group = 'products-donna'

with open(f'zara_catalog/donna/{group}.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

color = ""
for i,item in enumerate(data):
    if i == 2:
        break

    for item_color in item['schema_color']:
        color += item_color + ", "
        print(color)

    item['schema_color'] = color

    color = ""
# with open(f'zara_scripts/{group}.json', 'w', encoding = 'utf-8') as f:
#     json.dump(data, f, ensure_ascii=False, indent=4)