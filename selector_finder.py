# selector_finder.py

import argparse
import re
from pathlib import Path
from urllib.request import urlopen
from bs4 import BeautifulSoup

# --- Configuration ---
CONFIG_PATH = Path("./config.py")
RULES_VAR_NAME = "BOOK_SCRAPING_RULES"

def suggest_selectors(soup):
    """
    Analyzes the HTML and suggests potential selectors for different data types.
    This uses a set of heuristics to find likely candidates.
    """
    suggestions = {
        'name': [],
        'genus': [],
        'citation': [],
        'content': []
    }
    
    # Heuristic 1: Bold tags often contain names/genera.
    for tag in soup.find_all('b'):
        text = " ".join(tag.get_text(strip=True).split())
        if 2 < len(text) < 100:
            suggestions['name'].append(('b', text))
            # Nested <i> tags are strong candidates for genus.
            if nested_i := tag.find('i'):
                text_i = " ".join(nested_i.get_text(strip=True).split())
                suggestions['genus'].append(('b i', text_i))

    # Heuristic 2: Paragraphs and spans with significant text are content candidates.
    for tag in soup.find_all(['p', 'span']):
        text = " ".join(tag.get_text(strip=True).split())
        if len(text) > 200: # Look for reasonably long text blocks
             selector = 'p[align="justify"]' if tag.name == 'p' else 'span'
             suggestions['content'].append((selector, text[:150] + "...")) # Show a preview
        # Heuristic 3: Text with years (e.g., 1931, 2005) are likely citations.
        if re.search(r'\b(19|20)\d{2}\b', text) and len(text) < 200:
            selector = 'p[align="justify"] > span' if tag.name == 'span' else 'p'
            suggestions['citation'].append((selector, text))
            
    return suggestions

def get_user_choice(data_type, suggestions):
    """
    Displays suggestions to the user and gets their confirmed choice.
    """
    print(f"\n--- Finding Selector for: {data_type.upper()} ---")
    
    # Display suggestions
    for i, (selector, text) in enumerate(suggestions, 1):
        print(f"[{i}] Selector: '{selector}'")
        print(f"    Extracts: \"{text}\"")
    
    print("\n[c] Enter a custom selector")
    print("[s] Skip this selector")
    
    while True:
        choice = input(f"Enter your choice for '{data_type}': ").lower()
        if choice == 's':
            return None
        if choice == 'c':
            custom_selector = input("Enter custom CSS selector: ")
            # You would add validation here in a real app
            return custom_selector
        try:
            if 1 <= int(choice) <= len(suggestions):
                return suggestions[int(choice) - 1][0]
        except ValueError:
            pass
        print("Invalid choice, please try again.")

def update_config_file(book_name, confirmed_selectors):
    """
    Safely reads, updates, and writes back the configuration file.
    """
    print(f"\nUpdating '{CONFIG_PATH}' with new rules for book '{book_name}'...")

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    try:
        # Find the start and end of the rules dictionary
        start_index = -1
        end_index = -1
        brace_count = 0
        in_dict = False

        for i, line in enumerate(lines):
            if line.strip().startswith(f"{RULES_VAR_NAME} = {{"):
                start_index = i
                in_dict = True
            
            if in_dict:
                brace_count += line.count('{')
                brace_count -= line.count('}')
                if brace_count == 0:
                    end_index = i
                    break
        
        if start_index == -1 or end_index == -1:
            print("Error: Could not find the BOOK_SCRAPING_RULES dictionary in config.py.")
            return

        # Format the new rule entry
        new_rule_lines = [f"    '{book_name}': {{\n"]
        for key, value in confirmed_selectors.items():
            new_rule_lines.append(f"        '{key}': '{value}',\n")
        new_rule_lines.append("    },\n")

        # Create the new file content
        new_lines = lines[:start_index + 1] # Keep the opening line
        new_lines.extend(new_rule_lines)
        # Add back old lines, skipping any previous entry for this book
        in_old_book_entry = False
        for line in lines[start_index + 1 : end_index]:
            if f"'{book_name}':" in line:
                in_old_book_entry = True
            if '}' in line and in_old_book_entry:
                in_old_book_entry = False
                continue
            if not in_old_book_entry:
                new_lines.append(line)
        new_lines.append(lines[end_index]) # Keep the closing brace
        new_lines.extend(lines[end_index + 1:])

        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print("✅ Config file updated successfully!")

    except Exception as e:
        print(f"❌ Failed to update config file: {e}")

def run_interactive_selector_finder(book_name, sample_url):
    """The core logic of the selector finder, now as a callable function."""
    print(f"--- Launching Interactive Selector Finder for book: '{book_name}' ---")
    print(f"Using sample URL: {sample_url}")
    try:
        html = urlopen(sample_url).read()
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return

    suggestions = suggest_selectors(soup)
    confirmed = {}

    fields_to_find = ['name', 'genus', 'citation', 'content']
    
    for field in fields_to_find:
        selector = get_user_choice(field, suggestions.get(field, []))
        if selector:
            # This is a simplification. For content/citation, you might also need to save the 'extraction_method'
            # For now, we'll just save the selector.
            confirmed[f"{field}_selector"] = selector
    
    if confirmed:
        update_config_file(book_name, confirmed)
        # After updating, we need to dynamically reload the config.
        # This is an advanced technique, but crucial for this workflow.
        print("Configuration updated. You may need to restart the main script for changes to take effect in this session.")
    else:
        print("No selectors were chosen. Exiting interactive session.")

def main():
    parser = argparse.ArgumentParser(description="Interactively find and save CSS selectors for the MoB scraper.")
    parser.add_argument("book_name", help="The name of the book (e.g., 'eleven').")
    parser.add_argument("sample_url", help="A full URL to a sample page from the book.")
    args = parser.parse_args()
    
    run_interactive_selector_finder(args.book_name, args.sample_url)

if __name__ == "__main__":
    main()