import os
import sys

from sympy import li

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import time
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# --- ADD THESE 4 LINES ---
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import random
from supabase_queries import check_if_value_exists_in_colum, setup_supabase_client




# CATEGORY_URL_SHOES_TEMPLATE = "https://www2.hm.com/en_us/men/shoes/{slug}.html?page={page}"
CATEGORY_URL_TEMPLATE = "https://www.zara.com/us/en/{slug}"


# --- NEW: Category configuration based on your schema ---
CATEGORIES_TO_SCRAPE = [
    {
        "slug": "man-shoes-sneakers-l797.html?v1=2436336",
        "name": "man-shoes-sneakers-l797.html?v1=2436336",
        "main_category": "shoes",
        "role": "sneakers"
    },
    {
        "slug": "man-shoes-boots-l781.html?v1=2436391",
        "name": "man-shoes-boots-l781.html?v1=2436391",
        "main_category": "shoes",
        "role": "boots"
    },
        {
        "slug": "man-shoes-laceup-l4378.html?v1=2436383",
        "name": "man-shoes-laceup-l4378.html?v1=2436383",
        "main_category": "shoes",
        "role": "laceup"
    },
    {
        "slug": "man-shoes-moccasins-l789.html?v1=2436392",
        "name": "man-shoes-moccasins-l789.html?v1=2436392",
        "main_category": "shoes",
        "role": "moccasins"
    },
    # {
    #     "slug": "woman-shoes-sandals-l1280.html?v1=2419172",
    #     "name": "woman-shoes-sandals-l1280.html?v1=2419172",
    #     "main_category": "shoes",
    #     "role": "sandals"
    # },
    # {
    #     "slug": "woman-trousers-high-waist-l1779.html?v1=2420787",
    #     "name": "woman-trousers-high-waist-l1779.html?v1=2420787",
    #     "main_category": "bottom",
    #     "role": "trousers-high-waist"
    # },
    # {
    #     "slug": "woman-shirts-l1217.html?v1=2420369",
    #     "name": "woman-shirts-l1217.html?v1=2420369",
    #     "main_category": "top",
    #     "role": "shirts"
    # },
    # {
    #     "slug": "woman-tshirts-short-sleeved-l1380.html?v1=2420409",
    #     "name": "woman-tshirts-short-sleeved-l1380.html?v1=2420409",
    #     "main_category": "top",
    #     "role": "tshirts"
    # },
    # {
    #     "slug": "woman-skirts-l1299.html?v1=2420454",
    #     "name": "woman-skirts-l1299.html?v1=2420454",
    #     "main_category": "bottom",
    #     "role": "skirts"
    # },
    #     {
    #     "slug": "woman-accessories-jewelry-l1015.html?v1=2418963",
    #     "name": "woman-accessories-jewelry-l1015.html?v1=2418963",
    #     "main_category": "accessories",
    #     "role": "jewelry"
    # },
    #     {
    #     "slug": "woman-accessories-headwear-l1013.html?v1=2418968",
    #     "name": "woman-accessories-headwear-l1013.html?v1=2418968",
    #     "main_category": "accessories",
    #     "role": "headwear"
    # },
    #     {
    #     "slug": "woman-beachwear-l1052.html?v1=2418962",
    #     "name": "woman-beachwear-l1052.html?v1=2418962",
    #     "main_category": "swimwear",
    #     "role": "beachwear"
    # },
    #         {
    #     "slug": "woman-bags-l1024.html?v1=2417728",
    #     "name": "woman-bags-l1024.html?v1=2417728",
    #     "main_category": "accessories",
    #     "role": "bags"
    # } 

]

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

def make_driver():
    """Configures and initializes an undetectable Chrome driver for H&M."""
    
    options = uc.ChromeOptions()
    
    # --- CRUCIAL: TEMPORARILY REMOVE HEADLESS FOR DEBUGGING ---
    # When debugging blocks, it is essential to see the browser:
    # options.add_argument("--headless=new") # COMMENT OUT THIS LINE
    options.add_argument("--window-size=1920,1080")
    
    # --- PERFORMANCE/STABILITY (Keep these) ---
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3") 

    driver = uc.Chrome(options=options, version_main=143)
    
    # Add a network timeout (separate from script timeout)
    driver.set_page_load_timeout(60) # Set a high limit for the page to load
    
    return driver


