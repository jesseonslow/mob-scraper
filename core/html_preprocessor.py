# html_preprocessor.py

def remove_font_tags(html: str) -> str:
    """
    Removes potentially malformed <font> tags from a raw HTML string before
    it is parsed by BeautifulSoup. This is crucial for handling legacy
    Microsoft Frontpage HTML that can confuse the parser.

    This function is adapted from the HtmlCleanup library by Roderik Muit.
    
    Args:
        html (str): The raw HTML content.

    Returns:
        str: The HTML content with <font> tags removed.
    """
    # This simplified regex approach is safer than the original's complex
    # string manipulation and targets the specific issue of font tags.
    # It removes <font ...> and </font> tags without touching their content.
    import re
    
    # Remove opening font tags, e.g., <font face="Book Antiqua">
    html = re.sub(r'<font[^>]*>', '', html, flags=re.IGNORECASE)
    # Remove closing font tags
    html = re.sub(r'</font>', '', html, flags=re.IGNORECASE)
    
    return html