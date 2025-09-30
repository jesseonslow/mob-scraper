# link_rewriter.py

import re
from urllib.parse import urlparse
from file_system import build_legacy_to_new_url_map

_url_map = None

def get_url_map():
    """Helper function to build the map once and cache it."""
    global _url_map
    if _url_map is None:
        _url_map = build_legacy_to_new_url_map()
    return _url_map

def rewrite_legacy_links(markdown_text: str):
    """
    Finds all markdown links in a block of text and replaces any legacy URLs
    with their new, correct paths using the generated URL map.
    """
    url_map = get_url_map()
    if not url_map: return markdown_text

    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    def replacer(match):
        link_text, url = match.groups()
        
        # --- FIX: Handle relative links by checking if the URL is at the end of a legacy path ---
        for legacy_path, new_path in url_map.items():
            if legacy_path.endswith(url):
                # Make the new path relative, e.g., ./slug
                relative_new_path = f".{new_path.replace('/species', '')}"
                print(f"  -> Rewriting link: {url} -> {relative_new_path}")
                return f'[{link_text}]({relative_new_path})'
        
        # If no match was found, return the original link
        return match.group(0)

    return link_pattern.sub(replacer, markdown_text)