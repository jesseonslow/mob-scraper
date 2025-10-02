# core/citation_parser.py

import re

def _normalize_publication_for_matching(pub_string):
    """A shared function to create a consistent key for matching and grouping."""
    if not pub_string or pub_string == "N/A":
        return "uncategorized"
    # Convert to lowercase and remove all non-alphanumeric characters
    return re.sub(r'[^a-z0-9]', '', pub_string.lower())

def _parse_single_citation(citation_text, book_name, legacy_url, base_synonym=None):
    """
    Parses a single, complete citation string.
    """
    text = " ".join(citation_text.split())
    text = text.replace('*', '').strip()
    text = re.sub(r',\s*\.', ', ', text)
    text = re.sub(r'([a-zA-Z])\s+(\d{4})', r'\1, \2', text)
    text = re.sub(r'\s*,\s*', ', ', text)

    parsed = {
        "synonym": "N/A", "year": "N/A", "publication": "N/A",
        "pageref": "N/A", "comment": "N/A", "pattern": "Unrecognized",
        "original": citation_text, "canonical_url": legacy_url
    }

    short_form_match = re.search(r'^(.*?),\s*(\d{4}):\s*(.*)$', text)
    if base_synonym or (short_form_match and (len(text.split(',')) < 3 or 'sensu' in text.lower())):
        parsed["synonym"] = base_synonym if base_synonym else short_form_match.group(1)
        parsed["year"] = short_form_match.group(2)
        parsed["pageref"] = short_form_match.group(3)
        author_candidate = parsed["synonym"].split()[-1]
        
        if author_candidate.lower() != 'sensu' and author_candidate[0].isupper():
            parsed["publication"] = author_candidate
        elif 'sensu' in parsed["synonym"].lower():
             sensu_parts = parsed["synonym"].lower().split('sensu ')
             if len(sensu_parts) > 1:
                 parsed["publication"] = sensu_parts[1].strip().capitalize()
        parsed["pattern"] = "[SHORT_FORM]"
        return parsed

    remaining_text = text
    pattern_parts = []
    
    year_regex = r'(\[\d{4}\]\s*\d{4}(?:-\d{1,2})?|\d{4}-\d{4}|\d{4}-\d{1,2}|\d{4}\s*\(nec\s\d{4}\)|\d{4})'
    year_match = re.search(year_regex, remaining_text)
    if not year_match:
        return None 

    parsed["year"] = year_match.group(1)
    year_start_index, year_end_index = year_match.span(1)
    pre_year_part = remaining_text[:year_start_index]
    post_year_part = remaining_text[year_end_index:]

    parsed["synonym"] = pre_year_part.strip(' ,.') if not base_synonym else base_synonym
    pattern_parts.extend(["[SYNONYM]", "[YEAR]"])

    remaining_text = post_year_part.strip(' ,.')
    
    pageref_match = re.search(r'((?:\d+|[IVX]+)\s?:\s?[\d\s,\-]+\.?)$', remaining_text)
    if pageref_match and re.search(r'\d', pageref_match.group(1)):
        parsed["pageref"] = pageref_match.group(1).strip(' ,.')
        pattern_parts.append("[PAGEREF]")
        pub_end_index = pageref_match.start(1)
        parsed["publication"] = remaining_text[:pub_end_index].strip(' ,.')
    else:
        parsed["publication"] = remaining_text

    if parsed["publication"]:
        pattern_parts.append("[PUBLICATION]")

    parsed["pattern"] = ", ".join(pattern_parts)
    return parsed

def parse_citation(citation_text, book_name, legacy_url):
    """
    Top-level parser that handles splitting multiple citations.
    """
    if "habitat preference" in citation_text.lower() or not re.search(r'\d{4}', citation_text):
        return [{"pattern": "[INVALID CITATION]", "original": citation_text, "canonical_url": legacy_url}]

    if citation_text.count(';') > 1:
        parts = citation_text.split('; ')
        base_synonym = parts[0]
        parsed_list = []
        for part in parts[1:]:
            parsed = _parse_single_citation(part, book_name, legacy_url, base_synonym=base_synonym)
            if parsed:
                parsed_list.append(parsed)
        return parsed_list if parsed_list else None

    if '; ' in citation_text:
        synonym_part, rest_of_text = citation_text.split('; ', 1)
        parsed = _parse_single_citation(rest_of_text, book_name, legacy_url, base_synonym=synonym_part)
        return [parsed] if parsed else None

    parsed = _parse_single_citation(citation_text, book_name, legacy_url)
    return [parsed] if parsed else None


def format_citation(parsed):
    if not parsed or parsed.get("pattern") == "[INVALID CITATION]":
        return "N/A"

    synonym_parts = parsed["synonym"].split()
    formatted_synonym = f"*{' '.join(synonym_parts[:2])}* {' '.join(synonym_parts[2:])}".strip() if parsed["synonym"] != "N/A" else ""
    formatted_publication = f"*{parsed['publication']}*" if parsed["publication"] != "N/A" else ""
    formatted_comment = f"**{parsed['comment']}**" if parsed["comment"] != "N/A" else ""

    final_parts = [formatted_synonym, parsed["year"], formatted_publication, parsed["pageref"], formatted_comment]
    
    # Final validation to ensure no newlines leak through
    return ", ".join(filter(None, [part for part in final_parts if part and part != "N/A"])).replace('\n', ' ').replace('\r', '')