import re

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