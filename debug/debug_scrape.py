from selenium import webdriver
from bs4 import BeautifulSoup
import time

from utils_generic import setup_driver

# - - - - - - - - -

URL = "https://buffl.co"  # Replace with your target URL

# - - - - - - - - - -

def main():
    driver = setup_driver(URL, headless=False)  # Set headless=False to see and interact with the browser

    continue_scraping = True

    while continue_scraping:
        continue_scraping = scrape_and_save_website(driver)

# - - - - - - - - -

def scrape_and_save_website(driver: webdriver.Chrome) -> bool:
    
    input("Interact with the page as needed, when you're ready press 'Enter' to save it to the files.")
        
    # Ask user for filename
    filename_input = input("Enter a filename for the page (without extension): ")

    datetime_str = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{datetime_str} {filename_input}.html" if filename_input else "{datetime_str}.html"
    
    # Get the page source (HTML)
    html_content = driver.page_source 
        
    # Save HTML to file with proper formatting
    soup = BeautifulSoup(html_content, 'html.parser')
    formatted_html = soup.prettify()
    
    with open(f"./debug/html/{filename}", 'w', encoding='utf-8') as f:
        f.write(formatted_html)
    print(f"Page successfully saved as {filename} with formatted HTML")
    
    # Ask user if they want to continue scraping
    user_choice = input("Do you want to continue scraping? (y/n)")
    
    if user_choice.lower() != 'y':
        print("Exiting scraping process.")
        return False
    
    print("Continuing with scraping...")
    return True

# - - - - - - - - -

if __name__ == "__main__":
    main()