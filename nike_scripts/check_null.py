import json

with open('nike_catalog/final.json', 'r') as file:
    data = json.load(file)

count = []

for item in data:
    if item['price']:
        count.append(item['url'])

print(f'Total items with null price: {len(count)}')

print(count)