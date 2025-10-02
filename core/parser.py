# core/parser.py

import re
import string
from bs4 import BeautifulSoup
from markdownify import markdownify
from soupsieve.util import SelectorSyntaxError
from .processing import format_body_content, replace_ocr_symbols
from config import KNOWN_TAXONOMIC_STATUSES
from .citation_scraper import scrape_and_format_citation

# --- PRIVATE HELPER FUNCTIONS ---

def _get_text_from_rule(soup: BeautifulSoup, rule: dict) -> str:
    """Helper to safely get text using a rule (selector + index)."""
    selector = rule.get('selector')
    index = rule.get('index', 0)
    
    if not selector: 
        return ""
    
    try:
        elements = soup.select(selector)
        if not elements or abs(index) >= len(elements):
            return ""
        element = elements[index]
        raw_text = element.text
        return " ".join(raw_text.split())
    except (SelectorSyntaxError, IndexError):
        return ""

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
    # Other methods remain unchanged
    elif method == 'first_word':
        return tokens[0]
    elif method == 'last_word':
        for token in reversed(tokens):
            clean_token = token.strip(string.punctuation).lower()
            if clean_token not in KNOWN_TAXONOMIC_STATUSES:
                return token.strip(string.punctuation)
        return ""
    return text

def _find_taxonomic_statuses(full_name_text: str, full_genus_text: str) -> list:
    """Finds all known taxonomic statuses in the provided text blocks."""
    statuses = []
    combined_text = (full_name_text + " " + full_genus_text).lower()
    for status in KNOWN_TAXONOMIC_STATUSES:
        if status in combined_text:
            statuses.append(status)
    return statuses

def _split_complex_name_string(text: str, existing_statuses: list) -> dict:
    """
    Intelligently splits a single string that may contain a genus, name,
    author, and taxonomic statuses.
    """
    result = {'name': '', 'author': '', 'scraped_genus': '', 'taxonomic_status': existing_statuses}
    
    # Remove any known statuses from the text to simplify parsing
    for status in KNOWN_TAXONOMIC_STATUSES:
        if status in text.lower():
            if status not in result['taxonomic_status']:
                result['taxonomic_status'].append(status)
            text = re.sub(re.escape(status), '', text, flags=re.IGNORECASE)

    tokens = text.strip().split()
    if not tokens:
        return result

    # Find multi-word author like "Author & Author"
    found_author = None
    if '&' in tokens:
        try:
            amp_index = tokens.index('&')
            if amp_index > 0 and amp_index < len(tokens) - 1:
                author1 = tokens[amp_index - 1]
                author2 = tokens[amp_index + 1]
                if author1.istitle() and author2.istitle():
                    found_author = f"{author1} & {author2}"
        except ValueError:
            pass # Should not happen, but good practice

    # Fallback to single-word author if multi-word not found
    if not found_author:
        last_word = tokens[-1].strip(string.punctuation)
        if (last_word.istitle() or last_word.isupper()) and len(last_word) > 1:
            found_author = last_word

    # Assign author and remove it from the text
    if found_author:
        result['author'] = found_author
        text = text.replace(found_author, '').strip()

    # The remainder is the genus and name
    remaining_tokens = text.strip().split()
    if len(remaining_tokens) == 1:
        result['name'] = remaining_tokens[0]
    elif len(remaining_tokens) > 1:
        result['scraped_genus'] = remaining_tokens[0]
        result['name'] = ' '.join(remaining_tokens[1:])
        
    return result

def _determine_author(author: str, name: str, taxonomic_statuses: list) -> str:
    """Cleans an author string and applies specific overrides."""
    final_author = author
    
    # Clean any statuses that were part of the author string
    if final_author:
        for status in KNOWN_TAXONOMIC_STATUSES:
            if status in final_author.lower():
                final_author = re.sub(re.escape(status), '', final_author, flags=re.IGNORECASE)
        final_author = final_author.strip()

    # If no author was found, apply overrides
    if not final_author:
        lower_statuses = [s.lower() for s in taxonomic_statuses]
        is_new_species = "sp. n." in lower_statuses or "nom. nov." in lower_statuses
        is_sp_format = name == 'sp.' or (name and name.startswith('sp. ') and name.split(' ')[-1].isdigit())

        if is_new_species or is_sp_format:
            final_author = "Holloway"
            
    return final_author

