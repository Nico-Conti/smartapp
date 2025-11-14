import json

with open('zara_catalog/final.json', 'r') as file:
    data = json.load(file)

count = []

for i, item in enumerate(data):
    count.append(item)

    if len(count) >= 250:
        with open(f'final_{i}.json', 'w') as outfile:
            json.dump(count, outfile, indent=4)
        count = []

with open(f'zara_catalog/final_last.json', 'w') as outfile:
        json.dump(count, outfile, indent=4)