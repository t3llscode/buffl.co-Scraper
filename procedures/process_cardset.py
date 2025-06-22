from datetime import datetime
import json
import time
import os

from utils_generic import ActionHandler

def extract_cardsets(handler, all_cardsets):

    print("\nStarting to process cardsets...")

    for cardset in all_cardsets:

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
                results.append(rsp)
                click_to_next(handler, rsp["type"])
                time.sleep(0.5)

            if rsp["type"] == "end":
                print("Reached the end of the cardset.")
                keep_scraping = False

            if rsp["type"] == "overview" or rsp["type"] == "error":
                print("⚠️ Unexpected behavior in Extraction, Overview was openend!")

        # - - - Save the results for this cardset

        if results:
            print(f"Extracted {len(results)} cards from the cardset '{cardset['cardset-text']}'.")

            # Create timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')

            # Create filename using cardset details for uniqueness
            filename = f"{timestamp}_{cardset['cardset-text']}_{cardset['cardset-href'].split('/')[-1]}.json"
            filename = ''.join(c if c.isalnum() or c in ['_', '-', '.'] else '_' for c in filename)

            # Ensure the output directory exists
            output_dir = 'results/data'
            os.makedirs(output_dir, exist_ok=True)

            # Save results to JSON file
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

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
    
    picture_hrefs = None

    return {
        "type": "card",
        "question": {
            "text": elements[0].text.strip(),
            "html": elements[0].get_attribute("innerHTML").strip()
        },
        "answer": {
            "text": elements[1].text.strip(),
            "html": elements[1].get_attribute("innerHTML").strip()
        },
        "pictures": picture_hrefs
    }


def extract_multiple_choice(handler: ActionHandler, elements):
    """ len(elements) == 1"""

    element = elements[0]  # Assuming the first element is the one we need

    # Immediately click the "reveal" button to show the answer
    handler.action_by("class", "flip", "click", timeout=0.5)

    answer_elements = handler.get_all_by("class", "mcoptions-select-item", timeout=0.5, output = False)

    picture_hrefs = None

    answers = []
    for ans in answer_elements:
        answers.append({
            "text": ans.text.strip(),
            "html": ans.get_attribute("innerHTML").strip(),
            "is_correct": "correct" in ans.get_attribute("class")  # get all classes and check if it contains "correct"
        })

    return {
        "type": "multiple-choice",
        "question": {
            "text": element.text.strip(),
            "html": element.get_attribute("innerHTML").strip()
        },
        "answers": answers,
        "pictures": picture_hrefs
    }
    

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
    if type == "card":
        click_icon(handler, 5)  # Click the "next / wrong" button for a normal card
    
    elif type == "multiple-choice":
        handler.action_by("class", "flip", "click", timeout=0.5)  # Click the "flip" button for a multiple-choice question
    
    else:
        print(f"⚠️ Unexpected type '{type}' in click_to_next!")