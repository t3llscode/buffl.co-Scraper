from datetime import datetime
import requests
import hashlib
import json
import time
import os

from utils_generic import ActionHandler

def extract_cardsets(handler, all_cardsets):

    print("\nStarting to process cardsets...")

    for cardset in all_cardsets:

        count = 0
        total_results = []

        while count < cardset["cardset-count"]:

            results = []

            print(f"\nProcessing cardset: {cardset['cardset-text']}")

            handler.driver.get(cardset["cardset-href"])

            results = []

            error = True

            # - - - First get to the cardset Overview Page

            first_rsp = find_goethe_elements(handler)

            if first_rsp["is_card"]:
                error = leave_card_to_overview(handler)  # clicks the X and on the overview starts a full run through all cards
            
            if error:
                print("⚠️ Unexpected behavior in Navigation to Overview!")


            keep_scraping = True

            while keep_scraping:

                rsp = find_goethe_elements(handler)

                if rsp["is_card"]:
                    # Download images for all card types
                    if rsp["type"] == "card":
                        # For regular cards, we need to download images here since extract_card doesn't have handler
                        rsp["card"] = extract_and_download_pictures(handler, rsp["card"], log=True)
                    # For multiple-choice cards, images are already downloaded in extract_multiple_choice
                    
                    results.append(rsp)
                    click_to_next(handler, rsp["type"])
                    time.sleep(0.25)

                if rsp["type"] == "end":
                    print("Reached the end of the cardset.")
                    keep_scraping = False

                if rsp["type"] == "overview" or rsp["type"] == "error":
                    print("⚠️ Unexpected behavior in Extraction, Overview was openend!")

            # - - - Save the results for this cardset

            all_hashs = [r["card"]["hash"] for r in total_results if "hash" in r["card"]]
            new_count = 0

            for result in results:
                if result["card"]["hash"] not in all_hashs:
                    total_results.append(result)
                    all_hashs.append(result["card"]["hash"])
                    new_count += 1

            print(f"Extracted new {new_count} cards from the cardset '{cardset['cardset-text']}'.")
            print(f"Total cards extracted so far: {len(total_results)}")
            print(f"Expected cards in this cardset: {cardset['cardset-count']}")

            count = len(total_results)  # Update count to the number of cards extracted

        # Create timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')

        # Create filename using cardset details for uniqueness
        filename = f"{timestamp}_{cardset['cardset-text']}_{cardset['cardset-href'].split('/')[-1]}.json"
        filename = ''.join(c if c.isalnum() or c in ['_', '-', '.'] else '_' for c in filename)

        # Ensure the output directory exists
        output_dir = 'results/data'
        os.makedirs(output_dir, exist_ok=True)

        if len(total_results) > cardset['cardset-count']:
            total_results = total_results_duplicate_check(total_results)

        # Save results to JSON file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(total_results, f, ensure_ascii=False, indent=2)

        print(f"Saved results to {output_path}")

# - - - UTILITY - - -

def find_goethe_elements(handler: ActionHandler):

    type = None  # card, multiple-choice, overview, end

    for _ in range(30):

        if _ == 15: # Refresh each 15 tries
            handler.driver.refresh()
        
        # goethe-container - card (normal or multiple-choice)
        if handler.element_exists("class", "goethe-container", timeout=0.5, output = False):
            elements = handler.get_all_by("class", "goethe-container", timeout=0.5, output = False)
            
            if len(elements) == 1 and handler.element_exists("class", "mcoptions-select-item", timeout=0.5, output = False):
                return {
                    "is_card": True,
                    "type": "multiple-choice",
                    "card": extract_multiple_choice(handler, elements)
                }
            elif len(elements) == 2:
                return {
                    "is_card": True,
                    "type": "card",
                    "card": extract_card(elements)
                }
            else:
                print("⚠️ Unexpected behavior in Card Extraction!")

        # check for "end" screen
        elif handler.element_exists("class", "empty-state-wrapper", timeout=0.5, output = False):
            return {
                "is_card": False,
                "type": "end",
                "card": None
            }
        
        # check for "overview" screen
        elif handler.element_exists("class", "diagram-box", timeout=0.5, output = False):
            return {
                "is_card": False,
                "type": "overview",
                "card": None
            }

    print("⚠️ Unexpected behavior in Card Extraction! (timeout reached)") 

    return {
        "is_card": False,
        "type": "error",
        "card": None
    }


