import polars as pl

from utils_generic import ActionHandler

def get_all_cardsets(handler: ActionHandler):

    # - - - Check Courses - - -

    courses_elements = handler.get_all_by("class", "main-nav-link")
    courses = []

    for e in courses_elements:
        courses.append({
            "course-text": e.text.strip(),
            "course-href": e.get_attribute("href")
        })

        print("- ", e.text.strip(), " -> ", e.get_attribute("href"))

        import time

    # - - - Check for Cardsets in the Courses

    cardset_elements = []

    for course in courses:

        handler.driver.get(course["course-href"])

        elements, buttons = find_cardset_elements(handler)

        for i in range(len(buttons)):  # buttons as they hold the hrefs which are essential

            b = buttons[i]
            e = elements[i]

            texts = e.text.strip().split("\n")

            cardset_elements.append({
                "course-text": course["course-text"],
                "course-href": course["course-href"],
                "cardset-text": texts[0] if texts else "",
                "cardset-count": texts[1].replace(" Cards", "") if len(texts) > 1 else 0,
                "cardset-href": b.get_attribute("href")
            })

    # - - - Group by cardset-text and cardset-href - - -
    # aggreaate course-text and course-href into lists

    df = pl.DataFrame(cardset_elements)

    grouped_df = df.group_by(["cardset-text", "cardset-href", "cardset-count"]).agg([
        pl.col("course-text").unique().map_elements(lambda x: "; ".join(x)).alias("course-text"),
        pl.col("course-href").unique().map_elements(lambda x: "; ".join(x)).alias("course-href")
    ])

    return grouped_df.to_dicts()

# - - - UTILITY - - -

def cardsets_information(cardsets):
    info = "\n🔍 Found the following cardsets:\n"
    
    for cardset in cardsets:
        info += (
            f"\nCardset: {cardset['cardset-text']}\n"
            f"Course: {cardset['course-text']}\n"
            f"Cards: {cardset['cardset-count']}\n"
            f"Link: {cardset['cardset-href']}\n"
        )

    return info


def find_cardset_elements(handler: ActionHandler):

    for _ in range(60):  # Reasonable number of attempts

        if _ == 30: # Refresh each 30 tries
            handler.driver.refresh()

        try:
            # First check if resource tiles are available
            if handler.element_exists("class", "rlg-col", timeout=0.5, output=False):
                elements = handler.get_all_by("class", "rlg-col", timeout=0.5)
                buttons = handler.get_all_by("class", "learn-btn", timeout=0.5)
                return elements, buttons

            # Check if empty state is shown
            if handler.element_exists("class", "empty-state-wrapper", timeout=0.5, output=False):
                return [], []
            
            # Brief pause before checking again
            handler.wait_for(0.5)
        except:
            pass
    
    print("⚠️ Unexpected behavior in Cardset Extraction! (timeout reached)")

    return [], []
