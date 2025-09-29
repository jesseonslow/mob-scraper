# tasks/interactive_cli.py

import argparse
from urllib.request import urlopen
from bs4 import BeautifulSoup
import config
from reclassification_manager import add_reclassified_url
from parser import parse_html_with_rules
from file_system import update_config_file, create_markdown_file
from processing import correct_text_spacing
from selector_finder import suggest_selectors
from tasks.utils import get_book_from_url

def _get_user_choice(data_type, suggestions, soup):
    """Displays suggestions and gets the user's choice for a rule and method."""
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
        return chosen_rule, 'full_text'

    elements = soup.select(chosen_rule['selector'])
    raw_text = ""
    if elements and len(elements) > chosen_rule['index']:
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

def run_interactive_session(entry_data, existing_rules=None, failed_fields=None):
    """The main interactive loop for defining and verifying scraper rules."""
    sample_url = entry_data['url']
    book_name = get_book_from_url(sample_url)
    context_genus = entry_data['neighbor_data'].get('genus') if entry_data['context_type'] == 'species' else entry_data['neighbor_data'].get('name')

    print(f"\n--- Launching Interactive Session for book: '{book_name}' ---")
    
    try:
        relative_path = sample_url.replace(config.LEGACY_URL_BASE, "")
        php_path = config.PHP_ROOT_DIR / relative_path
        html = php_path.read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        print(f"Error loading source for '{sample_url}': {e}"); return 'error'

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
            parsed_data = parse_html_with_rules(soup, existing_rules, context_genus)
            lookup_key = 'body_content' if field == 'content' else ('citations' if field == 'citation' else field)
            extracted_text = parsed_data.get(lookup_key, "")
            if isinstance(extracted_text, list): extracted_text = " ".join(extracted_text)
            
            print(f"Current Rule: {existing_rules.get(field_key)}")
            print(f"Extracted Text: \"{extracted_text[:200]}\"")
            
            while True:
                choice = input("Is this correct? [Y/n/s]: ").lower()
                if choice in ('y', ''):
                    confirmed_rules[field_key] = existing_rules[field_key]
                    break
                elif choice == 'n':
                    rule, method = _get_user_choice(field, suggestions.get(field, []), soup)
                    if rule:
                        confirmed_rules[field_key] = {'selector': rule['selector'], 'index': rule['index'], 'method': method}
                    break
                elif choice == 's':
                    if field_key in confirmed_rules: del confirmed_rules[field_key]
                    print(f"  -> Rule for '{field}' will be removed."); break
        else:
            rule, method = _get_user_choice(field, suggestions.get(field, []), soup)
            if rule:
                confirmed_rules[field_key] = {'selector': rule['selector'], 'index': rule['index'], 'method': method}

    if confirmed_rules and confirmed_rules != existing_rules:
        print("\n" + "="*25 + "\n--- FINAL CONFIRMATION ---")
        final_data = parse_html_with_rules(soup, confirmed_rules, context_genus)
        print(f"Applying new rules produces:\n  - Name: {final_data.get('name')}\n  - Genus: {final_data.get('genus')}\n  - Author: {final_data.get('author')}")
        body_snippet = final_data.get('body_content', '').strip().replace('\n', ' ')
        print(f"  - Content:  {body_snippet[:100]}...")
        print("="*25)

        choice = input("\nSave these new rules to config.py? [Y/n]: ").lower().strip()
        if choice in ('y', 'yes', ''):
            update_config_file(book_name, confirmed_rules)
            save_choice = input("Rules saved. Save this scraped file now? [Y/n]: ").lower().strip()
            if save_choice in ('y', 'yes', ''):
                create_markdown_file(entry_data, final_data, book_name)
                return 'rules_updated_and_file_saved'
            return 'rules_updated'
    
    print("\nAborted. No changes have been made.")
    return 'no_change'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactively find CSS selectors for the MoB scraper.")
    parser.add_argument("book_name", help="The name of the book (e.g., 'eleven').")
    parser.add_argument("sample_url", help="A full URL to a sample page from the book.")
    parser.add_argument("--genus_fallback", help="Optional fallback genus for testing.", default="TestGenus")
    args = parser.parse_args()
    
    # This standalone mode won't be able to save a file, as it lacks the full 'entry_data'
    run_interactive_session({'url': args.sample_url, 'neighbor_data': {}, 'context_type': 'genus'}, existing_rules=None, failed_fields=None)