
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def make_driver():
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=options, version_main=143)
    return driver

def test_refinements():
    driver = make_driver()
    try:
        # Test item that previously had "Shop for..." description
        url = "https://www.jomashop.com/timex-waterbury-traditional-quartz-white-dial-ladies-watch-tw2r69400.html"
        print(f"Navigating to {url}")
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5) # Let it load
        
        description = "N/A"
        
        # Emulate scraper logic
        try:
            # 1. Try primary selector
            try:
                desc_el = driver.find_element(By.CLASS_NAME, "desc-content")
                description = desc_el.text.strip()
            except:
                # Fallback to meta
                try:
                    meta_desc = driver.find_element(By.XPATH, "//meta[@name='description']")
                    description = meta_desc.get_attribute("content")
                except:
                    pass
            
            print(f"Initial Description: {description[:50]}...")

            # 2. Apply Filter
            if description and ("shop for" in description.lower() and "jomashop" in description.lower()):
                print("Detected generic description. Retrying specific selector...")
                try:
                    desc_el = driver.find_element(By.CSS_SELECTOR, ".desc-content .show-more-text-content")
                    description = desc_el.text.strip()
                    print("Recovered detailed description!")
                except:
                    description = "N/A"
                    print("Could not recover description. Set to N/A.")

        except Exception as e:
            print(f"Error: {e}")
            
        print("-" * 20)
        print(f"Final Description: {description}")
        print("-" * 20)
        
        # Test Color Logic
        # ... (Include the robust color logic I verified earlier, plus Title Case)
        # For brevity, testing if Title Case works on a dummy string here or extracting real color
        # Let's just try to extract the real color using the robust logic and print it title cased
        
        # ... copy-paste robust logic ...
        color = "Unknown"
        try:
             dial_element = driver.find_elements(By.XPATH, "//*[normalize-space(text())='Dial']")
             if dial_element:
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
                     parts = after_dial_text.split("Dial Color")
                     if len(parts) > 1:
                         val_part = parts[1].strip()
                         for delimiter in ["Type", "Dial Type", "Band", "Case", "Bezel", "Function", "Movement", "Engine"]:
                             val_part = val_part.split(delimiter)[0]
                         potential_color = val_part.strip()
                         if potential_color:
                             color = potential_color.replace(':', '').strip()
        except:
            pass
            
        if color != "Unknown":
            color = color.title()
            
        print(f"Final Color: {color}")
        
        if "Shop for" not in description and description != "N/A" and color == "White":
            print("TEST PASSED")
        else:
            print("TEST FAILED")

    finally:
        driver.quit()

if __name__ == "__main__":
    test_refinements()
