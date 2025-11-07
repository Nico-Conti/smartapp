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



BASE_URL = "https://www2.hm.com"

# --- REMOVED OLD LISTING_URL ---

# --- NEW: URL Template for all categories ---
# CATEGORY_URL_ABBILIGIMENTO_TEMPLATE = "https://www2.hm.com/it_it/uomo/acquista-per-prodotto/{slug}.html?page={page}"
CATEGORY_URL_ABBILIGIMENTO_TEMPLATE = "https://www2.hm.com/en_us/women/products/{slug}.html?page={page}"


# CATEGORY_URL_SHOES_TEMPLATE = "https://www2.hm.com/en_us/men/shoes/{slug}.html?page={page}"
CATEGORY_URL_SHOES_TEMPLATE = "https://www2.hm.com/en_us/women/shoes/{slug}.html?page={page}"

CATEGORY_URL_ACCESORIES_TEMPLATE = "https://www2.hm.com/en_us/women/accessories/{slug}.html?page={page}"


# --- NEW: Category configuration based on your schema ---
CATEGORIES_TO_SCRAPE = [
    # {
    #     "slug": "hats",
    #     "name": "hats",
    #     "main_category": "accessories",
    #     "role": "hats"
    # },
    # {
    #     "slug": "hoodies-sweatshirts",
    #     "name": "hoodies-sweatshirts",
    #     "main_category": "top",
    #     "role": "hoodies-sweatshirts"
    # },
    # {
    #     "slug": "cardigans-sweaters",
    #     "name": "cardigans-sweaters",
    #     "main_category": "top",
    #     "role": "cardigans-sweaters"
    # },
    # {
    #     "slug": "skirts",
    #     "name": "skirts",
    #     "main_category": "bottom",
    #     "role": "skirts"
    # },
    # {
    #     "slug": "jackets-coats",
    #     "name": "jackets-coats",
    #     "main_category": "outerwear",
    #     "role": "jackets-coats"
    # },
    {
        "slug": "pants",
        "name": "pants",
        "main_category": "bottom",
        "role": "pants"
    },
    # {
    #     "slug": "tops",
    #     "name": "tops",
    #     "main_category": "top",
    #     "role": "tops"
    # },
    # {
    #     "slug": "shirts",
    #     "name": "shirts",
    #     "main_category": "top",
    #     "role": "shirts"
    # },

    # {
    #     "slug": "polos",
    #     "name": "polos",
    #     "main_category": "top",
    #     "role": "polos"
    # },
    # {
    #     "slug": "shorts",
    #     "name": "shorts",
    #     "main_category": "bottom",
    #     "role": "shorts"
    # },
    # #SCARPE E CIABATTE
    # {
    #     "slug": "sneakers",
    #     "name": "sneakers",
    #     "main_category": "shoes",
    #     "role": "sneakers"
    # },
    # {   
    #     "slug": "heels",
    #     "name": "heels",
    #     "main_category": "shoes",
    #     "role": "heels"

    # },
    # {   
    #     "slug": "dress-shoes",
    #     "name": "dress-shoes",
    #     "main_category": "shoes",
    #     "role": "dress-shoes"
    # },
    # {   
    #     "slug": "boots",
    #     "name": "boots",
    #     "main_category": "shoes",
    #     "role": "boots"
    # },
    # {   
    #     "slug": "sandals",
    #     "name": "sandals",
    #     "main_category": "shoes",
    #     "role": "sandals"
    # },

    # {   
    #     "slug": "hats-caps",
    #     "name": "hats-caps",
    #     "main_category": "accesories",
    #     "role": "hats-caps"
    # },
    # {   
    #     "slug": "jewelry",
    #     "name": "jewelry",
    #     "main_category": "accesories",
    #     "role": "jewelry"
    # },

    # {   
    #     "slug": "sunglasses",
    #     "name": "sunglasses",
    #     "main_category": "accesories",
    #     "role": "sunglasses"
    # },

    # {
    #     "slug": "blazers",
    #     "name": "blazers",
    #     "main_category": "outerwear",
    #     "role": "blazers"
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


def fully_scroll(driver, pause=0, max_loops=8):
    """Scrolls down the page until no new content is loaded."""

    loops = 0
    while loops < max_loops:

        driver.execute_script("window.scrollBy(0, 850);")
        time.sleep(pause)

        loops += 1
        print(f"Loops done: {loops}/{max_loops}")

def pick_image_urls(img_tag):
    """Extracts and normalizes image URLs from common image attributes."""
    urls = []

    def normalize(u: str):
        if not u:
            return None
        u = u.strip()
        if not u:
            return None
        if u.startswith("http://") or u.startswith("https://"):
            return u
        # H&M specific normalization
        return urljoin("https://image.hm.com/", u.lstrip("/"))

    # data-src
    ds = img_tag.get("data-src")
    if ds:
        u = normalize(ds)
        if u:
            urls.append(u)

    # srcset / data-srcset (first candidate)
    srcset = img_tag.get("data-srcset") or img_tag.get("srcset")
    if srcset:
        first = srcset.split(",")[0].strip().split(" ")[0]
        u = normalize(first)
        if u and u not in urls:
            urls.append(u)

    # src (fallback)
    src = img_tag.get("src")
    if src:
        u = normalize(src)
        if u and u not in urls:
            urls.append(u)

    return urls

# --- MODIFIED: Added main_category and role parameters ---
def scrape_listing_page(html: str, main_category: str, role: str, supabase_client):
    """Parses the HTML content to extract product details."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for li in soup.select('ul[data-elid="product-grid"] li'):
        img_tag = li.select_one("img")
        title_tag = li.select_one("h2")
        link_tag = li.select_one("a")




        if not title_tag:
            continue


        title = title_tag.get_text(strip=True) if title_tag else None

        images = pick_image_urls(img_tag)

        # product URL
        product_link = None
        if link_tag and link_tag.get("href"):
            href = link_tag["href"].strip()
            product_link = urljoin(BASE_URL, href)

        if check_if_value_exists_in_colum(supabase_client, "product_data", "url", product_link):
            # print(f"  -> Skipping already in DB URL: {product_link}")
            continue


        # NOTE: Price is stripped of the currency symbol here to be a pure number string
        results.append({
            "title": title,
            # "price": price.replace("$", "").strip() if price else None,
            "images": images,
            "url": product_link,
            # --- NEW: Added category data ---
            "main_category": main_category,
            "role": role
        })

    return results

# --- MODIFIED: Added main_category and role parameters ---
def scrap_images_titles_links(url, main_category, role, supabase_client):
    """Drives the Selenium browser to fetch and scroll the page."""
    print(f"Scraping {url}")
    driver = make_driver()
    try:
        driver.get(url)
        # time.sleep(5)
        fully_scroll(driver, pause=0.8, max_loops=8)
        soup_html = driver.page_source
        

    finally:
        driver.quit()

    # --- MODIFIED: Pass category data to parser ---
    return scrape_listing_page(soup_html, main_category, role, supabase_client)


def click_desc_button(driver):

    BUTTON_SELECTOR = (By.ID, "toggle-descriptionAccordion")
    
   

    # # # 2. Wait until the button is clickable
    wait = WebDriverWait(driver, 5)
    
    button = wait.until(
        EC.element_to_be_clickable(BUTTON_SELECTOR)
    )
    
    try:
        # 1. Wait for and find the clickable element
        button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(BUTTON_SELECTOR)
        )
        
        # 2. Click it
        button.click()
        
        # 3. Add a short delay and return success
        # time.sleep(1)
        return True 
        
    except Exception:
        return False

def check_if_2_pairs(driver):

    if click_desc_button(driver):

        # Correction of your XPath:
        DT_SELECTOR = (By.XPATH, 
                    '//dl[starts-with(@class, "ad91df")]/div[starts-with(@class, "cd043b")]/dt[contains(text(), "Pieces")]')
        
        print("-> Searching for <dt> tag containing 'Pieces' or 'Pairs'...")
        
        
        try:
            # 1. Wait for and locate the specific <dt> element
            wait_dt = WebDriverWait(driver, 0.5)
            dt_element = wait_dt.until(
                EC.presence_of_element_located(DT_SELECTOR)
            )
            
            # 2. Extract the text content from the <dt> (the term itself)
            pairs_term = dt_element.text.strip()
            
            # 3. Use the sibling (<dd>) of the parent <div> to get the value
            # This XPath finds the <dd> element that is a sibling of the <dt>'s parent (the <div>)
            # This is speculative and might require adjustment based on the exact <dd> location.
            try:
                # A more common structure: Find the next sibling of the <dt>
                # If the structure is <dt>... </dt> <dd>...</dd> inside the div:
                dd_element = dt_element.find_element(By.XPATH, './following-sibling::dd')
                pairs_value = dd_element.text.strip()
                full_data = f"{pairs_term}: {pairs_value}"
            except:
                # If no <dd> is found, just use the <dt> text
                full_data = pairs_term

            return True
            
        except Exception as e:

            return False

    return False
   

        



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
            # time.sleep(1) 
        except Exception:
            print("  -> No cookie banner detected or could not close it. Continuing.")
            pass

        if  check_if_2_pairs(driver):
            return None
  
            
        # 3. WAIT FOR THE SPECIFIC SCHEMA SCRIPT 
        schema_element = wait.until(
            EC.presence_of_element_located((By.ID, SCHEMA_ID))
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
            details_dict['schema_color'] = json_data.get('color')
            details_dict['schema_description'] = json_data.get('description')
            details_dict['material'] = json_data.get('material')
            details_dict['pattern'] = json_data.get('pattern')
            details_dict['brand'] = json_data.get('brand', {}).get('name')
            details_dict['category'] = json_data.get('category', {}).get('name')
            details_dict['price'] = json_data.get('offers')[0].get('price')
            details_dict['audience'] = json_data.get('audience').get('suggestedGender')

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

    supabase_client = setup_supabase_client()
    
    # --- STEP 1: Scrape Listing Pages for URLs and basic info ---
    print("--- STEP 1: Scraping Listing Pages for URLs and basic info ---")

    # --- MODIFICATION 1: Set to 5 to test 5 pages per category ---
    MAX_PAGES_PER_CATEGORY = 5

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
            elif main_cat in ["accessories"]:
                if i == 1:
                    page_url = CATEGORY_URL_ACCESORIES_TEMPLATE.format(slug=slug, page="")
                else:
                    page_url = CATEGORY_URL_ACCESORIES_TEMPLATE.format(slug=slug, page=i)
            else:
                page_url = CATEGORY_URL_ABBILIGIMENTO_TEMPLATE.format(slug=slug, page=i)


            # Pass the category info to the scraper
            data = scrap_images_titles_links(page_url, main_cat, role, supabase_client) 
            
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
    
    with open(f"h&m_catalog/donna/{role}.json", "w", encoding="utf-8") as f:
        json.dump(successful_data, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Test data successfully saved to h&m_catalog/donna/{role}.json")

    # print("\n" + "="*50)
    # print("--- Final Extracted Data Preview (First Item with Details) ---")
    # print("="*50)
    
    
    print(f"\nCompleted! Total {len(all_data)} products processed.")
if __name__ == "__main__":
    main()