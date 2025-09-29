# markdown_formatter.py

import mdformat

def format_markdown_text(markdown_text: str) -> str:
    """
    Uses the mdformat library to clean up and standardize a markdown string.

    This is excellent for fixing common stylistic and spacing issues, such as
    inconsistent spacing around italic/bold tags and punctuation.

    Args:
        markdown_text (str): The raw markdown text to be formatted.

    Returns:
        str: The cleaned and formatted markdown text.
    """
    if not markdown_text:
        return ""

    try:
        # Use mdformat.text() to format the string.
        # The `wrap="no"` option prevents the formatter from changing line wrapping.
        options = {"wrap": "no"}
        formatted_text = mdformat.text(markdown_text, options=options)
        return formatted_text
    except Exception as e:
        print(f"  -> WARNING: mdformat failed to process text. Returning original. Error: {e}")
        return markdown_text