def extract_card(elements):
    """ len(elements) == 2 """
    
    picture_hrefs = []

    # Extract data from elements with error handling
    try:
        question_text = elements[0].text.strip()
        question_html = elements[0].get_attribute("innerHTML").strip()
        answer_text = elements[1].text.strip()
        answer_html = elements[1].get_attribute("innerHTML").strip()
    except Exception as e:
        print(f"⚠️ Error extracting card data: {e}")
        # Set empty values if extraction fails
        question_text = ""
        question_html = ""
        answer_text = ""
        answer_html = ""

    rsp = {
        "question": {
            "text": question_text,
            "html": question_html
        },
        "answer": {
            "text": answer_text,
            "html": answer_html
        },
        "pictures": picture_hrefs
    }

    # Note: Image downloading is handled separately for regular cards
    # since we don't have the handler here
    
    # Create a unique hash from the card content
    content_to_hash = json.dumps(rsp, sort_keys=True).encode('utf-8')
    rsp["hash"] = hashlib.md5(content_to_hash).hexdigest()
    
    return rsp


def extract_multiple_choice(handler: ActionHandler, elements):
    """ len(elements) == 1"""

    element = elements[0]  # Assuming the first element is the one we need

    # Extract question data BEFORE clicking anything to avoid stale element reference
    try:
        question_text = element.text.strip()
        question_html = element.get_attribute("innerHTML").strip()
    except Exception as e:
        print(f"⚠️ Error extracting question data: {e}")
        # Try to re-find the element
        try:
            elements = handler.get_all_by("class", "goethe-container", timeout=0.5, output=False)
            if elements:
                element = elements[0]
                question_text = element.text.strip()
                question_html = element.get_attribute("innerHTML").strip()
            else:
                question_text = ""
                question_html = ""
        except:
            question_text = ""
            question_html = ""

    # Immediately click the "reveal" button to show the answer
    handler.action_by("class", "flip", "click", timeout=0.5)

    answer_elements = handler.get_all_by("class", "mcoptions-select-item", timeout=0.5, output = False)

    picture_hrefs = []

    answers = []
    for ans in answer_elements:
        try:
            answers.append({
                "text": ans.text.strip(),
                "html": ans.get_attribute("innerHTML").strip(),
                "is_correct": "correct" in ans.get_attribute("class")  # get all classes and check if it contains "correct"
            })
        except Exception as e:
            print(f"⚠️ Error extracting answer data: {e}")
            # Skip this answer if we can't extract it
            continue

    rsp = {
        "question": {
            "text": question_text,
            "html": question_html
        },
        "answers": answers,
        "pictures": picture_hrefs
    }

    rsp = extract_and_download_pictures(handler, rsp, log=True)

    # Create a unique hash from the card content
    content_to_hash = json.dumps(rsp, sort_keys=True).encode('utf-8')
    rsp["hash"] = hashlib.md5(content_to_hash).hexdigest()
    
    return rsp
    

def leave_card_to_overview(handler: ActionHandler):

    error = click_icon(handler, 4)  # Click the "X" buttonn (4th icon button)

    if error:
        print("⚠️ Error while clicking the 'X' button to leave the card!")
        return True

    rsp = find_goethe_elements(handler)

    if rsp["type"] == "overview":
        
        handler.action_by("class", "all-courses-col", "click", timeout=0.5)  # Click the overview box to start the full run

        return False

    print("⚠️ Unexpected behavior in Navigation to Overview!")
    return True  # TOOD: Maybe throw an exception here to stop the process?
        

def click_icon(handler: ActionHandler, occurence: int):
    button_elements = handler.get_all_by("class", "btn-icon-only", timeout=0.5, output = False)

    if len(button_elements) < occurence:
        print(f"⚠️ Not enough buttons found! Expected at least {occurence}, found {len(button_elements)}.")
        return True
    
    elif len(button_elements) != 6:
        print(f"⚠️ Unexpected number of buttons found! Expected 6, found {len(button_elements)}.")
        return True

    button_elements[occurence - 1].click()  # Click the button at the specified occurrence
    
    return False


def click_to_next(handler: ActionHandler, type: str):
    """
    Clicks the "next" button to go to the next card or multiple-choice question.
    """
    if type == "multiple-choice":
        handler.action_by("class", "flip", "click", timeout=0.5)  # Click the "flip" button for a multiple-choice question
        
    elif type == "card":
        click_icon(handler, 5)  # Click the "next / wrong" button for a normal card
    
    else:
        print(f"⚠️ Unexpected type '{type}' in click_to_next!")

    
