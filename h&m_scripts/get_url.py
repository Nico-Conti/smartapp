import os 
import sys

import json

abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(abs_path)

# with open('zalando_scripts/zalando_catalog_cleaned_color.json', 'r', encoding='utf-8') as f:
with open('h&m_catalog/donna/purses-bags.json', 'r', encoding='utf-8') as f: 
    data = json.load(f)

check = False 

url_list = []
for item in data:
    if 'schema_color' in item:
        url_list.append(item['schema_color'])
    else:
        print(f"{item['title']} does not have schema_color")
        break

print(len(url_list))


with open('url_test.txt', 'w', encoding='utf-8') as f:
    for url in url_list:
        f.write(url + '\n')