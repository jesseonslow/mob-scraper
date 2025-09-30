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

def is_data_valid(scraped_data: dict):
    """
    Performs a comprehensive quality check and returns a list of failing fields.
    """
    failures = []
    name = scraped_data.get("name")
    genus = scraped_data.get("genus")
    body = scraped_data.get("body_content", "")
    author = scraped_data.get("author")

    # --- THIS IS THE FIX ---
    # The name validation is now simpler and more robust, preventing false positives.
    if not name or name == "Unknown" or name in config.KNOWN_TAXONOMIC_STATUSES:
        failures.append('name')
    else:
        # --- THIS IS THE FIX ---
        # This version correctly handles all special cases we've discussed.
        is_special_sp_format = name.startswith('sp. ') and name.split(' ')[-1].isdigit()
        is_special_bracket_format = name.startswith('[') and ']' in name and len(name.split()) > 1
        
        if is_special_sp_format or is_special_bracket_format or name == 'sp.':
            # This is a valid special format, so we pass.
            pass
        else:
            # Fallback to the original format check for all other cases.
            has_uppercase = any(char.isupper() for char in name)
            if has_uppercase:
                if 'name' not in failures:
                    failures.append('name')

    if not genus or genus == "Unknown" or genus in config.KNOWN_TAXONOMIC_STATUSES:
        if 'genus' not in failures:
            failures.append('genus')
    else:
        # A valid genus must be a single word.
        if len(genus.split()) > 1:
            if 'genus' not in failures:
                failures.append('genus')

    if not author:
        if 'author' not in failures:
            failures.append('author')
    else:
        # Add a special check to invalidate "spp." as an author.
        normalized_author = author.strip('., ').lower()
        if normalized_author == 'spp':
            if 'author' not in failures:
                failures.append('author')
            
    if '<' in body or '>' in body:
        if 'content' not in failures:
            failures.append('content')

    if len(body.strip()) < 50:
        if 'content' not in failures:
            failures.append('content')

    return failures