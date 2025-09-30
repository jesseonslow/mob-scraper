import re
import string
from bs4 import BeautifulSoup
from markdownify import markdownify
from soupsieve.util import SelectorSyntaxError
from processing import format_body_content, correct_text_spacing, replace_ocr_symbols
from config import KNOWN_TAXONOMIC_STATUSES
from citation_scraper import scrape_and_format_citation

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
        if not elements or abs(index) >= len(elements):
            return ""
        element = elements[index]
        raw_text = element.text
        return " ".join(raw_text.split())
    except (SelectorSyntaxError, IndexError):
        return ""


def parse_html_with_rules(soup: BeautifulSoup, rules: dict, genus_fallback: str) -> dict:
    """
    The single source of truth for applying text-based scraping rules.
    """
    name_rule = rules.get('name_selector', {})
    genus_rule = rules.get('genus_selector', {})
    author_rule = rules.get('author_selector', {})

    full_name_text = _get_text_from_rule(soup, name_rule)
    full_genus_text = _get_text_from_rule(soup, genus_rule) if genus_rule else full_name_text
    full_author_text = _get_text_from_rule(soup, author_rule)
    
    combined_text_for_status_check = (full_name_text + " " + full_genus_text).lower()
    taxonomic_status = []
    for status in KNOWN_TAXONOMIC_STATUSES:
        if status in combined_text_for_status_check:
            taxonomic_status.append(status)

    name_method = name_rule.get('method', 'full_text')
    
    name = _apply_method(full_name_text, name_method)
    scraped_genus = _apply_method(full_genus_text, genus_rule.get('method', 'full_text'))
    author = _apply_method(full_author_text, author_rule.get('method', 'full_text'))

    is_complex_string = len(full_name_text.split()) > 1
    
    if name_method == 'full_text' and not author_rule and is_complex_string:
        temp_text = full_name_text
        
        for status in KNOWN_TAXONOMIC_STATUSES:
            if status in temp_text.lower():
                if status not in taxonomic_status:
                    taxonomic_status.append(status)
                temp_text = re.sub(re.escape(status), '', temp_text, flags=re.IGNORECASE)

        tokens = temp_text.strip().split()
        found_author = None
        try:
            if '&' in tokens:
                amp_index = tokens.index('&')
                # Check if there are capitalized words on both sides
                if amp_index > 0 and amp_index < len(tokens) - 1:
                    author1 = tokens[amp_index - 1]
                    author2 = tokens[amp_index + 1]
                    if author1.istitle() and author2.istitle():
                        found_author = f"{author1} & {author2}"
                        # Remove the full author string for further processing
                        temp_text = temp_text.replace(found_author, '').strip()
        except ValueError:
            pass # '&' not in tokens

        # Fallback to single author detection if multi-author not found
        if not found_author:
            last_word = tokens[-1].strip(string.punctuation)
            if (last_word.istitle() or last_word.isupper()) and len(last_word) > 1:
                found_author = last_word
                temp_text = temp_text.replace(found_author, '').strip()
        
        remaining_tokens = temp_text.strip().split()
        if len(remaining_tokens) == 1:
            name = remaining_tokens[0]
        elif len(remaining_tokens) > 1:
            scraped_genus = remaining_tokens[0]
            name = ' '.join(remaining_tokens[1:])
        if found_author:
            author = found_author

    final_genus = scraped_genus or genus_fallback

    if author:
        author_string = author
        for status in KNOWN_TAXONOMIC_STATUSES:
            if status in author_string.lower():
                if status not in taxonomic_status:
                    taxonomic_status.append(status)
                author_string = re.sub(re.escape(status), '', author_string, flags=re.IGNORECASE)
        author = author_string.strip()
    
    # --- THIS IS THE FIX ---
    # The "Holloway" overrides are now inside a safeguard to prevent them
    # from overwriting an author that has already been found.
    if not author:
        if "sp. n." in [s.lower() for s in taxonomic_status] or "nom. nov." in [s.lower() for s in taxonomic_status]:
            author = "Holloway"
        if name == 'sp.':
            author = 'Holloway'
        if name and name.startswith('sp. ') and name.split(' ')[-1].isdigit():
            author = 'Holloway'

    if name and name.strip().lower() == 'sp':
        name = 'sp.'
    
    if name:
        name = name.replace('\ufffd', '').strip('\'" ')
    if final_genus:
        final_genus = final_genus.replace('\ufffd', '').strip('\'" ')
    if author:
        author = author.replace('\ufffd', '').strip('\'" ., ')

    content_rule = rules.get('content_selector', {})
    body_content = ""
    if content_rule:
        selector = content_rule.get('selector')
        if selector:
            try:
                elements = soup.select(selector)
                if elements:
                    if rules.get('book_name') == 'thirteen':
                         html_content = "".join(str(p) for p in elements)
                         body_content = format_body_content(markdownify(html_content))
                    else:
                        index = content_rule.get('index', 0)
                        container = elements[index]
                        body_content = format_body_content(markdownify(str(container)))
            except (SelectorSyntaxError, IndexError):
                body_content = ""

    if rules.get('book_name') == 'thirteen':
        body_content = replace_ocr_symbols(body_content)
    
    citation_rule = rules.get('citation_selector', {})
    citations = []
    if citation_rule:
        citation_text = None
        if citation_rule.get('method') == 'build_citation_string':
            citation_text = scrape_and_format_citation(soup, citation_rule)
        else:
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