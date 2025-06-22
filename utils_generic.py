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
        options.add_argument("--headless")

    # Basic browser options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Privacy and tracking settings
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")

    # Block tracking domains to not arise attention
    domains_to_block = [
        "*://*.posthog.com/*",
        "*://posthog.com/*", 
        "*://*.stripe.com/*", 
        "*://stripe.com/*",
        "*://*.analytics.com/*",
        "*://*.doubleclick.net/*",
        "*://*.googletagmanager.com/*"
    ]
    
    prefs = {
        # Content blocking settings
        'profile.default_content_settings.cookies': 1,  # Allow cookies
        'profile.block_third_party_cookies': True,      # Block third-party cookies
        'profile.cookie_controls_mode': 0,
        'profile.managed_default_content_settings.javascript': 1,
        
        # Network blocking rules
        'profile.default_content_settings.plugins': 2,  # Block plugins
        'profile.content_settings.exceptions.plugins.*': 2,
        
        # Host blocking: Block all requests to tracking domains
        'profile.default_content_settings.popups': 2,   # Block popups

        # Content settings for specific features
        'profile.managed_default_content_settings': {
            'javascript': 1,        # Allow JS generally
            'geolocation': 2,       # Block geolocation
            'notifications': 2,     # Block notifications
            'images': 1,            # Allow images
        },
    }
    
    # Add content settings
    options.add_experimental_option('prefs', prefs)
    options.add_argument("--host-resolver-rules=MAP posthog.com 127.0.0.1, MAP *.posthog.com 127.0.0.1")
    
    # Apply options to Chrome driver
    driver = webdriver.Chrome(options=options)
    
    # Add custom request interceptor after driver initialization
    driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": domains_to_block})
    driver.execute_cdp_cmd('Network.enable', {})
    
    try:
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Extract domain names from domains_to_block without wildcards and protocols
        extracted_domains = []
        for domain in domains_to_block:
            clean_domain = domain.replace('*://*.', '').replace('*://', '').replace('/*', '')
            extracted_domains.append(clean_domain)
        
        # Create a script to check each domain individually
        domains_check_script = """
            let results = {};
            const testDomains = arguments[0];
            
            for (let domain of testDomains) {
            try {
                // Try to create a test object for each domain
                const testKey = domain.split('.')[0] + 'Test';
                window[testKey] = {};
                results[domain] = typeof window[testKey] === 'object';
            } catch(e) {
                results[domain] = false;
            }
            }
            
            return results;
        """
        
        domain_results = driver.execute_script(domains_check_script, extracted_domains)
        
        # Print results for each domain
        print("\nRestricting Tracking:")
        all_blocked = True
        for domain, blocked in domain_results.items():
            status = "✅ BLOCKED" if blocked else "❌ NOT BLOCKED"
            print(f"  {status} - {domain}")
            if not blocked:
                all_blocked = False
        
        if all_blocked:
            print("\nSuccessfully restriced all tracking domains!")
        else:
            print(f"\n⚠️ Some tracking domains not blocked - you might want to check the configuration!")
            
        print("____________________________________________________________")
        return driver

    except Exception as e:
        print(f"Error opening browser: {e}")
        if driver:
            driver.quit()
        raise

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

    def element_exists(self, by_method, value, timeout, output = True):
        """
        Check if an element exists on the page
        
        Args:
            by_method: By.ID, By.CLASS_NAME, By.NAME, etc. or string ('id', 'class', 'name', etc.)
            value: The value to search for
            timeout: How long to wait for the element (default: 10 seconds)
            output: Whether to print status messages (default: False)
        
        Returns:
            True if the element exists, False otherwise
        """
        # Convert string method to By type if needed
        if isinstance(by_method, str) and by_method.lower() in self.by_methods:
            by_method = self.by_methods[by_method.lower()]
        
        try:
            if output:
                print(f"\nChecking for element using {by_method} = '{value}':")
            
            wait = WebDriverWait(self.driver, timeout)
            wait.until(ec.presence_of_element_located((by_method, value)))
            
            if output:
                print(f"✓ Element with {by_method} = '{value}' exists")
            return True
            
        except Exception as e:
            if output:
                print(f"❌ Element with {by_method} = '{value}' not found")
            return False


    def wait_for_page_load(self, timeout=15):
        """
        Wait for the page to fully load by checking multiple load indicators
        
        Args:
            timeout: How long to wait for the page to load (default: 15 seconds)
        """
        try:
            print("Waiting for page to load...")
            
            # Check document.readyState
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            print("✓ Document ready state complete")
            
            # Check that jQuery is done (if jQuery exists)
            jquery_ready = """
                return (typeof jQuery === 'undefined') || 
                       (jQuery.active === 0 && jQuery.queue && jQuery.queue().length === 0)
            """
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script(jquery_ready)
            )
            print("✓ jQuery requests complete (or jQuery not used)")
            
            # Check for any pending AJAX requests
            ajax_complete = """
                return window.performance.getEntriesByType('resource').filter(
                    r => r.initiatorType === 'xmlhttprequest' && !r.responseEnd
                ).length === 0
            """
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script(ajax_complete)
            )
            print("✓ All AJAX requests complete")
            
            print("Page fully loaded")
        except Exception as e:
            print(f"❌ Page did not fully load within timeout: {e}")


    def wait_for_by(self, by_method, value, wait_overwrite=None, timeout=10):
        """
        Wait for an element to be present and visible on the page
        
        Args:
            by_method: By.ID, By.CLASS_NAME, By.NAME, etc. or string ('id', 'class', 'name', etc.)
            value: The value to search for
            wait_overwrite: Optional custom wait time (overrides default)
            timeout: How long to wait for the element (default: 10 seconds)
        """
        
        # Convert string method to By type if needed
        if isinstance(by_method, str) and by_method.lower() in self.by_methods:
            by_method = self.by_methods[by_method.lower()]
        
        try:
            print(f"\nWaiting for element using {by_method} = '{value}':")
            
            wait = WebDriverWait(self.driver, timeout)
            wait.until(ec.presence_of_element_located((by_method, value)))
            wait.until(ec.visibility_of_element_located((by_method, value)))
            
            print(f"✓ Element with {by_method} = '{value}' is present and visible")
            
        except Exception as e:
            print(f"❌ Element with {by_method} = '{value}' not found")

    # - - - GET ALL - - -

    def get_all_by(self, by_method, value, wait_overwrite=None, timeout=10, output = True):
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
            if output:
                print(f"\nLooking for elements using {by_method} = '{value}':")
            
            wait = WebDriverWait(self.driver, timeout)
            wait.until(ec.presence_of_all_elements_located((by_method, value)))
            
            elements = self.driver.find_elements(by_method, value)
            if output:
                print(f"✓ Found {len(elements)} elements")
            
            return elements
            
        except Exception as e:
            if output:
                print(f"❌ Elements with {by_method} = '{value}' not found")
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
        return list(set([el.get_attribute('href') for el in elements if el.get_attribute('href')]))


    # - - - ACCTION HANDLING - - -

    def action_by(self, by_method, value, handling, description='Element', wait_overwrite = None, timeout=10, output = True):
        """
        Generic method to find an element and perform an action on it
        
        Args:
            by_method: By.ID, By.CLASS_NAME, By.NAME, etc. or string ('id', 'class', 'name', etc.)
            value: The value to search for
            act: Action to perform ('click' for click, 'w-...' for write followed by text)
            description: Description of the element for error messages
            timeout: How long to wait for the element (default: 10 seconds)
            output: Whether to print status messages (default: True)
        """

        # Convert string method to By type if needed
        if isinstance(by_method, str) and by_method.lower() in self.by_methods:
            by_method = self.by_methods[by_method.lower()]
            
        try:
            if output:
                print(f"\nLooking for '{description}' using {by_method} = '{value}':")
            
            wait = WebDriverWait(self.driver, timeout)  # Try multiple wait conditions
            
            # First wait for element to be present
            wait.until(ec.presence_of_element_located((by_method, value)))
            if output:
                print(f"✓ Element present")
            
            # Then wait for it to be visible
            wait.until(ec.visibility_of_element_located((by_method, value)))
            if output:
                print(f"✓ Element visible")
            
            # Find the element
            element = self.driver.find_element(by_method, value)
            if output:
                print(f"✓ Element found: {element.tag_name}")
            
            # Perform the action
            self.handler(element, handling, wait_overwrite)
            if output:
                print(f"✓ Action completed on '{description}'")
            
        except Exception as e:
            if output:
                print(f"❌ '{description}' with value '{value}' not found")
                
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
