# tasks/utils.py

import re
import config
from bs4 import BeautifulSoup

def get_contextual_data(missing_url, existing_species, existing_genera_by_url, existing_genera_by_slug):
    # ... (this function remains unchanged) ...
    
    return None, None

def get_book_from_url(url: str) -> str:
    """Extracts the book name (e.g., 'seven') from a legacy URL."""
    match = re.search(r'/part-([\d-]+)/', url)
    if match:
        part_str = match.group(1)
        book_num = '15-16' if part_str == '15-16' else part_str.split('-')[0]
        return config.BOOK_WORD_MAP.get(book_num, "Unknown")
    return "Unknown"

# The is_data_valid function has been removed. Its logic now lives in models/species.py

def load_reference_lookup():
    # ... (this function remains unchanged) ...
    
    print(f"Reference lookup built with {len(lookup)} entries.")
    return lookup