import json
import time
from urllib.parse import urljoin
import re
import os

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import random

import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)


BASE_URL = "https://www.zalando.it"
ZALANDO_URL = "https://www.zalando.it/sneakers-basse-uomo/" 

# --- Category configuration ---
CATEGORIES_TO_SCRAPE = [
    {
        "slug": "sneakers-basse-uomo",
        "url": ZALANDO_URL,
        "name": "sneakers-basse-uomo",
        "main_category": "shoes",
        "role": "sneakers-basse-uomo"
    },
]

# --- ZALANDO SELECTORS (UPDATED!) ---
# Updated selector based on the full HTML provided: targeting the unique class on the <article> tag.
PRODUCT_GRID_SELECTOR = 'article[class*="z5x6ht"]' 
PRODUCT_LINK_SELECTOR = 'a[class*="CKDt_l"]' 
SCHEMA_SELECTOR = 'script[type="application/ld+json"]'
MAIN_CONTENT_ID = 'z-pdp-main-content' 

# --- DRIVER CONFIGURATION ---
def make_driver():
    """Configures and initializes an undetectable Chrome driver with default settings."""
    
    options = uc.ChromeOptions()
    
    print("  -> Using undetected_chromedriver's default User Agent.")
    
    # options.add_argument("--headless=new") 
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3") 

    driver = uc.Chrome(options=options, version_main=135)
    driver.set_page_load_timeout(90)
    
    return driver

# --- HELPER FUNCTIONS ---

def initial_wait_for_products(driver):
    """Waits for the first product elements to load, checking for VISIBILITY."""
    try:
        # Timeout is 60s
        WebDriverWait(driver, 60).until( 
            EC.visibility_of_element_located((By.CSS_SELECTOR, PRODUCT_GRID_SELECTOR))
        )
        print("  -> Initial product grid element IS VISIBLE.")
        time.sleep(random.uniform(2, 4)) 
        return True
    except Exception:
        print("  -> ❌ CRITICAL: Initial product grid element not VISIBLE after 60s. Page is blocked or selector is incorrect.")
        return False


def zalando_scroll_and_load(driver, max_scrolls=15):
    """Scrolls down to load all products on Zalando's infinite scroll page."""
    
    print("-> Starting infinite scroll...")
    scroll_count = 0
    
    driver.execute_script("window.scrollTo(0, 100);")
    time.sleep(random.uniform(1, 2))
    
    # last_height = driver.execute_script("return document.body.scrollHeight")
    
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, 100);")
        
        scroll_time = random.uniform(1, 2) 
        time.sleep(scroll_time)
        
        # new_height = driver.execute_script("return document.body.scrollHeight")
        
        # if new_height == last_height:
        #     print(f"-> Scroll count {scroll_count}: Reached end of page or no new items loaded.")
        #     break
            
        # last_height = new_height
        scroll_count += 1
        print(f"-> Scroll count {scroll_count}/{max_scrolls} completed. New content loaded.")
    
    print("-> Infinite scroll finished.")
    return driver.page_source

