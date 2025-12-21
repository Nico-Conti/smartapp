import json
import os

COMMON_COLORS = ["green", "blue", "black", "white", "silver", "gold", "red", "orange", "yellow", "brown", "grey", "gray", "champagne", "beige", "pink", "purple", "turquoise", "cream", "ivory", "rose gold"]

def process_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print(f"Processing {filepath}...")
    with open(filepath, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON in {filepath}")
            return

    processed_count = 0
    for item in data:
        # 1. Clean Title (Remove Brand)
        if 'title' in item and 'brand' in item:
            brand = item['brand']
            title = item['title']
            # Normalize for check
            if title.lower().startswith(brand.lower()):
                # Case insensitive removal
                item['title'] = title[len(brand):].strip()
        
        # 2. Fix Price (Keep only first component, remove $)
        if 'price' in item:
             p = item['price'].replace('$', '').replace(',', '')
             # If range "100 - 200", take 100
             if '-' in p:
                 p = p.split('-')[0].strip()
             try:
                 item['price'] = float(p)
             except:
                 pass # Keep as string if fail or handle? 
                 # User wanted "numeric"? The scraper filter uses float.
                 # Let's keep it consistent? Or just clean string.
                 # Scraper saves "$220.00".
                 # Let's clean to number? JSON usually prefers numbers or consistent strings.
                 # I'll leave it as scraper output for now to minimize risk, just clean formatting if needed.
                 pass

        # 3. Fill Schema Color (Heuristic)
        # Use schema_color if present, else fallback
        color_key = 'schema_color' if 'schema_color' in item else 'color'
        
        current_color = item.get(color_key, "")
        if not current_color or current_color == "Unknown":
            # Heuristic
            # Construct text to check: Brand + Title (original or current?)
            # Since we stripped brand from title, we should use brand + title
            brand = item.get('brand', "")
            title = item.get('title', "")
            full_text = (brand + " " + title).lower()
            
            found_color = "Unknown"
            for c in sorted(COMMON_COLORS, key=len, reverse=True):
                if c in full_text:
                    found_color = c.title()
                    break
            
            item[color_key] = found_color
            if found_color != "Unknown":
                processed_count += 1

    # Save back
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"  -> Processed {len(data)} items. Filled color for {processed_count}.")

def main():
    files = [
        "/home/nico/UNIPI/courses/smartapp-ai/watches_catalog/uomo/watches.json",
        "/home/nico/UNIPI/courses/smartapp-ai/watches_catalog/donna/watches.json"
    ]
    for p in files:
        process_file(p)

if __name__ == "__main__":
    main()