def _parse_content(soup: BeautifulSoup, rules: dict) -> str:
    """Extracts and formats the main body content from the page."""
    content_rule = rules.get('content_selector', {})
    if not content_rule or not content_rule.get('selector'):
        return ""
        
    try:
        elements = soup.select(content_rule['selector'])
        if not elements:
            return ""
        
        book_name = rules.get('book_name')
        if book_name == 'thirteen':
            html_content = "".join(str(p) for p in elements)
            body_content = format_body_content(markdownify(html_content))
        else:
            index = content_rule.get('index', 0)
            container = elements[index]
            body_content = format_body_content(markdownify(str(container)))
        
        return replace_ocr_symbols(body_content) if book_name == 'thirteen' else body_content

    except (SelectorSyntaxError, IndexError):
        return ""

def _parse_citations(soup: BeautifulSoup, rules: dict) -> list:
    """Extracts citation strings from the page."""
    citation_rule = rules.get('citation_selector', {})
    if not citation_rule:
        return []

    method = citation_rule.get('method')
    if method == 'build_citation_string':
        citation_text = scrape_and_format_citation(soup, citation_rule)
    else:
        citation_text = _get_text_from_rule(soup, citation_rule)

    return [citation_text] if citation_text else []


# --- MAIN ORCHESTRATOR FUNCTION ---

def parse_html_with_rules(soup: BeautifulSoup, rules: dict, genus_fallback: str) -> dict:
    """
    Orchestrates the parsing of a species page by applying text-based scraping rules
    and calling specialized helper functions.
    """
    # 1. Get raw text from rules
    name_rule = rules.get('name_selector', {})
    genus_rule = rules.get('genus_selector', {})
    author_rule = rules.get('author_selector', {})

    full_name_text = _get_text_from_rule(soup, name_rule)
    full_genus_text = _get_text_from_rule(soup, genus_rule) if genus_rule else ""
    full_author_text = _get_text_from_rule(soup, author_rule)
    
    # 2. Initial data extraction
    taxonomic_status = _find_taxonomic_statuses(full_name_text, full_genus_text)
    name = _apply_method(full_name_text, name_rule.get('method', 'full_text'))
    scraped_genus = _apply_method(full_genus_text, genus_rule.get('method', 'full_text'))
    author = _apply_method(full_author_text, author_rule.get('method', 'full_text'))

    # 3. Refine data if using the complex 'full_text' method on the name selector
    if name_rule.get('method') == 'full_text' and not author_rule and len(full_name_text.split()) > 1:
        split_result = _split_complex_name_string(full_name_text, taxonomic_status)
        name = split_result['name']
        author = split_result['author']
        scraped_genus = split_result['scraped_genus']
        taxonomic_status = split_result['taxonomic_status']

    # 4. Finalize genus and author
    final_genus = scraped_genus or genus_fallback
    final_author = _determine_author(author, name, taxonomic_status)

    # 5. Parse content and citations using dedicated helpers
    body_content = _parse_content(soup, rules)
    citations = _parse_citations(soup, rules)
    
    # 6. Final cleaning and assembly
    if name and name.strip().lower() == 'sp':
        name = 'sp.'
    
    return {
        "name": name.replace('\ufffd', '').strip('\'" ') if name else "Unknown",
        "author": final_author.replace('\ufffd', '').strip('\'" ., ') if final_author else None,
        "taxonomic_status": list(set(taxonomic_status)),
        "genus": final_genus.replace('\ufffd', '').strip('\'" ') if final_genus else "Unknown",
        "scraped_genus_raw": scraped_genus,
        "body_content": body_content,
        "citations": citations
    }