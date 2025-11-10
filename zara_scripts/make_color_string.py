import os
import json
import re

# 1. Configuration
# Set the base directory containing the JSON files
base_dir = "zara_catalog/donna" 
# NOTE: Adjust this path if the script is run from a different location

# 2. Define the transformation function
def update_image_links(data):
    """
    Iterates over the list of items and removes 'w=177' from the 'image_link'.
    """
    count = 0
    updated_data = data
    
    for item in updated_data:
        count += 1
        
        # Check if the 'image_link' key exists and has a truthy value
        if item.get('image_link'):
            # Use re.sub to find and replace the pattern 'w=177' with an empty string
            rescale_img = re.sub(r'w=177', '', item['image_link'])
            item['image_link'] = rescale_img
        
        # NOTE: Keeping the 'else' block from your request, though 'break' might
        # stop processing the rest of the file if one image is missing.
        # If you want to continue processing the rest of the file, replace 'break' with 'continue'.
        else:
            print(f"Warning: No images found for item count {count} in the current file. ID: {item.get('id', 'N/A')}")
            # Consider changing 'break' to 'continue' to process all other items
            # continue 
            

# 3. Iterate over the directory and process files
print(f"Starting to process files in: {base_dir}")

for filename in os.listdir(base_dir):
    # Only process files that end with .json
    if filename.endswith(".json"):
        filepath = os.path.join(base_dir, filename)
        
        try:
            # Read the JSON file
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Ensure the data is a list (as suggested by the file structure and your loop)
            if isinstance(data, list):
                # Apply the transformation
                update_image_links(data)
                
                # Write the modified data back to the same file
                with open(filepath, 'w') as f:
                    # Use indent=4 for a human-readable format
                    json.dump(data, f, indent=4) 
                
                print(f"Successfully processed and updated: {filename}")
            else:
                print(f"Skipped {filename}: Content is not a list.")
                
        except json.JSONDecodeError:
            print(f"Error decoding JSON in file: {filename}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {filename}: {e}")

print("Processing complete.")