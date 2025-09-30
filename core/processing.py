import re
import yaml
import frontmatter
from link_rewriter import rewrite_legacy_links
from markdown_formatter import format_markdown_text

def format_body_content(markdown_text: str):
    """
    Cleans raw markdown scraped from HTML, creating well-structured headings,
    paragraphs, rewriting legacy links, and applying final formatting.
    """
    if not markdown_text:
        return ""

    processed_text = re.sub(r'^\s*\*\*\*.*\n', '', markdown_text.strip(), count=1)
    processed_text = re.sub(r'\s+', ' ', processed_text)

    def create_replacer(heading_str):
        return lambda match: f"\n\n{heading_str}\n\n"

    # This replacer is now simpler; a more robust fix is applied later.
    def create_holotype_replacer(match):
        symbol = match.group(1) or ""
        return f"\n\n### Holotype {symbol.strip()}\n\n"

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
    
    processed_text = re.sub(r'([a-z]{2,})\.\s+(?=[A-Z])', r'\1.\n\n', processed_text)
    
    def format_paratypes(match):
        header = match.group(1)
        content = match.group(2).strip()
        if content.startswith(':') and ';' in content:
            content = content[1:].strip()
            list_items = [f"- {item.strip()}" for item in content.split(';')]
            return f"{header}\n\n" + "\n".join(list_items)
        return match.group(0)

    processed_text = re.sub(
        r'(### Paratypes\n\n|### Paratype\n\n)(.*?)(?=\n\n###|\Z)', 
        format_paratypes, processed_text, flags=re.DOTALL
    )

    # --- FIX: Holotype heading formatting ---
    # This regex finds a Holotype heading followed by a symbol on a new line
    # and moves the symbol up, removing the trailing period.
    processed_text = re.sub(r'(### Holotype)\s*\n\n(♂|♀)\.', r'\1 \2\n\n', processed_text)

    processed_text = re.sub(r'\n\s*\.\s*', '\n', processed_text)
    processed_text = re.sub(r'\n{3,}', '\n\n', processed_text)
    
    rewritten_text = rewrite_legacy_links(processed_text)
    final_text = format_markdown_text(rewritten_text)
    return final_text.strip()

def clean_citation_frontmatter(fm_string: str):
    """
    Repairs malformed 'citations' blocks in a raw frontmatter string.
    """
    def replacer(match):
        raw_citation_block = match.group(1)
        
        if "*" in raw_citation_block:
            lines = raw_citation_block.split('\n')
            clean_lines = [re.sub(r'^\s*-\s*', '', line).strip() for line in lines if not line.startswith('citations:')]
            full_citation_text = " ".join(filter(None, clean_lines))
            full_citation_text = " ".join(full_citation_text.split()).replace("'", "''")
            return f"citations:\n- '{full_citation_text}'"
        else:
            return "citations: []"

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
    return fm_string

def correct_text_spacing(text: str) -> str:
    """
    Applies a series of corrections to text extracted from HTML to fix
    common spacing issues.
    """
    if not text:
        return ""
    
    if '? ' in text:
        text = text.replace('? ', '?')
    
    return text

def replace_ocr_symbols(text: str) -> str:
    """
    Replaces OCR scanning errors for male (G) and female (E) symbols
    with the correct unicode characters (♂, ♀) for book thirteen.
    """
    if not text: return ""
    
    # --- FIX: More specific replacement logic ---
    # Handle successive symbols and symbols after numbers
    text = re.sub(r'(\d+)\s*GG\b', r'\1♂♂', text)
    text = re.sub(r'\bGG\b', '♂♂', text)
    text = re.sub(r'(\d+)\s*EE\b', r'\1♀♀', text)
    text = re.sub(r'\bEE\b', '♀♀', text)
    text = re.sub(r'(\d+)\s*G\b', r'\1♂', text)
    text = re.sub(r'(\d+)\s*E\b', r'\1♀', text)

    # Handle cases like "Holotype G" but not "G. Dulit"
    text = re.sub(r'(Holotype|Paratype|Paratypes)\s+G\b', r'\1 ♂', text)
    text = re.sub(r'(Holotype|Paratype|Paratypes)\s+E\b', r'\1 ♀', text)

    # Replace standalone G/E that are not followed by a period
    text = re.sub(r'\bG\b(?!\.)', '♂', text)
    text = re.sub(r'\bE\b(?!\.)', '♀', text)

    return text