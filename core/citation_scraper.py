from bs4 import BeautifulSoup
from markdownify import markdownify

def scrape_and_format_citation(soup: BeautifulSoup, rule: dict):
    """
    Selects a parent container, removes the initial species name, and then
    intelligently combines the remaining fragmented HTML into a clean,
    formatted markdown citation string.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object for the page.
        rule (dict): The selector rule pointing to the parent container.

    Returns:
        str: The formatted citation string, or None if not found.
    """
    selector = rule.get('selector')
    index = rule.get('index', 0)
    if not selector:
        return None

    try:
        elements = soup.select(selector)
        container_tag = elements[index]
    except IndexError:
        return None

    # --- THIS IS THE FIX ---
    # Instead of using the unreliable .copy() method, we create a new,
    # clean BeautifulSoup object from the string representation of the
    # selected tag. This is a much safer approach.
    if not container_tag:
        return None
    container = BeautifulSoup(str(container_tag), 'html.parser')

    # In this specific citation pattern, the first bold tag is the
    # species name and should be excluded from the citation itself.
    first_b = container.find('b')
    if first_b:
        first_b.decompose()

    # Convert the remaining HTML within the container to markdown.
    md_text = markdownify(str(container), strip=['a', 'p'])

    # Clean up extra whitespace, newlines, and artifacts
    clean_text = " ".join(md_text.strip().split())
    
    return clean_text