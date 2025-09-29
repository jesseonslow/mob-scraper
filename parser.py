import re
import string
from bs4 import BeautifulSoup
from markdownify import markdownify
from processing import format_body_content, correct_text_spacing
from config import KNOWN_TAXONOMIC_STATUSES

def _apply_method(text: str, method: str) -> str:
    """Applies a specific post-processing method to the extracted text."""
    tokens = text.split()
    if not tokens: return ""

    if method.startswith('position_'):
        try:
            pos = int(method.split('_')[1])
            index = pos - 1 if pos > 0 else pos
            return tokens[index] if 0 <= index < len(tokens) else ""
        except (ValueError, IndexError):
            return ""
    elif method == 'first_word':
        return tokens[0]
    elif method == 'last_word':
        for token in reversed(tokens):
            clean_token = token.strip(string.punctuation).lower()
            if clean_token not in KNOWN_TAXONOMIC_STATUSES:
                return token.strip(string.punctuation)
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
    return text

def _get_text_from_rule(soup: BeautifulSoup, rule: dict) -> str:
    """Helper to safely get text using a rule (selector + index)."""
    selector = rule.get('selector')
    index = rule.get('index', 0)
    
    if not selector: 
        return ""
    
    try:
        elements = soup.select(selector)
        if index >= len(elements) or index < -len(elements):
            return ""
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
    author_rule = rules.get('author_selector', {})

    # --- Step 1: Extract all raw text blocks based on defined rules ---
    full_name_text = _get_text_from_rule(soup, name_rule)
    full_genus_text = _get_text_from_rule(soup, genus_rule) if genus_rule else full_name_text
    full_author_text = _get_text_from_rule(soup, author_rule)
    
    # --- Step 2: Always check for taxonomic status in the main name string ---
    taxonomic_status = []
    for status in KNOWN_TAXONOMIC_STATUSES:
        if status in full_name_text.lower():
            taxonomic_status.append(status)

    # --- Step 3: Scrape individual fields ---
    name_method = name_rule.get('method', 'full_text')
    
    # Use specific methods if they exist
    name = _apply_method(full_name_text, name_method)
    scraped_genus = _apply_method(full_genus_text, genus_rule.get('method', 'full_text'))
    author = _apply_method(full_author_text, author_rule.get('method', 'full_text'))

    is_complex_string = len(full_name_text.split()) > 1
    
    # If using the 'full_text' heuristic, refine the extracted values
    if name_method == 'full_text' and not author_rule:
        temp_text = full_name_text
        for status in taxonomic_status:
            temp_text = re.sub(re.escape(status), '', temp_text, flags=re.IGNORECASE)

        tokens = temp_text.strip().split()
        found_author = None
        if tokens:
            last_word = tokens[-1].strip(string.punctuation)
            if (last_word.istitle() or last_word.isupper()) and len(last_word) > 1:
                found_author = last_word
                temp_text = temp_text.replace(found_author, '').strip()
        
        remaining_tokens = temp_text.strip().split()
        if len(remaining_tokens) == 1:
            # Case 1: Only a single word remains (e.g., "sp.")
            name = remaining_tokens[0]
        elif len(remaining_tokens) > 1:
            # Case 2: Multiple words remain (e.g., "Genus species")
            scraped_genus = remaining_tokens[0]
            name = ' '.join(remaining_tokens[1:])
        if found_author:
            author = found_author
            
    # --- Step 4 (THE FIX): Apply the "sp. n." override at the end ---
    if "sp. n." in [s.lower() for s in taxonomic_status]:
        author = "Holloway"

    if name and name.strip().lower() == 'sp':
        name = 'sp.'

    if name == 'sp.':
        author = 'Holloway'
    
    final_genus = scraped_genus or genus_fallback

    # --- Step 5: Process content and citations ---
    content_rule = rules.get('content_selector', {})
    body_content = ""
    selector = content_rule.get('selector')
    
    if selector:
        elements = soup.select(selector)
        if elements:
            try:
                index = content_rule.get('index', 0)
                container = elements[index]
                body_content = format_body_content(markdownify(str(container)))
            except IndexError:
                body_content = ""
    
    citation_rule = rules.get('citation_selector', {})
    citations = []
    if citation_rule:
        citation_text = _get_text_from_rule(soup, citation_rule)
        if citation_text:
            citations.append(citation_text)

    return {
        "name": name or "Unknown",
        "author": author,
        "taxonomic_status": list(set(taxonomic_status)),
        "genus": final_genus,
        "scraped_genus_raw": scraped_genus,
        "body_content": body_content,
        "citations": [c for c in citations if c]
    }