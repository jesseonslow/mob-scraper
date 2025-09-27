# mob-scraper/scraper.py
from bs4 import BeautifulSoup
from config import BOOK_NUMBER_MAP, BOOK_SCRAPING_RULES
# Import the single text parser and the image scraper
from parser import parse_html_with_rules
from scrapers import image_scraper

class SpeciesScraper:
    """
    Orchestrates the scraping of a species page by calling specialized modules.
    """
    def __init__(self, soup: BeautifulSoup, book_name: str, genus_name: str):
        self.soup = soup
        self.book_name = book_name
        self.book_number = BOOK_NUMBER_MAP.get(book_name)
        self.genus_fallback = genus_name
        self.rules = BOOK_SCRAPING_RULES.get(book_name, BOOK_SCRAPING_RULES['default'])
    
    def scrape_all(self):
        """
        Executes all scraping methods and returns a consolidated dictionary of data.
        """
        # Call the new, unified text parser
        text_data = parse_html_with_rules(self.soup, self.rules, self.genus_fallback)
        
        # Call the image scraper
        plates, genitalia, misc_images = image_scraper.scrape_images_and_labels(
            self.soup, self.book_name, self.book_number
        )
        
        # Consolidate the results
        text_data.update({
            "plates": plates,
            "genitalia": genitalia,
            "misc_images": misc_images
        })
        
        return text_data