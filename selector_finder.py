# selector_finder.py

import argparse
import re
from pathlib import Path
from urllib.request import urlopen
from bs4 import BeautifulSoup
from reclassification_manager import add_reclassified_url
from parser import parse_html_with_rules
from file_system import update_config_file

# --- Configuration ---
CONFIG_PATH = Path("./config.py")
RULES_VAR_NAME = "BOOK_SCRAPING_RULES"

def suggest_selectors(soup):
    """
    Analyzes the HTML and suggests potential rules (selector + index) for different data types.
    """
    suggestions = { 'name': [], 'genus': [], 'citation': [], 'content': [] }
    
    # Heuristic 1: Bold tags for name and genus
    b_tags = soup.select('b')
    for i, tag in enumerate(b_tags):
        text = " ".join(tag.get_text(strip=True, separator=' ').split())
        rule = {'selector': 'b', 'index': i}
        if 2 < len(text) < 100:
            # Add the same reliable rule suggestion for both name and genus
            suggestions['name'].append((rule, text))
            suggestions['genus'].append((rule, text))

    # Heuristic 2: Paragraph tags for content and citation
    p_tags = soup.select('p')
    for i, tag in enumerate(p_tags):
        text = " ".join(tag.get_text(strip=True, separator=' ').split())
        rule = {'selector': 'p', 'index': i}
        if len(text) > 150:
             suggestions['content'].append((rule, text[:150] + "..."))
        if re.search(r'\b(19|20)\d{2}\b', text) and len(text) < 200:
            suggestions['citation'].append((rule, text))
            
    return suggestions

def get_user_choice(data_type, suggestions, soup):
    """
    Displays suggestions and gets the user's choice for a rule (selector + index) AND a method.
    Skips the method prompt for the 'content' field.
    """
    print(f"\n--- Finding Rule for: {data_type.upper()} ---")
    
    # --- Step 1: Choose a selector and index ---
    print("Step 1: Choose a selector and index.")
    for i, (rule, text) in enumerate(suggestions, 1):
        print(f"[{i}] Selector: '{rule['selector']}' (Match #{rule['index'] + 1}) -> Extracts: \"{text}\"")
    print("\n[c] Enter a custom selector")
    print("[s] Skip this rule")
    
    chosen_rule = None
    while not chosen_rule:
        choice = input(f"Enter your choice for '{data_type}' selector: ").lower()
        if choice == 's': return None, None
        if choice == 'c':
            custom_selector = input("Enter custom CSS selector: ")
            chosen_rule = {'selector': custom_selector, 'index': 0}
        try:
            if 1 <= int(choice) <= len(suggestions):
                chosen_rule = suggestions[int(choice) - 1][0]
        except (ValueError, IndexError):
            if not chosen_rule: print("Invalid choice, please try again.")

    # --- Step 2: Choose the Method (Conditional) ---
    
    # For body content, we always want the full text.
    if data_type == 'content':
        print(f"  -> Method for 'content' is always 'full_text'.")
        return chosen_rule, 'full_text'

    # For all other fields, show the method prompt.
    elements = soup.select(chosen_rule['selector'])
    raw_text = ""
    if len(elements) > chosen_rule['index']:
        element = elements[chosen_rule['index']]
        raw_text = " ".join(element.get_text(strip=True, separator=' ').split())

    print(f"\nRule (selector: '{chosen_rule['selector']}', index: {chosen_rule['index']}) extracted: \"{raw_text}\"")
    print("Step 2: How should this text be processed?")
    print("[1] Use the full text")
    print("[2] Get word by position (e.g., first, last)")
    print("[p] Paste the target word to generate a rule")
    
    while True:
        method_choice = input("Enter your choice for method: ").lower()
        if method_choice == '1':
            return chosen_rule, 'full_text'
        elif method_choice == '2':
            pos = int(input("Enter position (1 for first, 2 for second, -1 for last): "))
            return chosen_rule, f'position_{pos}'
        elif method_choice == 'p':
            target_word = input(f"Paste the exact word you want to extract from \"{raw_text}\": ")
            if target_word in raw_text:
                tokens = raw_text.split()
                if target_word in tokens:
                    if target_word.islower():
                        return chosen_rule, 'first_lowercase'
                    elif target_word.istitle():
                        return chosen_rule, 'first_titlecase'
                print("Could not generate a reliable rule. Please try another method.")
            else:
                print("Target word not found in extracted text.")

