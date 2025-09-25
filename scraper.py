# mob-scraper/scraper.py

import re
from pathlib import Path
from bs4 import BeautifulSoup
from config import CDN_BASE_URL, BOOK_NUMBER_MAP, DEFAULT_PLATE

class SpeciesScraper:
    """
    Encapsulates all the logic for scraping data from a single legacy species PHP file.
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
        self.genus_name = genus_name

    def scrape_name_author_status(self):
        """
        Scrapes the species name, author, and taxonomic status.
        This logic is adapted from the robust implementation in missing_entries.py.
        """
        name_tag = self.soup.find('b')
        if not name_tag:
            return {"name": "Unknown", "author": None, "taxonomic_status": []}

        # 1. Pre-process text: remove brackets and clean corrupted characters
        raw_text = name_tag.get_text(strip=True, separator=' ')
        processed_text = re.sub(r'\[.*?\]', ' ', raw_text)
        clean_text = processed_text.replace('"', '').replace("'", "").strip()
        clean_genus = self.genus_name.replace('"', '').replace("'", "")

        # 2. Extract taxonomic statuses
        statuses = []
        status_patterns = [r'sp\.\s*n\.', r'comb\.\s*n\.', r'sp\.\s*rev\.', r'comb\.\s*rev\.']
        temp_text = clean_text
        for pattern in status_patterns:
            match = re.search(pattern, temp_text, re.IGNORECASE)
            if match:
                statuses.append(match.group(0))
                temp_text = temp_text.replace(match.group(0), '')
        
        # 3. Extract Author (heuristic: last capitalized word(s))
        author = None
        parts = temp_text.split()
        author_parts = []
        for part in reversed(parts):
            if part.istitle() or part.isupper() or (part.startswith('(') and part.endswith(')')):
                author_parts.insert(0, part)
            else:
                break
        if author_parts:
            author = " ".join(author_parts)
            temp_text = temp_text.replace(author, '').strip()

        # 4. Extract Name by removing the known genus
        name = re.sub(f'^{re.escape(clean_genus)}', '', temp_text, flags=re.IGNORECASE).strip()

        # 5. Apply special rules
        if 'sp. n.' in [s.lower() for s in statuses]:
            author = "Holloway"

        return {"name": name or "Unknown", "author": author, "taxonomic_status": statuses}

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
        plates, genitalia, misc_images = self.scrape_images_and_labels()
        
        return {
            "name": name_data['name'],
            "author": name_data['author'],
            "taxonomic_status": name_data['taxonomic_status'],
            "plates": plates,
            "genitalia": genitalia,
            "misc_images": misc_images
        }