def fully_scroll(driver, pause=0, max_loops=8):
    """Scrolls down the page until no new content is loaded."""

    loops = 0
    while loops < max_loops:

        driver.execute_script("window.scrollBy(0, 850);")
        time.sleep(pause)

        loops += 1
        print(f"Loops done: {loops}/{max_loops}")

def click_to_get_to_correct_view(driver):
    """Clicks the 'Stay on Site' button if the popup appears."""
    try:
        cookies = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[id="onetrust-accept-btn-handler"]'))
        )
        cookies.click()
        print("  -> Cookie banner accepted/closed.")
        time.sleep(1)  # Allow time for the banner to close

        stay_button = WebDriverWait(driver, 100).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class="zds-button geolocation-modal__button zds-button--primary zds-button--small"]'))
        )
        stay_button.click()
        print("  -> 'Stay on Site' button clicked.")
        time.sleep(1)  # Allow time for the popup to close
        view_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-qa-action="view-option-selector-button"][aria-label="Switch to zoom 3"]'))
        )
        view_button.click()
        print("  -> 'View Site' button clicked.")
        time.sleep(1)  # Allow time for the popup to close
    except Exception as e:
        print(f"{e}")
        pass

# --- MODIFIED: Added main_category and role parameters ---
def parse_product_grid(html: str, main_category: str, role: str):
    """Parses the HTML content to extract product details."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for li in soup.select('ul.product-grid__product-list > li'):

        # Selects the specific primary image tag
        img_tag = li.select_one('img.media-image__image')
        image = img_tag.get('src') if img_tag else None

        # --- FIX: Force High Resolution Image ---
        if image:
            # Replace w=... with w=1080 to get high quality
            image = re.sub(r'w=\d+', 'w=1080', image)

        # Selects the specific link tag
        link_tag = li.select_one('a[class="product-link product-grid-product__link link"]')
        product_link = link_tag.get('href') if link_tag else None


        anchor_tag = li.select_one('a[class="product-link _item product-grid-product-info__name link"]')
        # Then select the <h3> tag inside the anchor
        title_tag = anchor_tag.select_one('h3') if anchor_tag else None
        # Extracts the text and cleans it
        title = title_tag.text.strip() if title_tag else None

        # Extract ID from image link (e.g. 12289620800 from .../12289620800-e1...)
        image_id = None
        if image:
            match = re.search(r'/(\d+)-e1', image)
            if match:
                image_id = match.group(1)

        results.append({
            "title": title,
            "image_link": image,
            "url": product_link,
            "main_category": main_category,
            "role": role,
            "image_id": image_id
        })

    return results

# --- MODIFIED: Added main_category and role parameters ---
def fetch_and_scroll(driver, url, main_category, role):
    """Drives the Selenium browser to fetch and scroll the page."""
    print(f"Scraping {url}")
    # driver = make_driver()
    # try:
    driver.get(url)
    click_to_get_to_correct_view(driver)
    # time.sleep(5)
    fully_scroll(driver, pause=0.8, max_loops=7)
    soup_html = driver.page_source
        

    # finally:
    #     driver.quit()

    # --- MODIFIED: Pass category data to parser ---
    return parse_product_grid(soup_html, main_category, role)


        



def scrape_product_detail_via_schema(driver, product_url, image_id=None):
    print(f"  -> Fetching details for: {product_url} (Image ID: {image_id})")
    details_dict = {} # <-- NOTE: Renamed to avoid confusion
    SCHEMA_ID = 'product-schema'
    MAIN_CONTENT_ID = 'main-content'
    json_string = None
    
    try:
        driver.get(product_url)
        wait = WebDriverWait(driver, 5) 

        # # 1. WAIT FOR PAGE STABILITY 
   
        # try:
        #     cookies = WebDriverWait(driver, 1).until(
        #         EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[id="onetrust-accept-btn-handler"]'))
        #     )
        #     cookies.click()
        #     print("  -> Cookie banner accepted/closed.")
        #     time.sleep(1)  # Allow time for the banner to close
        
        #     stay_button = WebDriverWait(driver, 0.5).until(
        #         EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class="zds-button geolocation-modal__button zds-button--primary zds-button--small"]'))
        #     )
        #     stay_button.click()
        #     print("  -> 'Stay on Site' button clicked.")
        # except Exception as e:
        #     print(f"  -> No popup appeared")
        #     pass

        # wait.until(
        #     EC.presence_of_element_located((By.ID, MAIN_CONTENT_ID))
        # )
        # print("  -> Main content container found via Presence. Adding buffer...")
        # # time.sleep(1.5) 

        # 2. POPUP/COOKIE BANNER HANDLING (Code omitted for brevity, assumed correct)
      
            
        schema_element = wait.until(
            # CHANGE IS HERE: Use By.CSS_SELECTOR to find the script by its type attribute
            EC.presence_of_element_located((By.CSS_SELECTOR, 'script[type="application/ld+json"]')) 
        )

        print("  -> ✅ Product Schema script found after stabilization.")
        json_string = schema_element.get_attribute('innerHTML')
        detail_soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # --- NEW: Extract viewPayload for correct Variant URL ---
        page_source = driver.page_source
        variant_product_id = None
        
        try:
            start_marker = "viewPayload ="
            start_idx = page_source.find(start_marker)
            if start_idx != -1:
                obj_start = page_source.find("{", start_idx)
                if obj_start != -1:
                    brace_count = 0
                    json_payload_str = ""
                    for i in range(obj_start, len(page_source)):
                        char = page_source[i]
                        json_payload_str += char
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                break
                    
                    payload_data = json.loads(json_payload_str)
                    colors = payload_data.get('product', {}).get('detail', {}).get('colors', [])
                    
                    if image_id:
                        color_code = image_id[-3:] if len(image_id) >= 3 else image_id
                        for c in colors:
                            if c.get('id') == color_code:
                                variant_product_id = c.get('productId')
                                print(f"  -> Found Variant ID in viewPayload: {variant_product_id} for color {color_code}")
                                break
        except Exception as vp_e:
            print(f"  -> Warning: Could not extract viewPayload for variant ID: {vp_e}")
            
    except Exception as e:
        print(f"  -> ❌ ERROR during navigation/wait: {e}")
        return {} 
        
    # --- JSON PROCESSING (The core fix is here) ---
    if json_string:
        try:
            # 🐛 DEBUG: Print the raw JSON content to verify structure
            # print(f"  -> 🐛 DEBUG: JSON Preview (first 500 chars): {json_string[:20]}...")
            
            # --- CRITICAL FIX 1: LOAD THE JSON STRING INTO A PYTHON DICTIONARY ---
            json_data = json.loads(json_string)
            
            # --- FIND CORRECT VARIANT ---
            target_data = None
            if isinstance(json_data, list):
                # Only try to match if we have an image_id
                if image_id:
                    # Extract color code (last 3 digits usually)
                    # Example: 12289620800 -> 800
                    color_code = image_id[-3:] if len(image_id) >= 3 else image_id
                    
                    print(f"  -> Looking for variant matching color code: {color_code}...")
                    
                    for item in json_data:
                        sku = item.get('sku', '')
                        # Check if color code is in SKU (e.g. -800-)
                        # SKU format is often INTERNAL_ID-COLOR-SIZE
                        if f"-{color_code}-" in sku:
                            target_data = item
                            print("  -> ✅ FOUND MATCHING VARIANT by SKU!")
                            break
                        # Fallback: check if image link contains it (less reliable if image is generic)
                        # elif color_code in item.get('image', ''):
                        #     target_data = item
                        #     break
                
                if not target_data:
                    print("  -> No specific variant matched (or no ID provided). Using first item.")
                    target_data = json_data[0]
            else:
                target_data = json_data

            
            # Materiale - Usually common for all variants but good to re-extract
            composition_div = detail_soup.find("div", class_="product-detail-composition")
            material = ""
            if composition_div:
                material= composition_div.get_text(strip=True).replace("Composition: ", "")

            details_dict['id'] = target_data.get('sku')
            details_dict['schema_color'] = target_data.get('color')
            details_dict['schema_description'] = target_data.get('description')
            details_dict['material'] = material
            details_dict['brand'] = target_data.get('brand')
            details_dict['price'] = target_data.get('offers', {}).get('price')
            details_dict['audience'] = "male"
            
            # Update URL with variant ID if found
            if variant_product_id:
                base_url = product_url.split('?')[0] # Clean existing params if any
                details_dict['url'] = f"{base_url}?v1={variant_product_id}"
                print(f"  -> ✅ Updated URL to Variant URL: {details_dict['url']}")
            else:
                details_dict['url'] = product_url # Fallback

            print(f"  -> Extracted Color: {details_dict['schema_color']}")
            print("  -> ✅ Successfully extracted ALL data from dedicated JSON-LD schema.")
                
        except json.JSONDecodeError as e:
            print(f"  -> ❌ CRITICAL ERROR: Could not decode JSON from schema tag. Error: {e}")
            
        except Exception as e:
            print(f"  -> ❌ CRITICAL ERROR extracting schema fields: {e}")

    # --- CRITICAL FIX 3: RETURN THE DICTIONARY ---
    return details_dict

def products_already_in_database(filepath):
    """Loads previously scraped product URLs from a JSON file."""

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    scraped_urls = {item['url'] for item in data if 'url' in item}
    # print(scraped_urls)
    print(f"Loaded {len(scraped_urls)} previously scraped product URLs.")
    return scraped_urls


def main():
    """Orchestrates the scraping process."""
    driver = make_driver()

    # --- STEP 1: Scrape Listing Pages for URLs and basic info ---
    print("--- STEP 1: Scraping Listing Pages for URLs and basic info ---")

    # --- MODIFICATION 1: Set to 5 to test 5 pages per category ---
    MAX_PAGES_PER_CATEGORY = 1

    # --- MODIFIED LOOP STRUCTURE ---
    for category_info in CATEGORIES_TO_SCRAPE:
        all_data = []
        
        successful_data = []

        slug = category_info["slug"]
        cat_name = category_info["name"]
        main_cat = category_info["main_category"]
        role = category_info["role"]
        
        print(f"\n--- Scraping Category: {cat_name} ({slug}) ---")

        # Loop through the pages for this category
        for i in range(1, MAX_PAGES_PER_CATEGORY + 1): 
            print(f"  -> Loading Page {i}...")

            page_url = CATEGORY_URL_TEMPLATE.format(slug=slug, page=i)

            # Pass the category info to the scraper
            data = fetch_and_scroll(driver, page_url, main_cat, role) 
            
            if not data:
                print(f"  -> No data found on page {i} for {slug}. Stopping this category.")
                break 

            # --------------------------------------------------
            
            # Random delay between listing pages
            # time.sleep(1 + random.random() * 3)
            all_data.extend(data)
        # --- END OF MODIFIED LOOP ---
            
        # Now all_data will have (3 pages * 11 categories) = 33 items (if all pages/categories exist)
        print(f"\nTotal items collected for detailed scraping: {len(all_data)}")

        if not all_data:
            print("Skipping STEP 2: No product URLs collected due to block/error.")
            return 

        # --- STEP 2: Scrape Product Detail Pages (PDP) ---
        print("\n--- STEP 2: Scraping Details from Product Pages ---")
        
    

        for i, item in enumerate(all_data):
            if i > 100:
                break
            # Added print to show progress
            print(f"\nProcessing item {i+1}/{len(all_data)} (Category: {item['main_category']})")
            if not item.get('url'):
                print("  -> Skipping item, no URL found.")
                continue
            
            # Call the PDP scraping function
            details = scrape_product_detail_via_schema(driver, item['url'], item.get('image_id'))
            
            # # Print the successfully extracted dictionary
            # print("  -> JSON DETTAGLIATO: ", details)
            if details is None:
                print("  -> Item skipped intentionally ('Pairs' item). NOT added to final list.")
                continue  # Skip this item entirely
            # Merge the new details into the existing item dictionary
            else:
                item.update(details)
                successful_data.append(item) # ONLY successful items are kept here
            
            # Random delay between products to mimic human behavior
            # time.sleep(1 + random.random() * 1.5) 

            with open(f"zara_catalog/uomo/{role}.json", "w", encoding="utf-8") as f:
                json.dump(successful_data, f, indent=4, ensure_ascii=False)
            print(f"\n✅ Test data successfully saved to zara_catalog/uomo/{role}.json")

            print("\n" + "="*50)
            print("--- Final Extracted Data Preview (First Item with Details) ---")
            print("="*50)
            
            
            print(f"\nCompleted! Total {len(all_data)} products processed.")
            
    driver.quit()

    # --- Final Saving and Preview ---
    
   

if __name__ == "__main__":
    main()