def run_interactive_selector_finder(book_name, sample_url, existing_rules=None):
    """
    The core logic of the selector finder, now using the unified parser for verification.
    """
    print(f"\n--- Launching Interactive Selector Finder for book: '{book_name}' ---")
    
    if not existing_rules:
        print(f"Analyzing sample URL: {sample_url}")
        print("This sample might be a genus/subfamily page. What would you like to do?")
        while True:
            choice = input(
                "[1] Proceed (define selectors for species in this book)\n"
                "[2] Reclassify this URL as a genus page\n"
                "[3] Skip this book for the rest of this session\n"
                "Your choice: "
            ).lower()
            if choice == '1': break
            elif choice == '2': add_reclassified_url(sample_url); return 'reclassified'
            elif choice == '3': print(f"  -> Skipping book '{book_name}'."); return 'skip_book'
            else: print("Invalid choice.")

    try:
        html = urlopen(sample_url).read()
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL: {e}"); return 'error'

    suggestions = suggest_selectors(soup)
    confirmed_rules = existing_rules.copy() if existing_rules else {}
    fields_to_find = ['name', 'genus', 'citation', 'content']
    
    for field in fields_to_find:
        field_key = f"{field}_selector"

        if existing_rules and failed_fields is not None and field not in failed_fields:
            print(f"--- Verifying Rule for: {field.upper()} ---")
            print("  -> Rule assumed to be correct. Skipping.")
            continue
        
        if existing_rules and field_key in existing_rules:
            print(f"\n--- Verifying Rule for: {field.upper()} ---")
            
            parsed_data = parse_html_with_rules(soup, existing_rules, "N/A")
            extracted_text = parsed_data.get(field)
            
            print(f"Current Rule: {existing_rules.get(field_key)}")
            if isinstance(extracted_text, list): extracted_text = " ".join(extracted_text)
            print(f"Extracted Text: \"{extracted_text[:200]}\"")
            
            while True:
                choice = input("Is this correct? [Y/n/s]: ").lower()
                if choice in ('y', ''):
                    confirmed_rules[field_key] = existing_rules[field_key]
                    break
                elif choice == 'n':
                    new_rule, new_method = get_user_choice(field, suggestions.get(field, []), soup)
                    if new_rule:
                        confirmed_rules[field_key] = {'selector': new_rule['selector'], 'index': new_rule['index']}
                        if new_method: confirmed_rules[field_key]['method'] = new_method
                    break
                elif choice == 's':
                    if field_key in confirmed_rules: del confirmed_rules[field_key]
                    print(f"  -> Rule for '{field}' will be removed.")
                    break
                else:
                    print("Invalid choice.")
        else:
            rule, method = get_user_choice(field, suggestions.get(field, []), soup)
            if rule:
                confirmed_rules[field_key] = {'selector': rule['selector'], 'index': rule['index']}
                if method:
                    confirmed_rules[field_key]['method'] = method

    if confirmed_rules and confirmed_rules != existing_rules:
        update_config_file(book_name, confirmed_rules)
        return 'rules_updated'
    else:
        print("\nNo changes made to rules.")
        return 'no_change'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactively find and save CSS selectors for the MoB scraper.")
    parser.add_argument("book_name", help="The name of the book (e.g., 'eleven').")
    parser.add_argument("sample_url", help="A full URL to a sample page from the book.")
    args = parser.parse_args()
    
    run_interactive_selector_finder(args.book_name, args.sample_url)