def extract_and_download_pictures(handler: ActionHandler, rsp, log: bool = False) -> dict:
    """
    Extract and download pictures from card content, replacing URLs with local paths.
    
    Args:
        handler: ActionHandler instance for downloading images (uses driver's cookies)
        rsp: Card response dictionary containing HTML content
        log: Whether to print debug information (default: False)
        
    Returns:
        Updated dictionary with local image paths
    """
    import re
    import os
    import base64
    from urllib.parse import urlparse
    
    # Convert response to string for searching
    rsp_str = json.dumps(rsp, ensure_ascii=False)
    
    if log:
        print(f"Debug: Searching for images in JSON string (first 500 chars): {rsp_str[:500]}")
    
    # Multiple patterns to catch different image URL formats
    patterns = [
        # Pattern for escaped quotes in JSON
        r'src=\\"(https://[^"]*\\.(?:png|jpg|jpeg|gif|webp|svg)[^"]*)\\"',
        # Pattern for regular quotes
        r'src="(https://[^"]*\.(?:png|jpg|jpeg|gif|webp|svg)[^"]*)"',
        # Pattern for single quotes
        r"src='(https://[^']*\.(?:png|jpg|jpeg|gif|webp|svg)[^']*)'",
        # Pattern without quotes (less likely but possible)
        r'src=(https://[^\s>]*\.(?:png|jpg|jpeg|gif|webp|svg)[^\s>]*)',
        # More general pattern for any image URL
        r'(https://[^\s"\'<>]*\.(?:png|jpg|jpeg|gif|webp|svg)(?:\?[^\s"\'<>]*)?)',
    ]
    
    all_matches = []
    for pattern in patterns:
        matches = re.findall(pattern, rsp_str, re.IGNORECASE)
        if matches:
            if log:
                print(f"Found {len(matches)} matches with pattern: {pattern}")
            # Some patterns return tuples, others return strings
            for match in matches:
                if isinstance(match, tuple):
                    # Take the first group (the URL)
                    url = match[0] if match[0] else (match[1] if len(match) > 1 else match)
                else:
                    url = match
                if url and url not in all_matches:
                    all_matches.append(url)
    
    if not all_matches:
        if log:
            print("No images found in card content")
        return rsp
    
    # Use all found URLs
    image_urls = all_matches
    
    if log:
        print(f"Found {len(image_urls)} images to download")
    
    # Ensure media directory exists
    media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results', 'media')
    os.makedirs(media_dir, exist_ok=True)
    
    # Process each image URL
    url_mapping = {}
    
    for image_url in image_urls:
        try:
            # Extract filename from URL
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path)
            
            # If no filename, create one from URL hash
            if not filename or '.' not in filename:
                url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
                filename = f"{url_hash}.png"
            
            # Ensure we have an extension
            if '.' not in filename:
                filename += '.png'
            
            local_path = os.path.join(media_dir, filename)
            
            # Download image if not already exists
            if not os.path.exists(local_path):
                if log:
                    print(f"Downloading: {image_url}")
                
                try:
                    # Method 1: Use handler's driver to download with cookies in a new tab
                    # Store current window handle
                    current_window = handler.driver.current_window_handle
                    
                    # Open image in new tab
                    handler.driver.execute_script(f"window.open('{image_url}', '_blank');")
                    
                    # Switch to the new tab
                    new_window = None
                    for window_handle in handler.driver.window_handles:
                        if window_handle != current_window:
                            new_window = window_handle
                            break
                    
                    if new_window:
                        handler.driver.switch_to.window(new_window)
                        time.sleep(1)  # Wait for image to load
                        
                        # Get image data as base64
                        image_data = handler.driver.execute_script("""
                            var canvas = document.createElement('canvas');
                            var ctx = canvas.getContext('2d');
                            var img = document.getElementsByTagName('img')[0];
                            if (img && img.complete && img.naturalWidth > 0) {
                                canvas.width = img.naturalWidth;
                                canvas.height = img.naturalHeight;
                                ctx.drawImage(img, 0, 0);
                                return canvas.toDataURL().split(',')[1];
                            }
                            return null;
                        """)
                        
                        # Close the new tab and switch back to original
                        handler.driver.close()
                        handler.driver.switch_to.window(current_window)
                    else:
                        if log:
                            print(f"⚠️ Could not open new tab for: {image_url}")
                        image_data = None
                    
                    if image_data:
                        # Decode base64 and save
                        with open(local_path, 'wb') as f:
                            f.write(base64.b64decode(image_data))
                        
                        if log:
                            print(f"✓ Saved: {filename}")
                    else:
                        # Method 2: Try direct request with session cookies
                        if log:
                            print(f"⚠️ Canvas method failed, trying direct request for: {image_url}")
                        
                        # Get cookies from selenium driver
                        cookies = handler.driver.get_cookies()
                        session = requests.Session()
                        for cookie in cookies:
                            session.cookies.set(cookie['name'], cookie['value'])
                        
                        # Add headers to mimic browser
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Accept-Encoding': 'gzip, deflate, br',
                            'Connection': 'keep-alive',
                            'Upgrade-Insecure-Requests': '1',
                        }
                        
                        response = session.get(image_url, headers=headers, timeout=10)
                        if response.status_code == 200 and len(response.content) > 0:
                            with open(local_path, 'wb') as f:
                                f.write(response.content)
                            if log:
                                print(f"✓ Saved via direct request: {filename}")
                        else:
                            if log:
                                print(f"⚠️ Direct request failed ({response.status_code}), keeping original URL: {image_url}")
                            url_mapping[image_url] = image_url  # Keep original URL
                            continue
                            
                except Exception as e:
                    if log:
                        print(f"⚠️ Both download methods failed for {image_url}: {e}")
                    url_mapping[image_url] = image_url  # Keep original URL
                    continue
            else:
                if log:
                    print(f"✓ Already exists: {filename}")
            
            # Store mapping for URL replacement
            relative_path = f"results/media/{filename}"
            url_mapping[image_url] = relative_path
            
        except Exception as e:
            if log:
                print(f"❌ Failed to download {image_url}: {e}")
            # Keep original URL if download fails
            url_mapping[image_url] = image_url
    
    # Replace URLs in the response with local paths
    updated_rsp_str = rsp_str
    replacement_count = 0
    for original_url, local_path in url_mapping.items():
        if original_url in updated_rsp_str:
            updated_rsp_str = updated_rsp_str.replace(original_url, local_path)
            replacement_count += 1
            if log:
                print(f"  ✓ Replaced {original_url} -> {local_path}")
        elif log:
            print(f"  ⚠️ URL not found in response: {original_url}")
    
    if log:
        print(f"Made {replacement_count} URL replacements")
    
    # Convert back to dictionary
    try:
        updated_rsp = json.loads(updated_rsp_str)

        # Add picture paths to the 'pictures' field
        picture_paths = [path for path in url_mapping.values() if path and path.startswith('results/media/')]
        if picture_paths:
            updated_rsp['pictures'] = picture_paths

        if log:
            successful_downloads = len([v for v in url_mapping.values() if v.startswith('results/')])
            print(f"✓ Successfully processed {successful_downloads} image URLs with local paths")
        return updated_rsp
    except json.JSONDecodeError as e:
        if log:
            print(f"❌ Failed to parse updated JSON: {e}")
            print(f"JSON content (first 500 chars): {updated_rsp_str[:500]}")
        return rsp  # Return original if parsing fails

