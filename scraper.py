# mob-scraper/scraper.py
from bs4 import BeautifulSoup
from config import BOOK_NUMBER_MAP, BOOK_SCRAPING_RULES
from scrapers import text_scraper, image_scraper

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
        # Call the specialized functions, passing the necessary context
        name_data = text_scraper.scrape_name_author_status(self.soup, self.rules, self.genus_fallback)
        body_content = text_scraper.scrape_body_content(self.soup, self.rules)
        citations = text_scraper.scrape_citations(self.soup, self.rules)
        plates, genitalia, misc_images = image_scraper.scrape_images_and_labels(self.soup, self.book_name, self.book_number)
        
        scraped_data = {
            "body_content": body_content,
            "citations": citations,
            "plates": plates,
            "genitalia": genitalia,
            "misc_images": misc_images
        }
        scraped_data.update(name_data)
        
        return scraped_data