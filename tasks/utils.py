import re
import config

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
    # 1. Self-Referential Check
    if missing_url in existing_genera_by_url:
        return existing_genera_by_url.get(missing_url), 'self-referential genus'

    # 2. Species Neighbor Check
    neighbor_minor = int(minor) - 1
    if neighbor_minor > 0:
        neighbor_url = f"{base}_{major}_{neighbor_minor}.php"
        if neighbor_url in existing_species:
             return existing_species.get(neighbor_url), 'species neighbor'

    # 3. Unusual Genus URL Check (..._XX_1.php)
    genus_url_format1 = f"{base}_{major}_1.php"
    if genus_url_format1 in existing_genera_by_url:
        return existing_genera_by_url.get(genus_url_format1), 'genus by unusual URL'

    # 4. Standard Genus URL Check (..._XX.php)
    genus_url_format2 = f"{base}_{major}.php"
    if genus_url_format2 in existing_genera_by_url:
        return existing_genera_by_url.get(genus_url_format2), 'genus by standard URL'

    # 5. Book 4 Fallback
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
    # This regex correctly uses a single backslash for the digit character class
    match = re.search(r'/part-([\d-]+)/', url)
    if match:
        part_str = match.group(1)
        # Handle cases like '15-16' vs '15'
        book_num = '15-16' if part_str == '15-16' else part_str.split('-')[0]
        return config.BOOK_WORD_MAP.get(book_num, "Unknown")
    return "Unknown"

def is_data_valid(scraped_data: dict):
    """
    Performs a comprehensive quality check and returns a list of failing fields.
    """
    failures = []
    name = scraped_data.get("name")
    genus = scraped_data.get("genus")
    body = scraped_data.get("body_content", "")
    author = scraped_data.get("author")

    if (not name or name == "Unknown" or '\ufffd' in name or
            name in config.KNOWN_TAXONOMIC_STATUSES or name == author):
        failures.append('name')
    
    if not genus or genus == "Unknown" or genus in config.KNOWN_TAXONOMIC_STATUSES:
        failures.append('genus')

    if not author:
        failures.append('author')

    if len(body.strip()) < 50:
        failures.append('content')

    return failures