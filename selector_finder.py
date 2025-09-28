# selector_finder.py

import re
from processing import correct_text_spacing

def suggest_selectors(soup):
    """
    Analyzes the HTML and suggests potential rules (selector + index) for different data types.
    This function contains no user interaction logic.
    """
    suggestions = {'name': [], 'genus': [], 'citation': [], 'content': []}
    
    # Heuristic 1: Bold tags for name and genus
    b_tags = soup.select('b')
    for i, tag in enumerate(b_tags):
        text = " ".join(tag.get_text(strip=True, separator=' ').split())
        text = correct_text_spacing(text)
        rule = {'selector': 'b', 'index': i}
        if 2 < len(text) < 100:
            suggestions['name'].append((rule, text))
            suggestions['genus'].append((rule, text))

    # Heuristic 2: Paragraph tags for content and citations
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
            
            text = " ".join(tag.get_text(strip=True, separator=' ').split())
            rule = {'selector': selector, 'index': i}

            if len(text) > 150:
                suggestions['content'].append((rule, text[:150] + "..."))
            if re.search(r'\\b(19|20)\\d{2}\\b', text) and len(text) < 200:
                suggestions['citation'].append((rule, text))
            
    return suggestions