import os 
import sys

import json

abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(abs_path)

# with open('zalando_scripts/zalando_catalog_cleaned_color.json', 'r', encoding='utf-8') as f:
with open('h&m_catalog/donna/shirts-blouses.json', 'r', encoding='utf-8') as f: 
    data = json.load(f)

check = False 

url_list = []
for item in data:
    for keys in item:
        if keys == 'audience':
            # url_list.append(item['audience'])
            check = True
        
    if not check:
        print(item['url'])

    check = False

    url_list.append(item['url'])

print(len(url_list))


with open('url_test.txt', 'w', encoding='utf-8') as f:
    for url in url_list:
        f.write(url + '\n')