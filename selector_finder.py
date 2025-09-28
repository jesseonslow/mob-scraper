# selector_finder.py

import argparse
import re
import pprint
from pathlib import Path
from urllib.request import urlopen
from bs4 import BeautifulSoup
from reclassification_manager import add_reclassified_url
from parser import parse_html_with_rules
from file_system import update_config_file
from config import RULES_VAR_NAME
from processing import correct_text_spacing

def suggest_selectors(soup):
    """
    Analyzes the HTML and suggests potential rules (selector + index) for different data types.
    This version now generates more specific selectors for paragraph tags.
    """
    suggestions = { 'name': [], 'genus': [], 'citation': [], 'content': [] }
    
    # Heuristic 1: Bold tags for name and genus (remains simple)
    b_tags = soup.select('b')
    for i, tag in enumerate(b_tags):
        text = " ".join(tag.get_text(strip=True, separator=' ').split())
        text = correct_text_spacing(text)
        rule = {'selector': 'b', 'index': i}
        if 2 < len(text) < 100:
            suggestions['name'].append((rule, text))
            suggestions['genus'].append((rule, text))

    # Heuristic 2: Paragraph tags with enhanced selector generation
    processed_tags = set() # Track tags to avoid duplicate suggestions

    # Prioritize more specific selectors first
    candidate_selectors = [
        'p[align="justify"]',
        'p[style*="text-align:justify"]',
        'p' # Generic fallback
    ]

    for selector in candidate_selectors:
        matched_tags = soup.select(selector)
        for i, tag in enumerate(matched_tags):
            # Use the tag's object id to see if we've already processed it
            # under a more specific selector.
            if id(tag) in processed_tags:
                continue
            
            processed_tags.add(id(tag))
            
            text = " ".join(tag.get_text(strip=True, separator=' ').split())
            rule = {'selector': selector, 'index': i}

            # Add suggestions based on content heuristics
            if len(text) > 150:
                suggestions['content'].append((rule, text[:150] + "..."))
            if re.search(r'\b(19|20)\d{2}\b', text) and len(text) < 200:
                suggestions['citation'].append((rule, text))
            
    return suggestions

def get_user_choice(data_type, suggestions, soup):
    """
    Displays suggestions and gets the user's choice for a rule (selector + index) AND a method.
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

def run_interactive_selector_finder(book_name, sample_url, genus_fallback, existing_rules=None, failed_fields=None):
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
            
            parsed_data = parse_html_with_rules(soup, existing_rules, genus_fallback)
            
            lookup_key = 'body_content' if field == 'content' else ('citations' if field == 'citation' else field)
            extracted_text = parsed_data.get(lookup_key)
            
            print(f"Current Rule: {existing_rules.get(field_key)}")
            if isinstance(extracted_text, list): extracted_text = " ".join(extracted_text)

            if extracted_text:
                print(f"Extracted Text: \"{extracted_text[:200]}\"")
            else:
                print("Extracted Text: \"\" (None Found)")
            
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
        print("\n" + "="*25)
        print("--- FINAL CONFIRMATION ---")
        print("Applying the new rules to the sample URL produces the following data:")

        final_data = parse_html_with_rules(soup, confirmed_rules, genus_fallback)

        print(f"  - Name:     {final_data.get('name')}")
        
        final_genus = final_data.get('genus')
        raw_genus = final_data.get('scraped_genus_raw')

        print(f"  - Genus:    {final_genus}")
        if (raw_genus and genus_fallback and raw_genus.lower() != genus_fallback.lower()):
            print("  -> ⚠️  WARNING: Genus discrepancy found!")
            print(f"     Inherited Context: {genus_fallback}")
            print(f"     Scraped from Page: {raw_genus}")
        
        print(f"  - Author:   {final_data.get('author')}")
        citations = final_data.get('citations', [])
        print(f"  - Citations:{' '.join(citations) if citations else 'None'}")
        
        body_snippet = final_data.get('body_content', '').strip().replace('\n', ' ')
        print(f"  - Content:  {body_snippet[:100]}...")
        print("="*25)

        while True:
            choice = input("\nSave these new rules to config.py? [Y/n]: ").lower().strip()
            if choice in ('y', 'yes', ''):
                update_config_file(book_name, confirmed_rules)
                return 'rules_updated'
            elif choice in ('n', 'no'):
                print("Aborted. No changes have been saved.")
                return 'no_change'
            else:
                print("Invalid choice. Please enter 'y' or 'n'.")
    else:
        print("\nNo changes made to rules.")
        return 'no_change'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactively find and save CSS selectors for the MoB scraper.")
    parser.add_argument("book_name", help="The name of the book (e.g., 'eleven').")
    parser.add_argument("sample_url", help="A full URL to a sample page from the book.")
    parser.add_argument("--genus_fallback", help="Optional fallback genus for standalone testing.", default="TestGenus")
    args = parser.parse_args()
    
    run_interactive_selector_finder(args.book_name, args.sample_url, args.genus_fallback)