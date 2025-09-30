from bs4 import BeautifulSoup
import re
from pathlib import Path
from config import BOOK_NUMBER_MAP, SCRAPING_RULES, CDN_BASE_URL, DEFAULT_PLATE
from .parser import parse_html_with_rules
from .html_preprocessor import remove_font_tags

def scrape_images_and_labels(soup: BeautifulSoup, book_name: str, book_number: str) -> tuple:
    """
    Scrapes all images and categorizes them, mapping labels to plates.
    """
    plates, genitalia, misc_images = [], [], []
    if not book_number:
        return [DEFAULT_PLATE[0]], genitalia, misc_images

    all_img_tags = soup.find_all('img')
    plate_tags = []

    for img in all_img_tags:
        src = img.get('src', '')
        clean_src = src.replace('../images/', '').replace('../', '')
        cdn_url = f"{CDN_BASE_URL}/{book_number}/{clean_src}"
        filename = Path(cdn_url).name.lower()
        
        is_plate = False
        if book_name == 'three':
            if re.match(r'^p.*?\d+.*', filename): is_plate = True
            elif re.match(r'^\d+\..*', filename): genitalia.append(cdn_url)
            else: misc_images.append(cdn_url)
        else:
            if 'plate' in cdn_url.lower(): is_plate = True
            elif 'genitalia' in cdn_url.lower(): genitalia.append(cdn_url)
            else: misc_images.append(cdn_url)
        
        if is_plate:
            plate_tags.append(img)

    if not plate_tags:
        return [DEFAULT_PLATE[0]], genitalia, misc_images
    
    label_strings = []
    for element in soup.find_all(['td', 'p']):
        text = element.get_text()
        if re.search(r'(♂|♀|\(holotype\)|\(paratype\))', text, re.IGNORECASE):
            label_parts = []
            symbols = re.findall(r'(♂|♀)', text)
            types = re.findall(r'(\(holotype\)|\(paratype\))', text, re.IGNORECASE)
            
            max_len = max(len(symbols), len(types))
            for i in range(max_len):
                parts = []
                if i < len(symbols):
                    parts.append(symbols[i])
                if i < len(types):
                    parts.append(types[i].lower())
                if parts:
                    label_strings.append(' '.join(parts))

    label_map = {tag.get('src'): label_strings[i] for i, tag in enumerate(plate_tags) if i < len(label_strings)}
    
    for tag in plate_tags:
        src = tag.get('src')
        clean_src = src.replace('../images/', '').replace('../', '')
        cdn_url = f"{CDN_BASE_URL}/{book_number}/{clean_src}"
        plates.append({'url': cdn_url, 'label': label_map.get(src, "")})

    return plates, genitalia, misc_images

class SpeciesScraper:
    """
    Orchestrates the scraping of a species page by calling specialized modules.
    """
    def __init__(self, html_content: str, book_name: str, genus_name: str):
        # --- THIS IS THE FIX ---
        # 1. Clean the raw HTML before parsing.
        cleaned_html = remove_font_tags(html_content)
        
        # 2. Parse the *cleaned* HTML with BeautifulSoup.
        self.soup = BeautifulSoup(cleaned_html, 'html.parser')
        
        self.book_name = book_name
        self.book_number = BOOK_NUMBER_MAP.get(book_name)
        self.genus_fallback = genus_name
                # 1. Get the appropriate set of rules for the book.
        self.rules = BOOK_SCRAPING_RULES.get(book_name, BOOK_SCRAPING_RULES.get('default', {}))
        # 2. Add the book's name to the rules dictionary so the parser can identify it.
        self.rules['book_name'] = book_name
    
    def scrape_all(self):
        """
        Executes all scraping methods and returns a consolidated dictionary of data.
        This is the single source of truth for scraping.
        """
        # 1. Get all text data using the unified, rule-based parser
        text_data = parse_html_with_rules(self.soup, self.rules, self.genus_fallback)
        
        # 2. Get all image data
        plates, genitalia, misc_images = scrape_images_and_labels(
            self.soup, self.book_name, self.book_number
        )
        
        # 3. Combine and return the final dictionary
        text_data.update({
            "plates": plates,
            "genitalia": genitalia,
            "misc_images": misc_images
        })
        
        return text_data