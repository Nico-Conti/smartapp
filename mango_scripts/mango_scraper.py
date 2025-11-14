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
CATEGORY_URL_TEMPLATE = "https://shop.mango.com/us/en/c/{slug}"


# --- NEW: Category configuration based on your schema ---
CATEGORIES_TO_SCRAPE = [
    {
        "slug": "women/blazers/fitted_51f3df1a",
        "name": "women/blazers/fitted_51f3df1a",
        "main_category": "outerwear",
        "role": "blazers-donna"
    },
    {
        "slug": "women/dresses-and-jumpsuits/wedding-guest_d66b6a79",
        "name": "women/dresses-and-jumpsuits/wedding-guest_d66b6a79",
        "main_category": "dresses",
        "role": "wedding-dresses-donna"
    },
        {
        "slug": "women/dresses-and-jumpsuits/casual_fe0040cc",
        "name": "women/dresses-and-jumpsuits/casual_fe0040cc",
        "main_category": "dresses",
        "role": "dresses-donna"
    },
    {
        "slug": "women/dresses-and-jumpsuits/floral_97b9994b",
        "name": "women/dresses-and-jumpsuits/floral_97b9994b",
        "main_category": "dresses",
        "role": "floral-dresses-donna"
    },
        {
        "slug": "women/jackets_5ef3ad3b",
        "name": "women/jackets_5ef3ad3b",
        "main_category": "outerwear",
        "role": "jackets-donna"
    },
    {
        "slug": "women/jeans_164d8c42",
        "name": "women/jeans_164d8c42",
        "main_category": "bottom",
        "role": "jeans-donna"
    },
    {
        "slug": "women/pants/straight_47e592a3",
        "name": "women/pants/straight_47e592a3",
        "main_category": "bottom",
        "role": "pants-donna"
    },
    {
        "slug": "women/t-shirts_8e23bdfb",
        "name": "women/t-shirts_8e23bdfb",
        "main_category": "top",
        "role": "t-shirts-donna"
    },
        {
        "slug": "women/trench-coats-and-parkas/trench-coats_6b240267",
        "name": "women/trench-coats-and-parkas/trench-coats_6b240267",
        "main_category": "outerwear",
        "role": "trench-coats-donna"
    },
    {
        "slug": "women/skirts/short_3a5e9b8a",
        "name": "women/skirts/short_3a5e9b8a",
        "main_category": "bottom",
        "role": "skirts-donna"
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
        cookies = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class="ButtonBase_button__SOIgU textActionM_className__8McJk ButtonPrimary_default__2Mbr8 CookiesFooter_button__l_Uzv"]'))
        )
        cookies.click()
        print("  -> Cookie banner accepted/closed.")
        time.sleep(1)  # Allow time for the banner to close

        accept_country = WebDriverWait(driver, 55).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class="ButtonBase_button__SOIgU textActionM_className__8McJk ButtonBase_fullWidth__g0ppN ButtonPrimary_default__2Mbr8"]'))
        )
        accept_country.click()
        print("  -> Country selector accepted/closed.")
    except Exception as e:
        print(f"{e}")
        pass

