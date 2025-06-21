import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as ec

# - - - - - - - - - -

def setup_driver(url, headless=False):
    """Set up and return a configured Chrome webdriver"""
    options = Options()
    
    if headless:
        options.add_argument("--headless")  # Run in headless mode (no GUI)
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        print(f"Accessing {url}")
        
        WebDriverWait(driver, 10).until( # Wait for page to load
            ec.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print("Browser window opened, returning driver...\n")
        return driver

    except Exception as e:
        print(f"Error opening browser: {e}")
        if driver:
            driver.quit()
            print("Driver closed due to error")
        raise  # Re-raise the exception after cleanup

# - - - - - - - - - - -

class ActionHandler:

    by_methods = {
        'id': By.ID,
        'class': By.CLASS_NAME,
        'name': By.NAME,
        'xpath': By.XPATH,
        'css': By.CSS_SELECTOR,
        'tag': By.TAG_NAME
    }


    def __init__(self, driver: webdriver.Chrome, wait_time=1):
        self.driver = driver
        self.wait_time = 1

    # - - - WAIT FOR PAGE LOAD - - -

    def wait_for_page_load(self, timeout=15):
        """
        Wait for the page to fully load by checking the document ready state
        
        Args:
            timeout: How long to wait for the page to load (default: 10 seconds)
        """
        try:
            print("Waiting for page to load...")
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            print("Page loaded successfully")
        except Exception as e:
            print(f"❌ Page did not load within {timeout} seconds: {e}")

    # - - - GET ALL - - -

    def get_all_by(self, by_method, value, wait_overwrite=None, timeout=10):
        """
        Get all elements matching the given locator
        
        Args:
            by_method: By.ID, By.CLASS_NAME, By.NAME, etc. or string ('id', 'class', 'name', etc.)
            value: The value to search for
            wait_overwrite: Optional custom wait time (overrides default)
            timeout: How long to wait for the elements (default: 10 seconds)
        
        Returns:
            List of found elements
        """
        
        # Convert string method to By type if needed
        if isinstance(by_method, str) and by_method.lower() in self.by_methods:
            by_method = self.by_methods[by_method.lower()]
        
        try:
            print(f"\nLooking for elements using {by_method} = '{value}'...")
            
            wait = WebDriverWait(self.driver, timeout)
            wait.until(ec.presence_of_all_elements_located((by_method, value)))
            
            elements = self.driver.find_elements(by_method, value)
            print(f"✓ Found {len(elements)} elements")
            
            return elements
            
        except Exception as e:
            print(f"❌ Elements with {by_method} = '{value}' not found: {e}")
            return []
        
    def get_all_by_return_href(self, by_method, value, wait_overwrite=None, timeout=10):
        """
        Get all elements matching the given locator and return their href attributes
        
        Args:
            by_method: By.ID, By.CLASS_NAME, By.NAME, etc. or string ('id', 'class', 'name', etc.)
            value: The value to search for
            wait_overwrite: Optional custom wait time (overrides default)
            timeout: How long to wait for the elements (default: 10 seconds)
        
        Returns:
            List of href attributes of found elements
        """
        
        elements = self.get_all_by(by_method, value, wait_overwrite, timeout)
        return [el.get_attribute('href') for el in elements if el.get_attribute('href')]


    # - - - ACCTION HANDLING - - -

    def action_by(self, by_method, value, handling, description='Element', wait_overwrite = None, timeout=10):
        """
        Generic method to find an element and perform an action on it
        
        Args:
            by_method: By.ID, By.CLASS_NAME, By.NAME, etc. or string ('id', 'class', 'name', etc.)
            value: The value to search for
            act: Action to perform ('click' for click, 'w-...' for write followed by text)
            description: Description of the element for error messages
            timeout: How long to wait for the element (default: 10 seconds)
        """

        # Convert string method to By type if needed
        if isinstance(by_method, str) and by_method.lower() in self.by_methods:
            by_method = self.by_methods[by_method.lower()]
            
        try:
            print(f"\nLooking for '{description}' using {by_method} = '{value}'...")
            
            wait = WebDriverWait(self.driver, timeout)  # Try multiple wait conditions
            
            # First wait for element to be present
            wait.until(ec.presence_of_element_located((by_method, value)))
            print(f"✓ Element present")
            
            # Then wait for it to be visible
            wait.until(ec.visibility_of_element_located((by_method, value)))
            print(f"✓ Element visible")
            
            # Find the element
            element = self.driver.find_element(by_method, value)
            print(f"✓ Element found: {element.tag_name}")
            
            # Perform the action
            self.handler(element, handling, wait_overwrite)
            print(f"✓ Action completed on '{description}'")
            
        except Exception as e:
            print(f"❌ '{description}' with value '{value}' not found: {e}")
            
            # Additional debugging info
            try:
                print(f"🔍 Current page title: {self.driver.title}")
                print(f"🔍 Current URL: {self.driver.current_url}")
                
                # Try to find similar elements for debugging
                if by_method == By.NAME:
                    all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    print(f"🔍 Found {len(all_inputs)} input elements:")
                    for i, inp in enumerate(all_inputs[:5]):  # Show first 5
                        name_attr = inp.get_attribute("name") or "No name"
                        type_attr = inp.get_attribute("type") or "No type"
                        placeholder_attr = inp.get_attribute("placeholder") or "No placeholder"
                        print(f"   {i+1}. name='{name_attr}', type='{type_attr}', placeholder='{placeholder_attr}'")
                        
            except Exception as debug_e:
                print(f"🔍 Debug info failed: {debug_e}")
            
            # Don't continue execution, let the error bubble up
            return False
        
        return True


    def handler(self, element, action, wait_overwrite = None):
        """
        Perform an action on the given element
        
        Args:
            element: The web element to act on
            action: Action string that determines what to do with the element
                    - 'w-text': Write the text after 'w-' into the element
                    - 'click': Click on the element
        """

        try:
            if action.startswith('w-'):
                element.clear()  # For input fields, first clear any existing content
                text_to_send = action[2:]  # Then send the text
                element.send_keys(text_to_send)
                print(f"✓ Typed text into element")
                
            elif action == 'click':
                wait = WebDriverWait(self.driver, 10)  # Wait for element to be clickable
                wait.until(ec.element_to_be_clickable(element))
                element.click()
                print(f"✓ Clicked element")

            # Wait for the specified or given time after any action
            wait_time = wait_overwrite if wait_overwrite else self.wait_time
            if wait_time > 0:
                time.sleep(wait_time)
                
        except Exception as e:
            print(f"❌ Action '{action}' failed: {e}")
            raise
