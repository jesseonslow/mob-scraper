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
    if not url_map:
        return markdown_text

    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    def replacer(match):
        link_text = match.group(1)
        url = match.group(2)
        
        parsed_url = urlparse(url)
        if parsed_url.path in url_map:
            new_path = url_map[parsed_url.path]
            print(f"  -> Rewriting link: {parsed_url.path} -> {new_path}")
            return f'[{link_text}]({new_path})'
        else:
            return match.group(0)

    return link_pattern.sub(replacer, markdown_text)