def scrape_zalando_listing(html: str, main_category: str, role: str):
    """Parses Zalando's HTML to extract product details."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    
    # Use the newly corrected selector
    for article in soup.select(PRODUCT_GRID_SELECTOR):
        title_tag = article.select_one(PRODUCT_LINK_SELECTOR)
        
        # if not title_tag:
        #     continue
            
        # title = title_tag.get("title", "").strip() or title_tag.get_text(strip=True)
        
        product_link = None
        href = title_tag.get("href")
        if href:
            product_link = urljoin(BASE_URL, href.strip())

        results.append({
            # "title": title,
            "url": product_link,
            "main_category": main_category,
            "role": role
        })

    return results

def scrape_product_detail_via_schema(driver, product_url):
    """Fetches a single Zalando product page and extracts data from the JSON-LD schema."""
    print(f"  -> Fetching details for: {product_url}")
    details_dict = {} 
    json_string = None
    
    try:
        driver.get(product_url)
        wait = WebDriverWait(driver, 10) 

        # 1. WARM-UP WAIT (Buffer for PDP rendering)
        print("  -> Applying 3-second buffer for PDP rendering...")
        time.sleep(3) 

        # 2. POPUP/COOKIE BANNER HANDLING (Re-check for PDP)
        try:
            cookie_accept_selector = (By.ID, "uc-btn-accept-banner")
            cookie_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(cookie_accept_selector))
            cookie_button.click()
            print("  -> Cookie banner accepted/closed.")
            time.sleep(random.uniform(1, 2)) 
        except Exception:
            pass 

        # 3. CRITICAL WAIT: Wait ONLY for the SCHEMA SCRIPT (The actual data)
        schema_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SCHEMA_SELECTOR))
        )
        print("  -> ✅ Product Schema script found.")
        json_string = schema_element.get_attribute('innerHTML')

            
    except Exception as e:
        print(f"  -> ❌ ERROR during navigation/wait: {e}")
        return {} 
        
    # --- JSON PROCESSING ---
    if json_string:
        try:
            match = re.search(r'\{.*\}', json_string.strip(), re.DOTALL)
            if not match:
                raise ValueError("Could not extract valid JSON object from script content.")

            json_data = json.loads(match.group(0)) 

            details_dict['title'] = json_data.get('name') 

            
            # Extract fields based on the Zalando schema structure
            details_dict['images'] = json_data.get('image')
            details_dict['schema_color'] = json_data.get('color')
            details_dict['schema_description'] = json_data.get('description')
            
            details_dict['material'] = None
            details_dict['pattern'] = None  
            details_dict['audience'] = "uomo" 
            
            details_dict['brand'] = json_data.get('manufacturer')
            
            details_dict['category'] = None
            
            # Safely access price
            offers = json_data.get('offers')
            if offers and offers[0]:
                details_dict['price'] = offers[0].get('price')
                details_dict['price_currency'] = offers[0].get('priceCurrency')
            else:
                details_dict['price'] = None
                details_dict['price_currency'] = None

            print("  -> ✅ Successfully extracted ALL data from dedicated JSON-LD schema.")
                
        except json.JSONDecodeError as e:
            print(f"  -> ❌ CRITICAL ERROR: Could not decode JSON from schema tag. Error: {e}")
            
        except Exception as e:
            print(f"  -> ❌ CRITICAL ERROR extracting schema fields: {e}")

    return details_dict

MAX_PAGES = 5

# --- MAIN EXECUTION LOGIC ---
def main():
    """Orchestrates the Zalando scraping process."""
    all_data = []
    
    # --- STEP 1: Scrape Listing Pages for URLs via Infinite Scroll ---
    print("--- STEP 1: Scraping Listing Pages for URLs via Infinite Scroll ---")
    for page in range(MAX_PAGES):
        for category_info in CATEGORIES_TO_SCRAPE:
            url = category_info["url"]
            cat_name = category_info["name"]
            main_cat = category_info["main_category"]
            role = category_info["role"]
            
            print(f"\n--- Scraping Category: {cat_name} ({url}) ---")
            
            driver = make_driver()
            
            try:
                if page > 0:
                    url = f"{url}?p={page + 1}"
                print(f"  -> Loading URL: {url}")
                driver.get(url)
                
                # 1. INITIAL WARMUP
                print("  -> Applying 5-second initial wait...")
                time.sleep(5)
                
                # --- DEBUG: PRINT HTML SOURCE (Set to print 10001-15000 in last step) ---
                # print("\n--- DEBUG: PRINTING PAGE HTML SOURCE (Chars 10001 to 15000) ---")
                # print(driver.page_source[10000:15000]) 
                # print("----------------------------------------------------------\n")
                # -----------------------------------

                # # 2. Handle Cookie Banner (First priority to clear overlays)
                # try:
                #     cookie_accept_selector = (By.ID, "uc-btn-accept-banner")
                #     # Increased cookie wait slightly, in case it's delayed
                #     cookie_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable(cookie_accept_selector))
                #     cookie_button.click()
                #     print("  -> ✅ Cookie banner accepted/closed.")
                #     time.sleep(random.uniform(2, 4)) 
                # except Exception:
                #     print("  -> Cookie button not found or not clickable within 15s. Proceeding.")
                #     pass

                # # 3. AGGRESSIVE BRUTE-FORCE WAIT FOR CONTENT INJECTION
                # print("  -> 🛑 Applying 30-second aggressive wait for product content to load...")
                # time.sleep(30)
                
                # 4. WAIT FOR PRODUCTS TO APPEAR (Should now succeed with the new selector)
                if not initial_wait_for_products(driver):
                    # Now that we have the correct HTML, if this still fails, the anti-bot measures are extremely aggressive.
                    driver.quit()
                    continue

                # 5. Scroll to load all products
                soup_html = zalando_scroll_and_load(driver, max_scrolls=4)
                
                # 6. Parse the HTML
                data = scrape_zalando_listing(soup_html, main_cat, role) 
                
                if not data:
                    print(f"  -> ❌ WARNING: No product data found. Check selectors or if the page blocked you.")
                    
                print(f"  -> Found {len(data)} items for {cat_name}.")
                all_data.extend(data) 

            except Exception as e:
                print(f"  -> ❌ CRITICAL ERROR during Zalando listing scraping: {e}")
                
            finally:
                driver.quit()
                
        print(f"\nTotal items collected for detailed scraping: {len(all_data)}")

        if not all_data:
            print("Skipping STEP 2: No product URLs collected due to block/error.")
            return 
    
    print(all_data)

    # --- STEP 2: Scrape Product Detail Pages (PDP) ---
    print("\n--- STEP 2: Scraping Details from Product Pages ---")
    
    driver = make_driver() 
    successful_data = []
    
    try:
        for i, item in enumerate(all_data):
            
            print(f"\nProcessing item {i+1}/{len(all_data)}")
            if not item.get('url'):
                print("  -> Skipping item, no URL found.")
                continue
            
            details = scrape_product_detail_via_schema(driver, item['url'])
            
            if details:
                item.update(details)
                successful_data.append(item) 
            
            sleep_time = random.uniform(2,3)
            print(f"  -> Pausing for {sleep_time:.2f} seconds before next product...")
            time.sleep(sleep_time) 

    finally:
        driver.quit()

    # --- Final Saving and Preview ---
    output_file = "zalando_catalog/sneakers-basse-uomo.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(successful_data, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Final data successfully saved to {output_file}")
    print(f"\nCompleted! Total {len(successful_data)} successful products collected.")

if __name__ == "__main__":
    os.makedirs("zalando_catalog", exist_ok=True)
    main()