# --- MODIFIED: Added main_category and role parameters ---
def parse_product_grid(html: str, main_category: str, role: str):
    """Parses the HTML content to extract product details."""
    soup = BeautifulSoup(html, "html.parser")
    results = []



    for div in soup.select('div.virtual-list div.virtual-item'):

        print(div)

        # Selects the specific primary image tag
        # img_tag = div.select_one('img.product-card__hero-image')
        # image = img_tag.get('src') if img_tag else None

        # Selects the specific link tag
        link_tag = div.select_one('a[class="ProductImage_imageWrapper__JfhWa"]')
        product_link = link_tag.get('href') if link_tag else None


        # title = div.select_one('div[class="product-card__title"]')
        # Then select the <h3> tag inside the anchor
        # title_tag = anchor_tag.select_one('h3') if anchor_tag else None
        # Extracts the text and cleans it
        # title = title.text.strip() if title else None

        results.append({
            # "title": title,
            # "image_link": image,
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

    # sensible defaults
    details = {
        "title": "N/A",
        "brand": "Mango",
        "schema_color": "N/A",
        "schema_description": "N/A",
        "material": "N/A",
        "price": "N/A",
        "audience": "female",
    }

    try:
        driver.get(product_url)
        wait = WebDriverWait(driver, 10)

        # wait until the main product title is present
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "h1.ProductDetail_title__Go9C2")
            )
        )

        # --- open the "See details" / composition sheet (if it exists) ---
        try:
            details_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.ProductDetailsLink_link__mAQy0")
                )
            )
            driver.execute_script("arguments[0].click();", details_btn)

            # wait for the composition list to appear inside the dialog
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-dialog-container='true'] ul.Composition_list__JsVcC")
                )
            )
        except Exception:
            # If there is no button or composition tab for this item, just carry on
            print("  -> ℹ️ No 'See details' button or composition list found.")

        # now grab the **updated** DOM
        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

    except Exception as e:
        print(f"  -> ❌ ERROR during navigation/wait: {e}")
        return details

    # ---------- TITLE ----------
    node = detail_soup.select_one("h1.ProductDetail_title__Go9C2")
    if node:
        details["title"] = node.get_text(strip=True)

    # ---------- DESCRIPTION ----------
    node = detail_soup.select_one("p.Description_descriptionContent__pCRwU")
    if node:
        details["schema_description"] = node.get_text(strip=True)

    # ---------- PRICE ----------
    node = detail_soup.select_one("span.SinglePrice_center__SWK1D")
    if node:
        price_text = node.get_text(strip=True)
        # clean currency formatting a bit
        for cur in ("US$", "€", "£"):
            price_text = price_text.replace(cur, "")
        price_text = price_text.replace(",", "").strip()
        details["price"] = price_text

    # ---------- COLOUR ----------
    selected_span = detail_soup.select_one("span.ColorSelectorPicker_selected__ek_DA")
    if selected_span:
        img = selected_span.find("img")
        if img and img.has_attr("alt"):
            alt_text = img["alt"]  # e.g. "Color Ecru selected"
            colour = alt_text
            if colour.lower().startswith("color "):
                colour = colour[6:]
            if colour.lower().endswith(" selected"):
                colour = colour[:-9]
            details["schema_color"] = colour.strip()

    # ---------- COMPOSITION / MATERIAL ----------
    comp_items = [
        li.get_text(strip=True)
        for li in detail_soup.select("ul.Composition_list__JsVcC > li")
    ]
    if comp_items:
        details["material"] = ", ".join(comp_items)


    # ---------- IMAGE LINKS ----------
    image_links = []
    
    # The image is inside a div with class 'CustomCursor_container__FcbV8' 
    # and has the 'srcset' attribute with all the different image URLs.
    # The image is likely loaded after a click/wait, so we use detail_soup.
    for img in detail_soup.select('div[class="CustomCursor_container__EeBvB"] img'):
        src = img.get("src")
        if src:
            for part in src.split(','):
                url = part.strip().split(' ')[0] # Get the URL part
                if url.startswith("http"):
                    image_links.append(url)
    final_img = image_links[-2] if image_links else None
    # Assign the list of links to the details dictionary
    details["image_link"] = final_img



    print("  -> ✅ Successfully extracted product details.")

    
    return details

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
            if i > 80:
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

            with open(f"mango_catalog/donna/{role}.json", "w", encoding="utf-8") as f:
                json.dump(successful_data, f, indent=4, ensure_ascii=False)
            print(f"\n✅ Test data successfully saved to mango_catalog/donna/{role}.json")

            print("\n" + "="*50)
            print("--- Final Extracted Data Preview (First Item with Details) ---")
            print("="*50)
                
            
        print(f"\nCompleted! Total {len(all_data)} products processed.")
        
    driver.quit()

    # --- Final Saving and Preview ---
    
   

if __name__ == "__main__":
    main()