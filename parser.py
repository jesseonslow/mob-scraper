import re
import string
from bs4 import BeautifulSoup
from markdownify import markdownify
from processing import format_body_content, correct_text_spacing
from config import KNOWN_TAXONOMIC_STATUSES

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
    # --- THIS IS THE CRITICAL FIX ---
    # The 'last_word' method is now smarter. It finds the last word that is
    # NOT a known taxonomic status, making it far more reliable.
    elif method == 'last_word':
        for token in reversed(tokens):
            # Clean the token and check if it's a known status word
            clean_token = token.strip(string.punctuation).lower()
            if clean_token not in KNOWN_TAXONOMIC_STATUSES:
                return token.strip(string.punctuation)
        return "" # Return empty if all words are statuses
    return text


def _get_text_from_rule(soup: BeautifulSoup, rule: dict) -> str:
    """Helper to safely get text using a rule (selector + index)."""
    selector = rule.get('selector')
    index = rule.get('index', 0)
    
    if not selector: 
        return ""
    
    try:
        elements = soup.select(selector)
        element = elements[index]
        raw_text = element.get_text(strip=True, separator=' ')
        clean_text = raw_text.replace('\ufffd', '')
        return " ".join(clean_text.split())
    except IndexError:
        return ""


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

    # --- ENHANCED LOGIC TO PREVENT MISIDENTIFICATION ---
    # 1. Extract Author and Status first
    author, taxonomic_status = None, []
    if full_name_text:
        if "sp. n." in full_name_text.lower():
            taxonomic_status.append("sp. n.")
            author = "Holloway"
        else:
            # Fallback to the old logic if not sp. n.
            tokens = full_name_text.split()
            for status in KNOWN_TAXONOMIC_STATUSES:
                if status in full_name_text.lower():
                    taxonomic_status.append(status)
            if tokens and (tokens[-1].istitle() or tokens[-1].isupper()) and len(tokens[-1]) > 1:
                author = tokens[-1].strip(string.punctuation)

    # 2. Apply methods to get the name and genus
    name_method = name_rule.get('method', 'full_text')
    genus_method = genus_rule.get('method', 'full_text')
    
    name = _apply_method(full_name_text, name_method)
    scraped_genus_raw = _apply_method(full_genus_text, genus_method)
    final_genus = scraped_genus_raw or genus_fallback

    # 3. Post-processing: If the extracted name is the same as the author, it's wrong.
    if name == author:
        # Attempt to find a better name, e.g., the second to last word
        text_without_author = full_name_text.replace(author, '').strip()
        name = _apply_method(text_without_author, name_method)

    content_rule = rules.get('content_selector', {})
    body_content = ""
    selector = content_rule.get('selector')
    index = content_rule.get('index', 0)
    
    if selector:
        elements = soup.select(selector)
        if rules.get('book_name') == 'thirteen':
             html_content = "".join(str(p) for p in elements)
             body_content = format_body_content(markdownify(html_content))
        elif elements:
            # Original logic for all other books
            container = elements[content_rule.get('index', 0)]
            body_content = format_body_content(markdownify(str(container)))

    citations = []

    return {
        "name": name or "Unknown",
        "author": author,
        "taxonomic_status": list(set(taxonomic_status)),
        "genus": final_genus,
        "scraped_genus_raw": scraped_genus_raw,
        "body_content": body_content,
        "citations": [c for c in citations if c]
    }