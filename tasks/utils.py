# tasks/utils.py

import re
import config
from bs4 import BeautifulSoup

def get_contextual_data(missing_url, existing_species, existing_genera_by_url, existing_genera_by_slug):
    """
    Finds a neighboring or parent entry to provide context for a missing species.
    This shared function is used by both the audit and scrape_new tasks.
    """
    url_pattern = re.compile(r'(.+)_(\d+)_(\d+)\.php$')
    match = url_pattern.search(missing_url)
    if not match:
        return None, None
    base, major, minor = match.groups()

    # --- Logic Flow ---
    if missing_url in existing_genera_by_url:
        return existing_genera_by_url.get(missing_url), 'self-referential genus'

    neighbor_minor = int(minor) - 1
    if neighbor_minor > 0:
        neighbor_url = f"{base}_{major}_{neighbor_minor}.php"
        if neighbor_url in existing_species:
             return existing_species.get(neighbor_url), 'species neighbor'

    genus_url_format1 = f"{base}_{major}_1.php"
    if genus_url_format1 in existing_genera_by_url:
        return existing_genera_by_url.get(genus_url_format1), 'genus by unusual URL'

    genus_url_format2 = f"{base}_{major}.php"
    if genus_url_format2 in existing_genera_by_url:
        return existing_genera_by_url.get(genus_url_format2), 'genus by standard URL'

    if '/part-4/' in missing_url:
        try:
            genus_slug = missing_url.split('/part-4/', 1)[1].split('/')[0]
            if genus_slug in existing_genera_by_slug:
                return existing_genera_by_slug.get(genus_slug), 'genus by slug'
        except IndexError:
            pass
    
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
    """
    Scans all references.php files and returns a set of all reference strings.
    """
    print("Building reference lookup from all references.php files...")
    lookup = set()
    reference_files = list(config.PHP_ROOT_DIR.glob('**/references.php'))
    
    for ref_path in reference_files:
        try:
            with open(ref_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            container = None
            for p_tag in soup.find_all('p'):
                if re.search(r'\(\d{4}\)', p_tag.get_text()):
                    container = p_tag
                    break
            
            if container:
                references_html = str(container)
                individual_references = re.split(r'<br\s*/?>', references_html, flags=re.IGNORECASE)
                for ref_html in individual_references:
                    text = BeautifulSoup(ref_html, 'html.parser').get_text(strip=True)
                    if text:
                        lookup.add(text)
        except Exception:
            continue
            
    print(f"Reference lookup built with {len(lookup)} entries.")
    return lookup