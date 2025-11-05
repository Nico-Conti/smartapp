import os 
import sys

import json

abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(abs_path)

# with open('zalando_scripts/zalando_catalog_cleaned_color.json', 'r', encoding='utf-8') as f:
with open('zalando_catalog/donna/scarpe-piatte-donna.json', 'r', encoding='utf-8') as f: 
    data = json.load(f)


url_list = []
for items in data:
    url_list.append(items['title'])


print(len(url_list))


with open('url_test.txt', 'w', encoding='utf-8') as f:
    for url in url_list:
        f.write(url + '\n')