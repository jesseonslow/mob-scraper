# selector_finder.py

import re
from .processing import correct_text_spacing
from tasks.utils import get_book_from_url

def suggest_selectors(soup):
    """
    Analyzes the HTML and suggests potential rules (selector + index) for different data types.
    This function contains no user interaction logic.
    """
    suggestions = {'name': [], 'genus': [], 'author': [], 'citation': [], 'content': []}
    
    # Heuristic 1: Bold tags for name and genus
    b_tags = soup.select('b')
    for i, tag in enumerate(b_tags):
        text = " ".join(tag.get_text(strip=True, separator=' ').split())
        text = correct_text_spacing(text)
        rule = {'selector': 'b', 'index': i}
        if len(text) >= 2 and len(text) < 100:
            suggestions['name'].append((rule, text))
            suggestions['genus'].append((rule, text))
            if text.istitle() or (text.startswith('(') and text.endswith(')')):
                suggestions['author'].append((rule, text))

    # Heuristic 2: span tags
    span_tags = soup.select('span')
    for i, tag in enumerate(span_tags):
        # To avoid noise, only consider spans that contain a <b> tag or have short text
        text = " ".join(tag.get_text(strip=True, separator=' ').split())
        if (tag.find('b') or len(text) < 30) and (len(text) >= 2 and len(text) < 100):
            rule = {'selector': 'span', 'index': i}
            suggestions['name'].append((rule, text))
            suggestions['genus'].append((rule, text))
            if text.istitle() or (text.startswith('(') and text.endswith(')')):
                 suggestions['author'].append((rule, text))

    # Heuristic 3: Paragraph tags for content and citations
    processed_tags = set()
    candidate_selectors = [
        'p[align="justify"]',
        'p[style*="text-align:justify"]',
        'p'
    ]

    for selector in candidate_selectors:
        matched_tags = soup.select(selector)
        for i, tag in enumerate(matched_tags):
            if id(tag) in processed_tags:
                continue
            
            processed_tags.add(id(tag))
            
            text = " ".join(tag.get_text(strip=True).split())
            rule = {'selector': selector, 'index': i}

            if len(text) > 150:
                suggestions['content'].append((rule, text[:150] + "..."))
            if re.search(r'\\b(19|20)\\d{2}\\b', text) and len(text) < 200:
                suggestions['citation'].append((rule, text))
            
    return suggestions