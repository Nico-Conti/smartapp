import os
import time
import json
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
BASE_URL = "https://www.jomashop.com/filters/watches"
OUTPUT_DIR = "/home/nico/UNIPI/courses/smartapp-ai/watches_catalog"
MAX_PAGES = 15  # Increased limit to ensure >30 items after filtering

CATEGORIES = [
    {
        "name": "male",
        "gender_param": "Mens",
        "output_folder": "uomo",
        "price_filter": '{"from":0,"to":200}'
    },
    {
        "name": "female",
        "gender_param": "Ladies", 
        "output_folder": "donna",
        "price_filter": '{"from":0,"to":200}'
    }
]

def make_driver():
    """Configures and initializes an undetectable Chrome driver."""
    options = uc.ChromeOptions()
    # options.add_argument("--headless=new") # Debugging: see browser
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Initialize driver
    driver = uc.Chrome(options=options, version_main=143)
    driver.set_page_load_timeout(60)
    return driver

def scrape_category(driver, category):
    """Scrapes a specific category (gender)."""
    print(f"--- Scraping Category: {category['name']} ---")
    
    all_products = []
    output_path = os.path.join(OUTPUT_DIR, category['output_folder'], "watches.json")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    for page in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}?gender={category['gender_param']}&price={category['price_filter']}&p={page}"
        print(f"  -> Navigating to: {url}")
        
        try:
            driver.get(url)
            
            # Wait for products to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "productItem"))
            )
            
            # Scroll to load lazy images
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Extract products
            product_elements = driver.find_elements(By.CLASS_NAME, "productItem")
            print(f"  -> Found {len(product_elements)} products on page {page}")

            if not product_elements:
                print("  -> No products found, stopping pagination.")
                break

            current_page_products = []
            for el in product_elements:
                try:
                    title_el = el.find_element(By.CLASS_NAME, "productName")
                    title = title_el.text.strip()

                    if title:
                        title = title.replace('\n', ' ').strip()
                        brand = title.split(' ')[0]
                        # Remove brand from title
                        if title.startswith(brand):
                            title = title[len(brand):].strip()
                    else:
                        brand = "Unknown"

                    # Extract URL
                    link_el = el.find_element(By.CLASS_NAME, "productName-link")
                    product_url = link_el.get_attribute("href")
                    
                    # Extract Price
                    try:
                        price_el = el.find_element(By.CLASS_NAME, "productPrice") 
                        price = price_el.text.strip().split('\n')[0].strip()
                        
                        # Filter by price > 250
                        try:
                            price_val = float(price.replace('$', '').replace(',', ''))
                            if price_val > 250:
                                # Skip this item
                                continue
                        except:
                            pass # Keep if parsing fails
                    except:
                        price = "N/A"
                        
                    # Extract Image
                    try:
                        img_el = el.find_element(By.CSS_SELECTOR, ".productImg")
                        image_url = img_el.get_attribute("src")
                    except:
                        image_url = None

                    current_page_products.append({
                        "title": title,
                        "url": product_url,
                        "price": price,
                        "brand": brand,
                        "image_link": image_url, # Low res placeholder, updated in PDP loop
                        "audience": "male" if category['name'] == 'male' else "female",
                        "main_category": "accessories",
                        "role": "watch",
                        "schema_description": "N/A",
                        "schema_color": "Unknown"
                    })

                except Exception as e:
                    print(f"    -> Error extracting product from listing: {e}")
                    continue

            # Visit PDPs for descriptions (Limit to 5 for testing if needed, but per requirement we do all)
            # To speed up testing, we can limit here. For full run, remove slice.
            # Visit PDPs for descriptions
            for i, prod in enumerate(current_page_products):
                print(f"    -> [PDP {i+1}/{len(current_page_products)}] Scraping description: {prod['title']}")
                try:
                    driver.get(prod['url'])
                    # Wait slightly for body
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    
                    description = "N/A"
                    color = "Unknown"
                    try:
                        # Try detailed descriptions first
                        try:
                            desc_el = driver.find_element(By.CLASS_NAME, "desc-content")
                            description = desc_el.text.strip()
                        except:
                            # Fallback to meta description
                            try:
                                meta_desc = driver.find_element(By.XPATH, "//meta[@name='description']")
                                description = meta_desc.get_attribute("content")
                            except:
                                pass
                            
                        # Try to find Color in specs (Dial Color or Band Color)
                        try:
                            # Strategy 1: Find "Dial" header and look for "Dial Color" in following text
                            dial_element = driver.find_elements(By.XPATH, "//*[normalize-space(text())='Dial']")
                            if dial_element:
                                # Get text of Dial section using JS to avoid stale elements and handle text nodes
                                after_dial_text = driver.execute_script("""
                                    var dialEl = arguments[0];
                                    var text = '';
                                    var curr = dialEl.nextSibling;
                                    while(curr && !curr.textContent.includes('This website or its third-party tools use cookies')) {
                                        text += curr.textContent + ' ';
                                        curr = curr.nextSibling;
                                    }
                                    return text;
                                """, dial_element[0])
                                
                                if "Dial Color" in after_dial_text:
                                    # Extract "Dial Color Silver" -> "Silver"
                                    # Simple parsing: find "Dial Color" and take next words
                                    parts = after_dial_text.split("Dial Color")
                                    if len(parts) > 1:
                                        # Split by likely next field headers to isolate value
                                        val_part = parts[1].strip()
                                        for delimiter in ["Type", "Dial Type", "Band", "Case", "Bezel", "Function", "Movement", "Engine"]:
                                            val_part = val_part.split(delimiter)[0]
                                        
                                        potential_color = val_part.strip()
                                        if potential_color:
                                            color = potential_color.replace(':', '').strip()

                            # Strategy 2: Band Color (if Dial Color failed)
                            if color == "Unknown":
                                band_color_labels = driver.find_elements(By.XPATH, "//*[normalize-space(text())='Band Color']")
                                if band_color_labels:
                                    next_el = band_color_labels[0].find_element(By.XPATH, "following-sibling::*")
                                    color = next_el.text.strip()
                        except Exception as e:
                           print(f"      -> Error extracting color from DOM: {e}")

                        # Fallback to Title Heuristic if color is still Unknown
                        if color == "Unknown":
                            full_text_to_check = (prod['brand'] + " " + prod['title']).lower() 
                            COMMON_COLORS = ["green", "blue", "black", "white", "silver", "gold", "red", "orange", "yellow", "brown", "grey", "gray", "champagne", "beige", "pink", "purple", "turquoise", "cream", "ivory", "rose gold"]
                            for c in sorted(COMMON_COLORS, key=len, reverse=True):
                                if c in full_text_to_check:
                                    color = c.title()
                                    break
                    
                        # Extract high-quality image from og:image
                        try:
                            og_image = driver.find_element(By.XPATH, "//meta[@property='og:image']")
                            hq_image_url = og_image.get_attribute("content")
                            if hq_image_url:
                                 prod['image_link'] = hq_image_url
                                 print(f"      -> Got HQ image: {hq_image_url}")
                        except Exception as e:
                            print(f"      -> Could not extract HQ image: {e}")

                        # Validate Description - reject generic marketing blurbs
                        if description and ("shop for" in description.lower() and "jomashop" in description.lower()):
                            # If we grabbed the generic meta description, try one more time for specific elements
                            try:
                                # Sometimes desc-content isn't found by class name immediately? Try Css selector
                                desc_el = driver.find_element(By.CSS_SELECTOR, ".desc-content .show-more-text-content")
                                description = desc_el.text.strip()
                            except:
                                description = "N/A" # Better to have N/A than the generic blurb
                        
                        # Try to find Color in specs (Dial Color or Band Color)
                        # ... (existing logic) ... (we will effectively patch the cleanup below)

                        # Clean up color
                        if color and color != "Unknown":
                            color = color.title()

                        prod['schema_description'] = description
                        prod['schema_color'] = color
                        print(f"      -> Got description (len={len(description)}) and color ({color})")

                    except Exception as e:
                        print(f"      -> Error extracting details from PDP: {e}")
                
                    # Rate limiting
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e: 
                    print(f"      -> Error scraping PDP: {e}")
            all_products.extend(current_page_products)
            
            # Simple check to stop if we have enough products (though we filter later, so we grab more to be safe)
            if len(all_products) >= 40: 
                break
                
            time.sleep(random.uniform(2, 5))

        except Exception as e:
            print(f"  -> Error scraping page {page}: {e}")
            continue

    # Save to file (overwrite with new data)
    with open(output_path, 'w') as f:
        json.dump(all_products, f, indent=4)
    print(f"  -> Saved {len(all_products)} items to {output_path}")

def main():
    driver = make_driver()
    try:
        for category in CATEGORIES:
            scrape_category(driver, category)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
