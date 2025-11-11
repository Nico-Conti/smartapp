import os
import sys

from sympy import li

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
CATEGORY_URL_TEMPLATE = "https://www.nike.com/w/{slug}"


# --- NEW: Category configuration based on your schema ---
CATEGORIES_TO_SCRAPE = [
    {
        "slug": "womens-running-shoes-37v7jz5e1x6zy7ok",
        "name": "womens-running-shoes-37v7jz5e1x6zy7ok",
        "main_category": "shoes",
        "role": "road-running-shoes-men"
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

def click_cookies(driver):
    """Clicks the 'Stay on Site' button if the popup appears."""
    try:
        cookies = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class="nds-btn modal-actions-accept-btn css-1snynq4 ex41m6f0 btn-primary-dark  btn-md"]'))
        )
        cookies.click()
        print("  -> Cookie banner accepted/closed.")
        time.sleep(1)  # Allow time for the banner to close
    except Exception as e:
        print(f"{e}")
        pass

# --- MODIFIED: Added main_category and role parameters ---
def parse_product_grid(html: str, main_category: str, role: str):
    """Parses the HTML content to extract product details."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for div in soup.select('div.product-grid__items > div.product-card'):

        # Selects the specific primary image tag
        img_tag = div.select_one('img.product-card__hero-image')
        image = img_tag.get('src') if img_tag else None

        # Selects the specific link tag
        link_tag = div.select_one('a[class="product-card__link-overlay"]')
        product_link = link_tag.get('href') if link_tag else None


        title = div.select_one('div[class="product-card__title"]')
        # Then select the <h3> tag inside the anchor
        # title_tag = anchor_tag.select_one('h3') if anchor_tag else None
        # Extracts the text and cleans it
        title = title.text.strip() if title else None

        results.append({
            "title": title,
            "image_link": image,
            "url": product_link,
            "main_category": main_category,
            "role": role
        })

    return results

# --- MODIFIED: Added main_category and role parameters ---
def fetch_and_scroll(driver, url, main_category, role):
    """Drives the Selenium browser to fetch and scroll the page."""
    print(f"Scraping {url}")
    # driver = make_driver()
    # try:
    driver.get(url)
    click_cookies(driver)
    # time.sleep(5)
    fully_scroll(driver, pause=0.8, max_loops=7)
    soup_html = driver.page_source
        

    # finally:
    #     driver.quit()

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


            
        schema_element = wait.until(
            # CHANGE IS HERE: Use By.CSS_SELECTOR to find the script by its type attribute
            EC.presence_of_element_located((By.CSS_SELECTOR, 'script[type="application/ld+json"]')) 
        )

        print("  -> ✅ Product Schema script found after stabilization.")
        json_string = schema_element.get_attribute('innerHTML')
        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

            

    except Exception as e:
        print(f"  -> ❌ ERROR during navigation/wait: {e}")
        return {} 
        
    # --- JSON PROCESSING (The core fix is here) ---
    if json_string:
        try:
            # 🐛 DEBUG: Print the raw JSON content to verify structure
            print(f"  -> 🐛 DEBUG: JSON Preview (first 500 chars): {json_string[:20]}...")
            
            # --- CRITICAL FIX 1: LOAD THE JSON STRING INTO A PYTHON DICTIONARY ---
            json_data = json.loads(json_string)
            json_data = json_data if isinstance(json_data, dict) else json_data[0]
            
                    # Materiale

            color = detail_soup.select_one("li[data-testid='product-description-color-description']")
            color = color.get_text(strip=True) if color else "N/A"

            id = detail_soup.select_one('li[data-testid="product-description-style-color"]')
            id = id.get_text(strip=True) if id else "N/A"
            # if not color:
            # #     # Use .contents to get a list of all children (including text nodes)
            # #     # The color text is the last item in this list
            # #     all_content = color.contents
                
            # #     # Filter out comments and whitespace, and take the last piece of text
            # #     color_description = next((item.strip() for item in reversed(all_content) if isinstance(item, str) and item.strip()), "N/A")
            # # else:
            #     color = "N/A"

            description_element = detail_soup.select_one('p[data-testid="product-description"]')

            # 2. Extract the text and clean it up
            description_text = description_element.get_text(strip=True) if description_element else "N/A"

            price =  detail_soup.select_one('span[data-testid="currentPrice-container"]')
            if price:
                price = price.get_text(strip=True).replace("$", "").replace(",", "")
            else:
                price = "N/A"

            details_dict['id'] = id
            details_dict['brand'] = "Nike"
            details_dict['schema_color'] = color
            details_dict['schema_description'] = description_text
            details_dict['material'] = ""
            details_dict['price'] = price
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
            if i > 50:
                break
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

            with open(f"nike_catalog/donna/{role}.json", "w", encoding="utf-8") as f:
                json.dump(successful_data, f, indent=4, ensure_ascii=False)
            print(f"\n✅ Test data successfully saved to nike_catalog/donna/{role}.json")

            print("\n" + "="*50)
            print("--- Final Extracted Data Preview (First Item with Details) ---")
            print("="*50)
                
            
        print(f"\nCompleted! Total {len(all_data)} products processed.")
        
    driver.quit()

    # --- Final Saving and Preview ---
    
   

if __name__ == "__main__":
    main()