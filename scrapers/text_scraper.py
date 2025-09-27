# scrapers/text_scraper.py
import re
from bs4 import BeautifulSoup
from markdownify import markdownify
from processing import format_body_content

def _apply_method(text: str, method: str) -> str:
    """Applies a post-processing method to the extracted text."""
    if method == 'last_word':
        parts = text.split()
        return parts[-1] if parts else ""
    if method == 'first_word':
        parts = text.split()
        return parts[0] if parts else ""
    return text

def _get_text_from_rule(soup: BeautifulSoup, rule: dict) -> str:
    """
    Helper to safely get text using a rule (selector + index).
    This is now backward-compatible with old string-based rules.
    """
    # --- FIX: Handle both old (string) and new (dict) rule formats ---
    if isinstance(rule, str):
        selector = rule
        index = 0
    else:
        selector = rule.get('selector')
        index = rule.get('index', 0)
    
    if not selector:
        return ""
    
    elements = soup.select(selector)
    if len(elements) > index:
        element = elements[index]
        raw_text = element.get_text(strip=True, separator=' ')
        clean_text = raw_text.replace('\ufffd', '')
        return " ".join(clean_text.split())
    return ""

def scrape_body_content(soup: BeautifulSoup, rules: dict) -> str:
    rule = rules.get('content_selector', {})
    
    # Handle both old and new rule formats
    if isinstance(rule, str):
        selector = rule
        index = 0
    else:
        selector = rule.get('selector')
        index = rule.get('index', 0)

    if not selector: return ""
    
    elements = soup.select(selector)
    if len(elements) > index:
        container = elements[index]
        return format_body_content(markdownify(str(container)))
    return ""

def scrape_citations(soup: BeautifulSoup, rules: dict) -> list[str]:
    rule = rules.get('citation_selector', {})
    text = _get_text_from_rule(soup, rule)
    return [text] if text else []

def scrape_name_author_status(soup: BeautifulSoup, rules: dict, genus_fallback: str) -> dict:
    """
    Parses a block of text to semantically identify the genus, name,
    author, and taxonomic statuses based on capitalization and structure.
    """
    name_rule = rules.get('name_selector', {})
    
    # We only need one rule to find the entire text block
    text_block = _get_text_from_rule(soup, name_rule)
    
    if not text_block:
        return {"name": "Unknown", "author": None, "taxonomic_status": [], "genus": genus_fallback}

    tokens = text_block.split()
    
    # 1. Extract Taxonomic Statuses (e.g., "sp. n.", "stat. rev.")
    statuses = []
    remaining_tokens = []
    for token in tokens:
        if '.' in token:
            statuses.append(token)
        else:
            remaining_tokens.append(token)
    
    # Re-assemble multi-word statuses
    taxonomic_status = [" ".join(statuses)] if statuses else []

    # 2. Extract Author (last capitalized word)
    author = None
    if remaining_tokens and remaining_tokens[-1].istitle():
        author = remaining_tokens.pop(-1)

    # 3. Extract Genus (first capitalized word)
    genus = None
    if remaining_tokens and remaining_tokens[0].istitle():
        genus = remaining_tokens.pop(0)

    # 4. The rest is the species name (and potential subspecies)
    name = " ".join(remaining_tokens)

    return {
        "name": name or "Unknown",
        "author": author,
        "taxonomic_status": taxonomic_status,
        "genus": genus or genus_fallback
    }