import argparse
from urllib.request import urlopen
from bs4 import BeautifulSoup
import config
from reclassification_manager import add_reclassified_url
from core.parser import parse_html_with_rules
from core.file_system import update_config_file
from core.processing import correct_text_spacing
from core.selector_finder import suggest_selectors
from tasks.utils import get_book_from_url
from models import Species
from core.scraper import scrape_images_and_labels

def _get_user_choice(data_type, suggestions, soup):
    """Displays suggestions and gets the user's choice for a rule and method."""
    print(f"\n--- Finding Rule for: {data_type.upper()} ---")
    
    print("Step 1: Choose a selector and index.")
    for i, (rule, text) in enumerate(suggestions, 1):
        print(f"[{i}] Selector: '{rule['selector']}' (Match #{rule['index'] + 1}) -> Extracts: \"{text}\"")
    print("\n[c] Enter a custom selector")

    if data_type == 'citation':
        print("[b] Use the citation builder (for fragmented citations)")
        print("[n] No citations on this page")
    print("[s] Skip this rule for now")
    
    chosen_rule = None
    while not chosen_rule:
        choice = input(f"Enter your choice for '{data_type}' selector: ").lower()
        
        if choice == 's' or (data_type == 'citation' and choice == 'n'):
            return None, None

        if data_type == 'citation' and choice == 'b':
            print("\n--- Citation Builder ---")
            print("Enter the selector for the PARENT element containing all citation fragments.")
            custom_selector = input("Enter parent CSS selector: ")
            try:
                custom_index = int(input("Enter the match number (e.g., 1 for the first): "))
                rule = {'selector': custom_selector, 'index': custom_index - 1}
                return rule, 'build_citation_string'
            except ValueError:
                print("Invalid number. Aborting.")
                return None, None

        if choice == 'c':
            custom_selector = input("Enter custom CSS selector: ")
            try:
                custom_index = int(input("Enter the match number (e.g., 1 for the first, 2 for the second): "))
                chosen_rule = {'selector': custom_selector, 'index': custom_index - 1}
                break
            except ValueError:
                print("Invalid number. Defaulting to the first match (index 0).")
                chosen_rule = {'selector': custom_selector, 'index': 0}
                break

        try:
            if 1 <= int(choice) <= len(suggestions):
                chosen_rule = suggestions[int(choice) - 1][0]
        except (ValueError, IndexError):
            print("Invalid choice, please try again.")

    if not chosen_rule:
        return None, None

    if data_type == 'content':
        return chosen_rule, 'full_text'

    elements = soup.select(chosen_rule['selector'])
    raw_text = ""
    if elements and 0 <= chosen_rule['index'] < len(elements):
        element = elements[chosen_rule['index']]
        raw_text = " ".join(element.get_text(strip=True, separator=' ').split())
        raw_text = correct_text_spacing(raw_text)
    else:
        print(f"  -> WARNING: Selector '{chosen_rule['selector']}' with index {chosen_rule['index']} found no match.")

    print(f"\nRule (selector: '{chosen_rule['selector']}', index: {chosen_rule['index']}) extracted: \"{raw_text}\"")
    print("Step 2: How should this text be processed?")
    print("[1] Use the full text (intelligent parser will attempt to split it)")
    print("[2] Get word by its position in the text")
    if data_type == 'citation':
        print("[3] Build citation from mixed content")
    print("[p] Paste the target word to generate a reliable method")
    
    while True:
        method_choice = input("Enter your choice for method: ").lower()
        if method_choice == '1':
            return chosen_rule, 'full_text'
        elif method_choice == '2':
            while True:
                try:
                    # The typo in the prompt has also been corrected.
                    pos_input = input("Enter position (e.g., 1 for first, 2 for second, -1 for last): ")
                    pos = int(pos_input)
                    return chosen_rule, f'position_{pos}'
                except ValueError:
                    print("Invalid number. Please enter an integer.")
        elif data_type == 'citation' and method_choice == '3':
            return chosen_rule, 'build_citation_string'
        elif method_choice == 'p':
            target_word = input(f"Paste the exact word you want to extract from \"{raw_text}\": ").strip()
            if target_word in raw_text:
                tokens = raw_text.split()
                try:
                    idx = tokens.index(target_word)
                    position = idx + 1
                    print(f"  -> Detected '{target_word}' at position {position}.")
                    return chosen_rule, f'position_{position}'
                except ValueError:
                    print("Could not find the exact word as a distinct token. Please try another method.")
            else:
                print(f"The word '{target_word}' was not found in the extracted text.")


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
    
    while True:
        current_rules = existing_rules.copy() if existing_rules else {}
        confirmed_rules = {}

        fields_to_find = ['name', 'genus', 'author', 'citation', 'content']
        
        for field in fields_to_find:
            field_key = f"{field}_selector"
            
            if field == 'author':
                temp_data = parse_html_with_rules(soup, confirmed_rules, context_genus)
                if temp_data.get('author') == 'Holloway':
                    print("\n--- Verifying Rule for: AUTHOR ---")
                    print("  -> Author automatically set to 'Holloway' based on species name rule. Skipping.")
                    continue
            
            if failed_fields and field not in failed_fields and field_key in current_rules:
                print(f"--- Verifying Rule for: {field.upper()} ---")
                print("  -> Rule assumed to be correct. Skipping.")
                confirmed_rules[field_key] = current_rules[field_key]
                continue
            
            if field_key in current_rules:
                print(f"\n--- Verifying Rule for: {field.upper()} ---")
                parsed_data = parse_html_with_rules(soup, current_rules, context_genus)
                lookup_key = 'body_content' if field == 'content' else ('citations' if field == 'citation' else field)
                extracted_text = parsed_data.get(lookup_key, "")
                if isinstance(extracted_text, list): extracted_text = " ".join(extracted_text)
                
                print(f"Current Rule: {current_rules.get(field_key)}")
                print(f"Extracted Text: \"{extracted_text[:200]}\"")
                
                choice = 'n'
                if not failed_fields or field not in failed_fields:
                    choice = input("Is this correct? [Y/n/s]: ").lower()

                if choice in ('y', ''):
                    confirmed_rules[field_key] = current_rules[field_key]
                elif choice == 'n':
                    rule, method = _get_user_choice(field, suggestions.get(field, []), soup)
                    if rule and method:
                        confirmed_rules[field_key] = {'selector': rule['selector'], 'index': rule['index'], 'method': method}
                elif choice == 's':
                    if field_key in confirmed_rules: del confirmed_rules[field_key]
                    print(f"  -> Rule for '{field}' will be removed.")
            else:
                rule, method = _get_user_choice(field, suggestions.get(field, []), soup)
                if rule and method:
                    confirmed_rules[field_key] = {'selector': rule['selector'], 'index': rule['index'], 'method': method}
        
        if not confirmed_rules or confirmed_rules == existing_rules:
            print("\nAborted. No changes have been made.")
            return 'no_change'

        print("\n" + "="*25 + "\n--- RE-VALIDATING NEW RULES ---")
        # Step 1: Get text data using the new rules
        final_data = parse_html_with_rules(soup, confirmed_rules, context_genus)
        
        # Step 2: Get image data
        book_number = config.BOOK_NUMBER_MAP.get(book_name)
        plates, genitalia, misc_images = scrape_images_and_labels(soup, book_name, book_number)
        
        # Step 3: Combine them into the final data object
        final_data.update({
            "plates": plates,
            "genitalia": genitalia,
            "misc_images": misc_images
        })

        new_failed_fields = is_data_valid(final_data)

        if not new_failed_fields:
            print("✅ Confidence check passed!")
            print(f"Applying new rules produces:\n  - Name: {final_data.get('name')}\n  - Genus: {final_data.get('genus')}\n  - Author: {final_data.get('author')}")
            
            body_snippet = final_data.get('body_content', '').strip()
            print("  - Content Preview:")
            print("---")
            print(f"{body_snippet[:200]}...")
            print("---")
            print("="*25)

            choice = input("\nSave these new rules to config.py? [Y/n]: ").lower().strip()
            if choice in ('y', 'yes', ''):
                update_config_file(book_name, confirmed_rules)
                save_choice = input("Rules saved. Save this scraped file now? [Y/n]: ").lower().strip()
                if save_choice in ('y', 'yes', ''):
                    create_markdown_file(entry_data, final_data, book_name)
                    return 'rules_updated_and_file_saved'
                return 'rules_updated'
            else:
                print("\nAborted. No changes have been made.")
                return 'no_change'
        else:
            print(f"❌ Confidence check FAILED. The new rules are still producing invalid data.")
            print(f"   Failing fields: {new_failed_fields}")
            retry_choice = input("Would you like to try again? [Y/n]: ").lower().strip()
            if retry_choice in ('n', 'no'):
                print("\nAborted. No changes have been made.")
                return 'no_change'
            else:
                existing_rules = confirmed_rules
                failed_fields = new_failed_fields