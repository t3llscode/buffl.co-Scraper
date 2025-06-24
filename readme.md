# Buffl.co Scraper

### Want to learn at your own pace - and with your own data?

Unfortunately [Buffl.co](https://buffl.co) does not offer any export, so I built one.
This little script will scrape all your learning card sets available on your Buffl.co account.

## Setup

1. Clone the repository
2. Create a `credentials.py` within the `credentials` directory
3. Add your Buffl.co credentials in the variables `email` and `password` within `credentials.py`
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```
3. Activate the virtual environment:
   ```bash
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run `_main.py`

## Output

For each set you'll get a json file in the directory / format: `results/data/YYYY-MM-DD_HH-MM_Card_Set_Name.json`

This file contains a list like below with an object for each card in the set. For ease of use and further usage of the data I kept the original html of the card. Image links are automatically replaced to point to the `media` directory, which holds all the downloaded pictures. There is also a list of all image paths.

```json
[
  {
    "is_card": true, // this will be removed in a future commit
    "type": "card", // either 'card' or 'multiple-choice'
    "card": {
      "question": {
        "text": "What is your favorite tool to get learning cards from Buffl.co?",
        "html": "<div><div class=\"goethe-image2\"><div class=\"image-wrapper2\"><div><img tabindex=\"0\" src=\"results/media/f6aa1f60-239e-11e9-b6b1-0fbb16611da6.png\" class=\"img\" style=\"cursor: zoom-in; opacity: 1; border-radius: 12px; width: auto;\"></div></div></div><p><span>What is your favorite tool to get learning cards from Buffl.co? </span></p></div>"
      },
      "answer": {
        "text": "Of course it's `t3llscode/buffl.co-Scraper` which has the following, awesome features: \nScraping Learning Cards \nScraping Multiple Choice Questions \nDownloading Images",
        "html": "<div><p><span>Of course it's `t3llscode/buffl.co-Scraper` which has the following, awesome features: </span></p><ul><li><p><span>Scraping Learning Cards </span></p></li><li><p><span>Scraping Multiple Choice Questions </span></p></li><li><p><span>Downloading Images </span></p></li></ul><p><br></p></div>"
      },
      "pictures": ["results/media/"],
      "hash": "2887e19c8bde0b985e742fc572b4432d" // this will be removed in a future commit
    }
  },{
    "is_card": true, // this will be removed in a future commit
    "type": "multiple-choice", // either 'card' or 'multiple-choice'
    "card": {
      "question": {
        "text": "What features would you like next for the `t3llscode/buffl.co-Scraper`?",
        "html": "<div><p><span>What feature would you like next for the `t3llscode/buffl.co-Scraper`? </span></p></div>"
      },
      "answers": [
        {
          "text": "Markdown Export",
          "html": "<div class=\"label\">Markdown Export</div>",
          "is_correct": true
        },
        {
          "text": "XML Export",
          "html": "<div class=\"label\">XML Export</div>",
          "is_correct": true
        },
        {
          "text": "An AI Feature",
          "html": "<div class=\"label\">An AI Feature</div>",
          "is_correct": false
        }
      ],
      "hash": "edfeec990f42a87534772811aa10c062" // this will be removed in a future commit
    }
  }
]
```