import json

path = 'adidas_catalog/final.json'

with open(path, 'r') as file:
    data = json.load(file)

count = []

for item in data:
    item['id'] = 1


with open(path, 'w') as file:
    json.dump(data, file, indent=4)

print(count)