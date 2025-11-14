import json

with open('nike_catalog/final.json', 'r') as file:
    data = json.load(file)

count = []

for item in data:
    del item['id']

with open('nike_catalog/final.json', 'w') as file:
    json.dump(data, file, indent=4)

print(count)