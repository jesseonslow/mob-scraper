# core/citation_scraper.py

from bs4 import BeautifulSoup
from markdownify import markdownify
from .citation_parser import parse_citation, format_citation

def scrape_and_format_citation(soup: BeautifulSoup, rule: dict):
    """
    Selects a container, extracts the raw citation text, and then formats it
    using the centralized citation parser.
    """
    selector = rule.get('selector')
    index = rule.get('index', 0)
    if not selector:
        return None

    try:
        elements = soup.select(selector)
        container_tag = elements[index]
    except IndexError:
        return None

    if not container_tag:
        return None
    container = BeautifulSoup(str(container_tag), 'html.parser')

    first_b = container.find('b')
    if first_b:
        first_b.decompose()

    md_text = markdownify(str(container), strip=['a', 'p'])
    clean_text = " ".join(md_text.strip().split())
    
    # Use the new, centralized parser to format the text
    # We pass placeholder values as book_name/legacy_url are not critical here
    parsed_list = parse_citation(clean_text, "Unknown", "N/A")

    if not parsed_list or parsed_list[0].get("pattern") == "[INVALID CITATION]":
        # If parsing fails, return the original cleaned text as a fallback
        return clean_text
    
    # If parsing succeeds, format all parts and join them
    formatted_parts = [format_citation(p) for p in parsed_list]
    return "; ".join(formatted_parts)