def total_results_duplicate_check(total_results):
    """
    Duplicates have a different hash, this is because there are weird errors which lead to missing fields - but the html is always the same.
    
    Search the results for duplicates based on result['card''question''html'] for result in total_results

    If you find duplicates, remove the one where card has the most values which are "" or None
    """
    html_groups = {}
    for result in total_results:
        try:
            # Group results by the HTML of the question
            html = result['card']['question']['html']
            if html not in html_groups:
                html_groups[html] = []
            html_groups[html].append(result)
        except (KeyError, TypeError):
            # Handle malformed results by treating them as unique
            html_groups[id(result)] = [result]

    def count_empty_fields(res):
        """Counts how many important fields are empty in a result."""
        card = res.get('card', {})
        if not card:
            return float('inf')  # Should be heavily penalized

        count = 0
        # Check question text
        if not card.get('question', {}).get('text'):
            count += 1

        # Check answer text(s)
        if res.get('type') == 'card':
            if not card.get('answer', {}).get('text'):
                count += 1
        elif res.get('type') == 'multiple-choice':
            answers = card.get('answers', [])
            if not answers or all(not ans.get('text') for ans in answers):
                count += 1
        
        # Check for pictures
        if res.get('pictures') is None:
            count += 1
            
        return count

    final_results = []
    for group in html_groups.values():
        if len(group) <= 1:
            final_results.extend(group)
        else:
            # Find the best result (one with the fewest empty fields)
            best_result = min(group, key=count_empty_fields)
            final_results.append(best_result)

    return final_results