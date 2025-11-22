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

# --- NEW: Category configuration based on your schema ---
CATEGORIES_TO_SCRAPE = [
    {
        "slug": "dresses",
        "name": "dresses",
        "main_category": "dresses",
        "role": "dresses"
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

    # --- ADVANCED STEALTH BEHAVIOR ---
    # This setting can sometimes help with network blocks
    # options.add_argument("--disable-blink-features=AutomationControlled") # uc handles this, but redundancy can help
    
    # NOTE: uc handles the User-Agent and 'webdriver' property spoofing.
    
    # Initialize the driver. The argument 'browser_executable_path' is useful 
    # if the default location is wrong, but typically not needed.
    # Force driver for Chrome 135
    driver = uc.Chrome(options=options, version_main=141)
    
    # Add a network timeout (separate from script timeout)
    driver.set_page_load_timeout(60) # Set a high limit for the page to load
    
    return driver





def scrape_product_image(driver, product_url):
    # print(f"  -> Fetching details for: {product_url}")
    MAIN_CONTENT_ID = 'main-content'
    soup = None
    image = None
    
    try:
        driver.get(product_url)
        wait = WebDriverWait(driver, 5) 

        # 1. WAIT FOR PAGE STABILITY 
        wait.until(
            EC.presence_of_element_located((By.ID, MAIN_CONTENT_ID))
        )
        # print("  -> Main content container found via Presence. Adding buffer...")
        
        time.sleep(2)
        soup_html = driver.page_source
        soup = BeautifulSoup(soup_html, "html.parser")

    except Exception as e:
        print(f"  -> ❌ ERROR during navigation/wait: {e}")
        return {} 
        
    # --- JSON PROCESSING (The core fix is here) ---
    if soup:
        try:
            

            checked_div = soup.select_one(
                'div[data-testid="color-selector-wrapper"] a[aria-checked="true"]'
            )

            

            if checked_div:
                print("TEST ✅: Found checked color option. ")

                # 2. Select the <img> tag inside the checked <div>
                # The img tag contains the image source for the color option.
                img_tag = checked_div.select_one('img')

                # 3. Extract the 'src' attribute
                image = img_tag.get('src') if img_tag else None

                # print("IMAGE URL:", image)
            else:
                print("TEST ❌: No checked color option found.")

 
   
        except Exception as e:
            print(f"  -> ❌ CRITICAL ERROR extracting schema fields: {e}")

    # # --- CRITICAL FIX 3: RETURN THE DICTIONARY ---
    return image

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
    products = []
    urls = []

    with open("h&m_catalog/ids_to_recover_image.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            urls.append(line)
    

    print("--- STEP 1: Scraping Each product pages for image only to correct previously mishandled products ---")

    driver = make_driver() 


    # --- MODIFIED LOOP STRUCTURE ---
    for i, url in enumerate(urls):
        
        product = {}
        product['url'] = url
        
        print(f"\n--- Scraping Product: {url} ---")



            
        # Call the PDP scraping function
        image = scrape_product_image(driver, url)
        product['image'] = image

        products.append(product)

        print(f"Scraped {i+1}/{len(urls)} products.")

    driver.quit()
    # --- Final Saving and Preview ---
    
    with open(f"h&m_catalog/products_recovered.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Test data successfully saved to h&m_catalog/products_recovered.json")

    # print("\n" + "="*50)
    # print("--- Final Extracted Data Preview (First Item with Details) ---")
    # print("="*50)
    
    
    print(f"\nCompleted! Total {len(products)} products processed.")
if __name__ == "__main__":
    main()