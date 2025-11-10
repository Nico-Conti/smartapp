import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import time
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
CATEGORY_URL_SHOES_TEMPLATE = "https://www.adidas.com/us/{slug}"


# --- NEW: Category configuration based on your schema ---
CATEGORIES_TO_SCRAPE = [
    {
        "slug": "women-athletic_sneakers",
        "name": "women-athletic_sneakers",
        "main_category": "shoes",
        "role": "women-athletic_sneakers"
    }
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

    driver = uc.Chrome(options=options, version_main=141)
    
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



# --- MODIFIED: Added main_category and role parameters ---
def parse_product_grid(html: str, main_category: str, role: str):
    """Parses the HTML content to extract product details."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for article in soup.select('main[data-testid="product-grid"] article[data-testid="plp-product-card"]'):
        # Selects the specific primary image tag
        img_tag = article.select_one('img[data-testid="product-card-primary-image"]')
        image = img_tag.get('src') if img_tag else None

        # Selects the specific link tag
        link_tag = article.select_one('a[data-testid="product-card-image-link"]')
        product_link = link_tag.get('href') if link_tag else None

        # Selects the specific paragraph tag containing the title
        title_tag = article.select_one('p[data-testid="product-card-title"]')
        title = title_tag.text.strip() if title_tag else None


        # NOTE: Price is stripped of the currency symbol here to be a pure number string
        results.append({
            "title": title,
            "images": image,
            "url": product_link,
            "main_category": main_category,
            "role": role
        })

    return results

# --- MODIFIED: Added main_category and role parameters ---
def fetch_and_scroll(url, main_category, role):
    """Drives the Selenium browser to fetch and scroll the page."""
    print(f"Scraping {url}")
    driver = make_driver()
    try:
        driver.get(url)
        # time.sleep(5)
        fully_scroll(driver, pause=0.8, max_loops=16)
        soup_html = driver.page_source
        

    finally:
        driver.quit()

    # --- MODIFIED: Pass category data to parser ---
    return parse_product_grid(soup_html, main_category, role)


        



def scrape_product_detail_via_schema(driver, product_url):
    print(f"  -> Fetching details for: {product_url}")
    details_dict = {} # <-- NOTE: Renamed to avoid confusion
    SCHEMA_ID = 'product-schema'
    MAIN_CONTENT_ID = 'main-content'
    json_string = None
    
    try:
        driver.get(product_url)
        wait = WebDriverWait(driver, 5) 

        # 1. WAIT FOR PAGE STABILITY 
        wait.until(
            EC.presence_of_element_located((By.ID, MAIN_CONTENT_ID))
        )
        print("  -> Main content container found via Presence. Adding buffer...")
        # time.sleep(1.5) 

        # 2. POPUP/COOKIE BANNER HANDLING (Code omitted for brevity, assumed correct)
        try:
            cookie_accept_selector = (By.ID, "onetrust-accept-btn-handler")
            cookie_button = WebDriverWait(driver, 0.5).until(EC.element_to_be_clickable(cookie_accept_selector))
            cookie_button.click()
            print("  -> Cookie banner accepted/closed.")
            # time.sleep(1
        except Exception:
            print("  -> No cookie banner detected or could not close it. Continuing.")
            pass
  
            
        schema_element = wait.until(
            # CHANGE IS HERE: Use By.CSS_SELECTOR to find the script by its type attribute
            EC.presence_of_element_located((By.CSS_SELECTOR, 'script[type="application/ld+json"]')) 
        )

        print("  -> ✅ Product Schema script found after stabilization.")
        json_string = schema_element.get_attribute('innerHTML')

            

    except Exception as e:
        print(f"  -> ❌ ERROR during navigation/wait: {e}")
        return {} 
        
    # --- JSON PROCESSING (The core fix is here) ---
    if json_string:
        try:
            # 🐛 DEBUG: Print the raw JSON content to verify structure
            print(f"  -> 🐛 DEBUG: JSON Preview (first 500 chars): {json_string[:500]}...")
            
            # --- CRITICAL FIX 1: LOAD THE JSON STRING INTO A PYTHON DICTIONARY ---
            json_data = json.loads(json_string) 
            
            # --- CRITICAL FIX 2: POPULATE THE NEW DICTIONARY (details_dict) ---
            # details_dict['images'] = json_data.get('image')
            
            details_dict['id'] = json_data.get('sku')
            details_dict['schema_color'] = json_data.get('color')
            details_dict['schema_description'] = json_data.get('description')
            details_dict['material'] = json_data.get('material')
            details_dict['brand'] = json_data.get('brand', {}).get('name')
            details_dict['price'] = json_data.get('offers', {}).get('price')
            details_dict['audience'] = "female"

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
    all_data = []


    # --- STEP 1: Scrape Listing Pages for URLs and basic info ---
    print("--- STEP 1: Scraping Listing Pages for URLs and basic info ---")

    # --- MODIFICATION 1: Set to 5 to test 5 pages per category ---
    MAX_PAGES_PER_CATEGORY = 1

    # --- MODIFIED LOOP STRUCTURE ---
    for category_info in CATEGORIES_TO_SCRAPE:
        slug = category_info["slug"]
        cat_name = category_info["name"]
        main_cat = category_info["main_category"]
        role = category_info["role"]
        
        print(f"\n--- Scraping Category: {cat_name} ({slug}) ---")

        # Loop through the pages for this category
        for i in range(1, MAX_PAGES_PER_CATEGORY + 1): 
            print(f"  -> Loading Page {i}...")

            if main_cat in ["shoes"]:
                page_url = CATEGORY_URL_SHOES_TEMPLATE.format(slug=slug, page=i)

            # Pass the category info to the scraper
            data = fetch_and_scroll(page_url, main_cat, role) 
            
            if not data:
                print(f"  -> No data found on page {i} for {slug}. Stopping this category.")
                break 

            print(f"  -> Found {len(data)} items on page which aren't in Database{i}. Adding ALL {len(data)} items to scraping list.")
            all_data.extend(data) 
            # --------------------------------------------------
            
            # Random delay between listing pages
            # time.sleep(1 + random.random() * 3)
    # --- END OF MODIFIED LOOP ---
        
    # Now all_data will have (3 pages * 11 categories) = 33 items (if all pages/categories exist)
    print(f"\nTotal items collected for detailed scraping: {len(all_data)}")

    if not all_data:
        print("Skipping STEP 2: No product URLs collected due to block/error.")
        return 

    # --- STEP 2: Scrape Product Detail Pages (PDP) ---
    print("\n--- STEP 2: Scraping Details from Product Pages ---")
    
    driver = make_driver() 

    successful_data = []
    try:
        for i, item in enumerate(all_data):
            # if i > 1:
            #     break
            # Added print to show progress
            print(f"\nProcessing item {i+1}/{len(all_data)} (Category: {item['main_category']})")
            if not item.get('url'):
                print("  -> Skipping item, no URL found.")
                continue
            
            # Call the PDP scraping function
            details = scrape_product_detail_via_schema(driver, item['url'])
            
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

    finally:
        driver.quit()

    # --- Final Saving and Preview ---
    
    with open(f"adidas_catalog/donna/{role}.json", "w", encoding="utf-8") as f:
        json.dump(successful_data, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Test data successfully saved to adidas_catalog/uomo/{role}.json")

    # print("\n" + "="*50)
    # print("--- Final Extracted Data Preview (First Item with Details) ---")
    # print("="*50)
    
    
    print(f"\nCompleted! Total {len(all_data)} products processed.")
if __name__ == "__main__":
    main()