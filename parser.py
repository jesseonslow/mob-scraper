# parser.py
import re
import string
from bs4 import BeautifulSoup
from markdownify import markdownify
from processing import format_body_content, correct_text_spacing
from config import KNOWN_TAXONOMIC_STATUSES

# --- Low-Level Helper Functions ---

def _apply_method(text: str, method: str) -> str:
    """Applies a post-processing method to the extracted text."""
    tokens = text.split()
    if not tokens: return ""

    if method.startswith('position_'):
        try:
            pos = int(method.split('_')[1])
            index = pos - 1 if pos > 0 else pos
            return tokens[index]
        except (ValueError, IndexError):
            return ""
    elif method == 'first_lowercase':
        for token in tokens:
            clean_token = token.strip(string.punctuation)
            if clean_token and (clean_token.islower() or clean_token.isdigit()):
                return token
        return "" # Return empty string if no match is found
    elif method == 'first_titlecase':
        for token in tokens:
            clean_token = token.strip(string.punctuation)
            if clean_token and clean_token.istitle():
                return token
        return "" # Return empty string if no match is found
    # --- The method 'last_word' was not fully implemented ---
    elif method == 'last_word':
        # Find the last token that is not a known taxonomic status
        for token in reversed(tokens):
            if token.strip(string.punctuation).lower() not in config.KNOWN_TAXONOMIC_STATUSES:
                return token.strip(string.punctuation)
        return "" # Return empty if all words are statuses
    return text

def _get_text_from_rule(soup: BeautifulSoup, rule: dict) -> str:
    """Helper to safely get text using a rule (selector + index)."""
    if isinstance(rule, str):
        selector, index = rule, 0
    else:
        selector, index = rule.get('selector'), rule.get('index', 0)
    
    if not selector: return ""
    
    elements = soup.select(selector)
    if len(elements) > index:
        element = elements[index]
        raw_text = element.get_text(strip=True, separator=' ')
        clean_text = raw_text.replace('\ufffd', '')
        return " ".join(clean_text.split())
    return ""

# --- The Single, Authoritative Parsing Function ---

def _apply_method(text: str, method: str) -> str:
    """Applies a post-processing method to the extracted text."""
    tokens = text.split()
    if not tokens: return ""

    if method.startswith('position_'):
        try:
            pos = int(method.split('_')[1])
            index = pos - 1 if pos > 0 else pos
            return tokens[index]
        except (ValueError, IndexError):
            return ""
    elif method == 'first_lowercase':
        for token in tokens:
            clean_token = token.strip(string.punctuation)
            if clean_token and (clean_token.islower() or clean_token.isdigit()):
                return token
        return ""
    elif method == 'first_titlecase':
        for token in tokens:
            clean_token = token.strip(string.punctuation)
            if clean_token and clean_token.istitle():
                return token
        return ""
    elif method == 'last_word':
        for token in reversed(tokens):
            if token.strip(string.punctuation).lower() not in KNOWN_TAXONOMIC_STATUSES:
                return token.strip(string.punctuation)
        return ""
    return text

def _get_text_from_rule(soup: BeautifulSoup, rule: dict) -> str:
    """
    Helper to safely get text using a rule (selector + index).
    Now handles both positive and negative indices.
    """
    selector = rule.get('selector')
    index = rule.get('index', 0)
    
    if not selector: 
        return ""
    
    elements = soup.select(selector)
    
    # Use a try/except block to safely access the element by index.
    # This works for positive indices (e.g., 0, 1, 2) and
    # negative indices (e.g., -1 for the last, -2 for the second to last).
    try:
        element = elements[index]
        raw_text = element.get_text(strip=True, separator=' ')
        clean_text = raw_text.replace('\ufffd', '')
        return " ".join(clean_text.split())
    except IndexError:
        # Catches cases where the index is out of bounds.
        return ""

# --- The Single, Authoritative Parsing Function ---

def parse_html_with_rules(soup: BeautifulSoup, rules: dict, genus_fallback: str) -> dict:
    """
    The single source of truth for applying text-based scraping rules.
    """
    name_rule = rules.get('name_selector', {})
    genus_rule = rules.get('genus_selector', {})

    full_name_text = _get_text_from_rule(soup, name_rule)
    full_genus_text = _get_text_from_rule(soup, genus_rule) or full_name_text
    
    full_name_text = correct_text_spacing(full_name_text)
    full_genus_text = correct_text_spacing(full_genus_text)

    name_method = name_rule.get('method', 'full_text')
    genus_method = genus_rule.get('method', 'full_text')
    
    name = _apply_method(full_name_text, name_method)
    
    # --- MODIFIED BLOCK ---
    # Scrape the raw genus, then determine the final genus using the fallback.
    scraped_genus_raw = _apply_method(full_genus_text, genus_method)
    final_genus = scraped_genus_raw or genus_fallback
    # --- END MODIFIED BLOCK ---

    author, taxonomic_status = None, []
    if full_name_text:
        tokens = full_name_text.split()
        for status in KNOWN_TAXONOMIC_STATUSES:
            if status in full_name_text:
                taxonomic_status.append(status)
        if tokens and tokens[-1].istitle() and len(tokens[-1]) > 1:
            author = tokens[-1].strip(string.punctuation)

    content_rule = rules.get('content_selector', {})
    body_content = ""
    selector = content_rule.get('selector')
    index = content_rule.get('index', 0)
    
    if selector:
        elements = soup.select(selector)
        if len(elements) > index:
            container = elements[index]
            body_content = format_body_content(markdownify(str(container)))

    citation_rule = rules.get('citation_selector', {})
    citations = [_get_text_from_rule(soup, citation_rule)] if citation_rule else []

    return {
        "name": name or "Unknown",
        "author": author,
        "taxonomic_status": list(set(taxonomic_status)),
        "genus": final_genus,
        "scraped_genus_raw": scraped_genus_raw, # Return raw value for comparison
        "body_content": body_content,
        "citations": [c for c in citations if c]
    }