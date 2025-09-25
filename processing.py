# mob-scraper/processing.py

import re
import yaml
import frontmatter

def format_body_content(markdown_text: str):
    """
    Cleans raw markdown scraped from HTML, creating well-structured headings and paragraphs.

    This function takes a string of messy markdown and applies a series of regex rules
    to reflow the text, correctly identify and format headings, and fix common spacing
    and punctuation issues. It is adapted from the robust implementation in your
    'missing_entries.py' script.

    Args:
        markdown_text: The raw markdown string to be cleaned.

    Returns:
        A cleaned, well-formatted markdown string.
    """
    if not markdown_text:
        return ""

    # Remove the initial '***' line often found in the source
    processed_text = re.sub(r'^\s*\*\*\*.*\n', '', markdown_text.strip(), count=1)
    # Normalize all whitespace to single spaces before processing
    processed_text = re.sub(r'\s+', ' ', processed_text)

    # Helper function to create a standard replacer for headings
    def create_replacer(heading_str):
        return lambda match: f"\n\n{heading_str}\n\n"

    # Special replacer for 'Holotype' to include the symbol
    def create_holotype_replacer(match):
        symbol = match.group(1) or ""
        return f"\n\n### Holotype {symbol.strip()}\n\n"

    # A dictionary of regex patterns and their corresponding replacement functions
    rules = {
        re.compile(r'\*Taxonomic notes?[\.:]?\*', re.IGNORECASE): create_replacer("### Taxonomic Notes"),
        re.compile(r'\*Paratypes?[\.:]?\*', re.IGNORECASE): create_replacer("### Paratype"),
        re.compile(r'\*Holotype[\.:]?\*\s*(♂|♀)?', re.IGNORECASE): create_holotype_replacer,
        re.compile(r'\*Diagnosis[\.:]?\*', re.IGNORECASE): create_replacer("### Diagnosis"),
        re.compile(r'\*Geographical range[\.:]?\*', re.IGNORECASE): create_replacer("### Geographical range"),
        re.compile(r'\*Habitat preference[\.:]?\*', re.IGNORECASE): create_replacer("### Habitat preference"),
        re.compile(r'\*Biology[\.:]?\*', re.IGNORECASE): create_replacer("### Biology"),
    }

    for pattern, replacer in rules.items():
        processed_text = pattern.sub(replacer, processed_text)
    
    # Add line breaks after sentences ending with a period followed by a capital letter
    processed_text = re.sub(r'([a-z]{2,})\.\s+(?=[A-Z])', r'\1.\n\n', processed_text)
    # Clean up stray periods that are now at the start of a line
    processed_text = re.sub(r'\n\s*\.\s*', '\n', processed_text)
    # Consolidate multiple newlines into a maximum of two
    processed_text = re.sub(r'\n{3,}', '\n\n', processed_text)
    
    return processed_text.strip()

def clean_citation_frontmatter(fm_string: str):
    """
    Repairs malformed 'citations' blocks in a raw frontmatter string.

    This function uses regex to find and fix common YAML errors in the citations
    field, such as unquoted multi-line strings. It's adapted from the logic
    in your 'clean-citations.py' script.

    Args:
        fm_string: The raw string of the frontmatter block.

    Returns:
        The repaired frontmatter string, or the original if no repairs were needed.
    """

    def replacer(match):
        """This function is called by re.sub for the matched citation block."""
        raw_citation_block = match.group(1)
        
        # If the block contains '*', it's likely a malformed multi-line string
        if "*" in raw_citation_block:
            lines = raw_citation_block.split('\n')
            # Clean up lines, removing list markers and extra whitespace
            clean_lines = [re.sub(r'^\s*-\s*', '', line).strip() for line in lines if not line.startswith('citations:')]
            full_citation_text = " ".join(filter(None, clean_lines))
            # Collapse whitespace and escape single quotes for YAML
            full_citation_text = " ".join(full_citation_text.split()).replace("'", "''")
            # Rebuild the block as a valid YAML list item
            return f"citations:\n- '{full_citation_text}'"
        else:
            # If it's malformed but has no '*', replace with an empty list
            return "citations: []"

    # This regex captures the 'citations:' block until the next key or the end of the string
    regex_pattern = r'(^citations:[\s\S]*?)(?=\n^\w+:|\Z)'
    
    new_fm_string, num_replacements = re.subn(
        regex_pattern, 
        replacer, 
        fm_string, 
        count=1, 
        flags=re.MULTILINE
    )

    if num_replacements > 0:
        return new_fm_string
    return fm_string # Return original if no changes were made