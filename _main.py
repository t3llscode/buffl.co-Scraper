from credentials.credentials import email, password
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from urllib.parse import urljoin
import platform
import requests
import time
import json
import uuid
import os

from utils_generic import ActionHandler, setup_driver
from utils_specific import click_fourth_by
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# - - - CONFIGURATION - - -

URL = "https://buffl.co"  # Replace with your target URL

# - - - - - - 

def main():
    
    driver = setup_driver(URL, headless=False)  # Set headless=False to see and interact with the browse

    handler = ActionHandler(driver, wait_time=1)

    # - - - LOGIN - - -

    handler.action_by("class", "TopNav_login__mpeOl", "click", "Login Button")

    handler.action_by("name", "email", f"w-{email}", "Email Input", wait_overwrite=0.25)
    handler.action_by("name", "password", f"w-{password}", "Password Input", wait_overwrite=0.25)

    handler.action_by("class", "login-btn", "click", "Login Submit Button")

    # - - - COURSES & CARDSETS- - -

    all_course_elements = handler.get_all_by("class", "main-nav-icon-wrapper")
    all_cardsets_href = {}

    for course_element in all_course_elements:

        course_text = course_element.text.strip()
        print(f"Processing course: {course_text}")
        all_cardsets_href[course_text] = []
            
        # Open in new tab (OS-independent)

        if platform.system() == "Darwin":  # macOS
            ActionChains(handler.driver)\
            .key_down(Keys.COMMAND)\
            .click(course_element)\
            .key_up(Keys.COMMAND)\
            .perform()
        
        else:  # Windows/Linux
            ActionChains(handler.driver)\
            .key_down(Keys.CONTROL)\
            .click(course_element)\
            .key_up(Keys.CONTROL)\
            .perform()
        
        # Switch to the new tab
        handler.driver.switch_to.window(handler.driver.window_handles[-1])
        
        handler.wait_for_page_load(timeout=1.5)

        get_cardsets = handler.get_all_by("class", "learn-btn", timeout=1.5)
        for cardset in get_cardsets:
            href = cardset.get_attribute("href")
            if href and href not in all_cardsets_href:
                all_cardsets_href[course_text].append(href)

        # Close the current tab and switch back to the main tab
        handler.driver.close()
        handler.driver.switch_to.window(handler.driver.window_handles[0])

    # - - - EXPORT CARDSETS - - -

    results = []

    print("🔍 Found the following cardsets:")
    for course, cardsets in all_cardsets_href.items():
        print(f"Course: {course}, Cardsets: {len(cardsets)}")
        for cardset in cardsets:
            print(f"  - {cardset}")

    print("\nStarting to process cardsets...")

    for course_text, cardsets in all_cardsets_href.items():
        for cardset_href in cardsets:

            # Navigate to the cardset URL in the current tab
            handler.driver.get(cardset_href)
            
            # Wait for the page to load
            handler.wait_for_page_load()
            time.sleep(2)

            handler.action_by("class", "all-courses-col", "click", "Whole Cardset Link")

            handler.wait_for_page_load()

            time.sleep(2)
            
            click_fourth_by(handler, "class", "btn-icon-icon-only", timeout=3)
            # Add a 2 second delay to ensure the dropdown menu fully appears
            time.sleep(2)

            # handler.wait_for_page_load()

            try:
                # Explicitly wait for at least one element with class "false" to appear
                
                # Wait up to 10 seconds for at least one element with class "false" to be present
                WebDriverWait(handler.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "false"))
                )
                print("Found 'false' button, continuing with processing...")
            except Exception as e:
                print(f"Timeout waiting for 'false' button: {e}")
                # Continue to the next iteration of the loop
                continue

            false_buttons = handler.get_all_by("class", "false")  # Check if there's a button with class "false"

            if false_buttons and len(false_buttons) > 0:

                try:
                    # Explicitly wait for at least one element with class "false" to appear
                    
                    # Wait up to 10 seconds for at least one element with class "false" to be present
                    WebDriverWait(handler.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "false"))
                    )
                    print("Found 'false' button, continuing with processing...")
                except Exception as e:
                    print(f"Timeout waiting for 'false' button: {e}")
                    # Continue to the next iteration of the loop
                    continue

                cards = handler.get_all_by("class", "goethe-container")  # Get all cards in the cardset

                solution_index = 0  # 0 means false solution
                for card in cards:
                    card_html = card.get_attribute('outerHTML')
                    card_text = card.text.strip()
                    # Create the directory if it doesn't exist
                    os.makedirs('results/media', exist_ok=True)
                    # Find all img elements in the card
                    card_imgs = card.find_elements(By.TAG_NAME, 'img')
                    img_paths = []

                    for img in card_imgs:
                        src = img.get_attribute('src')
                        if src:
                            # Generate a UUID for the filename
                            img_uuid = str(uuid.uuid4())
                            img_path = f"results/media/{img_uuid}.png"
                            
                            # Download the image using the driver
                            try:
                                # Handle relative URLs
                                if not src.startswith(('http://', 'https://')):
                                    src = urljoin(handler.driver.current_url, src)
                                
                                # Open a new tab to download the image
                                original_window = handler.driver.current_window_handle
                                handler.driver.execute_script("window.open('');")
                                handler.driver.switch_to.window(handler.driver.window_handles[-1])
                                handler.driver.get(src)
                                # Get image as screenshot
                                img_element = handler.driver.find_element(By.TAG_NAME, 'img')
                                img_element.screenshot(img_path)
                                
                                # Close tab and return to original tab
                                handler.driver.close()
                                handler.driver.switch_to.window(original_window)
                                
                                img_paths.append(img_path)
                                # Replace the src in the HTML with the local path
                                card_html = card_html.replace(f'src="{src}"', f'src="{img_path}"')
                                print(f"Downloaded image: {img_path}")
                            except Exception as e:
                                print(f"Failed to download image from {src}: {e}")
                                # Continue with next image if there's an error

                    print(f"Processing card: {card_text[:50]}...")  # Print first 50 chars as preview
                    results.append({
                        'uuid': str(uuid.uuid4()),
                        'course': course_text,
                        'cardset': cardset_href,
                        'text': card_text,
                        'html': card_html,
                        'img': img_paths,
                        'solution': solution_index
                    })
                    solution_index += 1
                
                handler.action_by("class", "false", "click", "False Button")  # Click the first button with class "false"

            else:

                # No button with class "false", continue with the next cardset
                print(f"No 'false' class button found for cardset: {cardset_href}, assuming no more data to process.")
                continue

            # Optional: Add a small delay between processing different cardsets
            handler.driver.implicitly_wait(2)
    
    # - - - SAVE RESULTS - - -

    with open("cardsets_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    # - - - END - - -

    input("If you hit 'Enter', the browser will close and the script will exit.")

    driver.quit()

# - - - - - -

if __name__ == "__main__":
    main()