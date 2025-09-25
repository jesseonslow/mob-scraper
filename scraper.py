# mob-scraper/scraper.py

import re
from typing import List
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from processing import format_body_content
from config import CDN_BASE_URL, BOOK_NUMBER_MAP, DEFAULT_PLATE, BOOK_SCRAPING_RULES

class SpeciesScraper:
    """
    A rule-based engine for scraping data from a single legacy species PHP file.
    """
    def __init__(self, soup: BeautifulSoup, book_name: str, genus_name: str):
        """
        Initializes the scraper with the parsed HTML content and contextual data.

        Args:
            soup: A BeautifulSoup object representing the parsed PHP file.
            book_name: The name of the book this species belongs to (e.g., 'three').
            genus_name: The name of the parent genus, needed for accurate name parsing.
        """
        self.soup = soup
        self.book_name = book_name
        self.book_number = BOOK_NUMBER_MAP.get(book_name)
        self.genus_fallback = genus_name
        # Load the rules for this book, falling back to default if none are defined
        self.rules = BOOK_SCRAPING_RULES.get(book_name, BOOK_SCRAPING_RULES['default'])

    def _get_text_from_selector(self, selector: str) -> str:
        """
        Helper to safely get cleaned text from a CSS selector, preserving spaces.
        """
        element = self.soup.select_one(selector)
        if element:
            # The separator=' ' is crucial for preserving spaces between tags.
            raw_text = element.get_text(strip=True, separator=' ')
            
            # Aggressively clean text: remove unicode replacement chars 
            # and normalize all whitespace (including &nbsp;) into single spaces.
            clean_text = raw_text.replace('\ufffd', '')
            return " ".join(clean_text.split())
        return ""


    def scrape_body_content(self) -> str:
        """Scrapes the main body content using book-specific rules."""
        selector = self.rules.get('content_container_selector')
        extraction_method = self.rules.get('content_extraction_method')

        if not selector:
            return ""
        
        container = self.soup.select_one(selector)
        if not container:
            return ""

        # Handle special extraction methods
        if extraction_method == 'last_span_text':
            text_nodes = [span.text for span in container.find_all('span') if span.text.strip()]
            if text_nodes:
                # Re-wrap in a <p> tag for consistent markdown processing
                from markdownify import markdownify
                html_content = f"<p>{text_nodes[-1]}</p>"
                return format_body_content(markdownify(html_content))
        
        # Default extraction
        from markdownify import markdownify
        return format_body_content(markdownify(str(container)))


    def scrape_citations(self) -> List[str]:
        """Scrapes citations using book-specific rules."""
        selector = self.rules.get('citation_selector')
        extraction_method = self.rules.get('citation_extraction_method')
        if not selector:
            return []

        container = self.soup.select_one(selector)
        if not container:
            return []
        
        if extraction_method == 'first_span_text':
            full_text = " ".join(container.get_text(strip=True, separator=' ').split())
            if full_text:
                return [full_text]
        
        return []

    def scrape_name_author_status(self):
        """Scrapes name, genus, and author using book-specific rules."""
        name_selector = self.rules.get('name_selector')
        genus_selector = self.rules.get('genus_selector')

        full_name_text = self._get_text_from_selector(name_selector)
        found_genus = self._get_text_from_selector(genus_selector) if genus_selector else None
        
        # If we found a genus, remove it from the main name string
        if found_genus:
            full_name_text = full_name_text.replace(found_genus, '').strip()

        # Extract taxonomic statuses (this logic is generally consistent)
        statuses = []
        status_patterns = [r'sp\.\s*n\.', r'comb\.\s*n\.', r'sp\.\s*rev\.', r'comb\.\s*rev\.']
        temp_text = full_name_text
        for pattern in status_patterns:
            match = re.search(pattern, temp_text, re.IGNORECASE)
            if match:
                statuses.append(match.group(0))
                temp_text = temp_text.replace(match.group(0), '')
        
        # Extract Author (heuristic: last capitalized word)
        author = None
        parts = temp_text.strip().split()
        if parts and (parts[-1].istitle() or parts[-1].isupper()):
            author = parts.pop()
            temp_text = " ".join(parts)

        # The remainder is the species name
        name = temp_text.strip()

        return {
            "name": name or "Unknown",
            "author": author,
            "taxonomic_status": statuses,
            "genus": found_genus or self.genus_fallback
        }

    def scrape_images_and_labels(self):
        """
        Scrapes all images and categorizes them into plates, genitalia, and misc.
        It also intelligently maps labels to the plate images.
        """
        plates, genitalia, misc_images = [], [], []
        if not self.book_number:
            return plates, genitalia, misc_images

        # Find all image tags in the document
        all_img_tags = self.soup.find_all('img')
        plate_tags = []

        # Categorize all images first
        for img in all_img_tags:
            src = img.get('src', '')
            clean_src = src.replace('../images/', '').replace('../', '')
            cdn_url = f"{CDN_BASE_URL}/{self.book_number}/{clean_src}"
            filename = Path(cdn_url).name.lower()
            
            is_plate, is_genitalia, is_misc = False, False, False
            # Book three has a unique naming convention for images
            if self.book_name == 'three':
                if re.match(r'^p.*?\d+.*', filename): is_plate = True
                elif re.match(r'^\d+\..*', filename): is_genitalia = True
                else: is_misc = True
            else:
                if 'plate' in cdn_url.lower(): is_plate = True
                elif 'genitalia' in cdn_url.lower(): is_genitalia = True
                else: is_misc = True
            
            if is_plate:
                plate_tags.append(img)
            elif is_genitalia:
                genitalia.append(cdn_url)
            elif is_misc:
                misc_images.append(cdn_url)

        if not plate_tags:
            # If no plates are found, return the default plate
            return [DEFAULT_PLATE[0]], genitalia, misc_images
        
        # Find all potential label strings
        label_strings = []
        for element in self.soup.find_all(['td', 'p']):
            text = element.get_text()
            if re.search(r'(♂|♀|\(holotype\)|\(paratype\))', text, re.IGNORECASE):
                label_parts = []
                symbol_match = re.search(r'(♂|♀)', text)
                type_match = re.search(r'(\(holotype\)|\(paratype\))', text, re.IGNORECASE)
                if symbol_match: label_parts.append(symbol_match.group(0))
                if type_match: label_parts.append(type_match.group(0).lower())
                label_strings.append(' '.join(label_parts))

        # Map labels to plate tags based on their order in the document
        label_map = {tag.get('src'): label_strings[i] for i, tag in enumerate(plate_tags) if i < len(label_strings)}
        
        for tag in plate_tags:
            src = tag.get('src')
            clean_src = src.replace('../images/', '').replace('../', '')
            cdn_url = f"{CDN_BASE_URL}/{self.book_number}/{clean_src}"
            plates.append({'url': cdn_url, 'label': label_map.get(src, "")}) # Use "" as default label

        return plates, genitalia, misc_images
    
    def scrape_all(self):
        """
        Executes all scraping methods and returns a consolidated dictionary of data.
        """
        name_data = self.scrape_name_author_status()
        body_content = self.scrape_body_content()
        citations = self.scrape_citations()
        plates, genitalia, misc_images = self.scrape_images_and_labels()
        
        return {
            "genus": name_data.get('genus'),
            "name": name_data['name'],
            "author": name_data['author'],
            "taxonomic_status": name_data['taxonomic_status'],
            "body_content": body_content,
            "citations": citations,
            "plates": plates,
            "genitalia": genitalia,
            "misc_images": misc_images
        }