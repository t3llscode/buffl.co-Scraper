from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from credentials.credentials import email, password
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from urllib.parse import urljoin
from selenium import webdriver
import platform
import requests
import time
import json
import uuid
import os

from utils_generic import ActionHandler, setup_driver
from utils_specific import click_fourth_by
from procedures.obtain_cardsets import get_all_cardsets, cardsets_information
from procedures.process_cardset import extract_cardsets


# - - - CONFIGURATION - - -

URL = "https://buffl.co"  # Replace with your target URL - buffl.co uses posthog, which should be disabled via setup_driver

# - - - - - - 

def main():
    
    driver = setup_driver(URL, headless=False)  # Set headless=False to see and interact with the browse

    handler = ActionHandler(driver, wait_time=1)

    # - - - LOGIN - - -

    handler.action_by("class", "TopNav_login__mpeOl", "click", "Login Button")

    handler.action_by("name", "email", f"w-{email}", "Email Input", wait_overwrite=0.25)
    handler.action_by("name", "password", f"w-{password}", "Password Input", wait_overwrite=0.25)

    handler.action_by("class", "login-btn", "click", "Login Submit Button")

    print("\n____________________________________________________________\n")

    # - - - COURSES & CARDSETS- - -

    cardsets = get_all_cardsets(handler)
    print(cardsets_information(cardsets))

    print("\n____________________________________________________________'n")

    # - - - EXPORT CARDSETS - - -

    extract_cardsets(handler, cardsets)
    # print(extraction_information(results))

    print("\n____________________________________________________________\n")
    
    # - - - SAVE RESULTS - - -

    # with open("cardsets_data.json", "w", encoding="utf-8") as f:
    #     json.dump(results, f, ensure_ascii=False, indent=4)

    # - - - END - - -

    input("If you hit 'Enter', the browser will close and the script will exit.")

    driver.quit()

# - - - - - -

if __name__ == "__main__":
    main()