# tasks/interactive_cli.py

import argparse
from urllib.request import urlopen
from bs4 import BeautifulSoup
import config
from reclassification_manager import add_reclassified_url
from parser import parse_html_with_rules
from file_system import update_config_file
from processing import correct_text_spacing
from selector_finder import suggest_selectors

def _get_user_choice(data_type, suggestions, soup):
    """
    Displays suggestions and gets the user's choice for a rule and method.
    """
    print(f"\n--- Finding Rule for: {data_type.upper()} ---")
    
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

    if data_type == 'content':
        print(f"  -> Method for 'content' is always 'full_text'.")
        return chosen_rule, 'full_text'

    elements = soup.select(chosen_rule['selector'])
    raw_text = ""
    if len(elements) > chosen_rule['index']:
        element = elements[chosen_rule['index']]
        raw_text = " ".join(element.get_text(strip=True, separator=' ').split())
        raw_text = correct_text_spacing(raw_text)

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
                    if target_word.islower() or target_word.isdigit():
                        return chosen_rule, 'first_lowercase'
                    elif target_word.istitle():
                        return chosen_rule, 'first_titlecase'
                print("Could not generate a reliable rule. Please try another method.")
            else:
                print("Target word not found in extracted text.")


def run_interactive_session(book_name, sample_url, genus_fallback, existing_rules=None, failed_fields=None):
    """
    The main interactive loop for defining and verifying scraper rules.
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
        relative_path = sample_url.replace(config.LEGACY_URL_BASE, "")
        php_path = config.PHP_ROOT_DIR / relative_path
        if not php_path.exists():
            print(f"⚠️  Warning: Local PHP file not found at '{php_path}'. Falling back to live URL.")
            html = urlopen(sample_url).read()
        else:
            print(f"Reading from local file: {php_path}")
            html = php_path.read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        print(f"❌ Error loading source for '{sample_url}': {e}"); return 'error'

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
            # (UI logic for verifying/changing existing rules)
            pass # Abridged for brevity, this logic is the same as before
        else:
            rule, method = _get_user_choice(field, suggestions.get(field, []), soup)
            if rule:
                confirmed_rules[field_key] = {'selector': rule['selector'], 'index': rule['index']}
                if method:
                    confirmed_rules[field_key]['method'] = method

    if confirmed_rules and confirmed_rules != existing_rules:
        # (UI logic for final confirmation and saving)
        pass # Abridged for brevity, this logic is the same as before
    else:
        print("\nNo changes made to rules.")
        return 'no_change'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactively find CSS selectors for the MoB scraper.")
    parser.add_argument("book_name", help="The name of the book (e.g., 'eleven').")
    parser.add_argument("sample_url", help="A full URL to a sample page from the book.")
    parser.add_argument("--genus_fallback", help="Optional fallback genus for testing.", default="TestGenus")
    args = parser.parse_args()
    
    run_interactive_session(args.book_name, args.sample_url, args.genus_fallback)