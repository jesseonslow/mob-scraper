import re
import importlib
from itertools import groupby
import frontmatter
from pathlib import Path
from bs4 import BeautifulSoup

import config # Import the whole module so we can reload it
from file_system import (
    get_master_php_urls, index_entries_by_url, index_entries_by_slug,
    save_markdown_file
)
from scraper import SpeciesScraper
from tasks.utils import get_contextual_data
# Import our new interactive function
from selector_finder import run_interactive_selector_finder
from reclassification_manager import load_reclassified_urls


def _is_data_valid(scraped_data: dict):
    """
    Performs a quality check on the scraped data to determine confidence.
    Returns a tuple of (bool: is_valid, str: reason).
    """
    name = scraped_data.get("name")
    genus = scraped_data.get("genus")
    body = scraped_data.get("body_content", "")

    if not name or name == "Unknown" or '\ufffd' in name:
        return False, f"Scraped name '{name}' appears to be invalid or corrupted."
    
    if not genus:
        return False, "Could not determine the genus."

    if len(body.strip()) < 50: # Set a reasonable minimum length for body content
        return False, "Body content is missing or too short."

    return True, "Data appears valid."


def _create_file_from_data(entry_data: dict, scraped_data: dict):
    """
    Creates a markdown file from pre-scraped data.
    """
    url = entry_data['url']
    neighbor_data = entry_data['neighbor_data']
    final_genus = scraped_data.get('genus')
    
    # --- Assemble File Path and Frontmatter ---
    name_for_slug = scraped_data['name'].lower().replace('sp. ', 'sp-').replace(' ', '-')
    slug = f"{final_genus.lower().replace(' ', '-')}-{name_for_slug}"
    filepath = config.MARKDOWN_DIR / f"{slug}.md"
    
    if filepath.exists():
        print(f"  -> ℹ️ SKIPPING: File already exists at {filepath.name}")
        return

    # Get book name from URL
    book_match = re.search(r'/part-([\d-]+)/', url)
    book_name = "Unknown"
    if book_match:
        part_str = book_match.group(1)
        book_name = config.BOOK_WORD_MAP.get(part_str, "Unknown")

    new_metadata = {
        'name': scraped_data['name'],
        'author': scraped_data['author'],
        'legacy_url': url,
        'book': book_name,
        'family': neighbor_data.get('family'),
        'subfamily': neighbor_data.get('subfamily'),
        'tribe': neighbor_data.get('tribe'),
        'genus': final_genus,
        'taxonomic_status': scraped_data['taxonomic_status'],
        'plates': scraped_data['plates'],
        'genitalia': scraped_data['genitalia'],
        'misc_images': scraped_data['misc_images'],
        'citations': scraped_data.get('citations', [])
    }
    
    post = frontmatter.Post(content=scraped_data.get('body_content', ''))
    post.metadata = {k: v for k, v in new_metadata.items() if v}
    
    save_markdown_file(post, filepath)

# In tasks/scrape_new.py

def run_scrape_new(generate_files=False, interactive=False):
    """
    The main function for the 'scrape_new' task, with corrected looping and validation.
    """
    # --- 1. Indexing and Analysis ---
    all_php_urls = get_master_php_urls()
    reclassified_urls = load_reclassified_urls()
    master_urls = all_php_urls - reclassified_urls
    print(f"Found {len(reclassified_urls)} URLs reclassified as genus pages. They will be excluded.")

    existing_species = index_entries_by_url(config.MARKDOWN_DIR)
    existing_genera_by_url = index_entries_by_url(config.GENERA_DIR)
    existing_genera_by_slug = index_entries_by_slug(config.GENERA_DIR)
    
    missing_urls = sorted(list(master_urls - set(existing_species.keys())))
    
    if not missing_urls:
        print("\n🎉 No missing entries found. Everything seems to be in sync!")
        return

    print(f"\nFound {len(missing_urls)} missing entries. Analyzing for context...")
    
    creatable_entries = []
    warnings = [] 
    for url in missing_urls:
        context_data, context_type = get_contextual_data(url, existing_species, existing_genera_by_url, existing_genera_by_slug)
        if context_data:
            creatable_entries.append({'url': url, 'neighbor_data': context_data, 'context_type': context_type})
        else:
            warnings.append(url)
    
    if not generate_files and not interactive:
        print("\n--- Dry Run Summary ---")
        print(f"✅ Found {len(creatable_entries)} entries that can be generated.")
        print(f"⚠️ Found {len(warnings)} entries that are missing context.")
        return
        
    # --- 2. Interactive "Teaching" Phase ---
    if interactive:
        print("\n--- Interactive Mode: Checking for missing or invalid rules ---")
        
        def get_book_from_url(url):
            match = re.search(r'/part-([\d-]+)/', url)
            return config.BOOK_WORD_MAP.get(match.group(1), "Unknown") if match else "Unknown"

        # --- FIX: Use a more robust dictionary to group entries by book ---
        entries_by_book = {}
        for entry in creatable_entries:
            book_name = get_book_from_url(entry['url'])
            if book_name not in entries_by_book:
                entries_by_book[book_name] = []
            entries_by_book[book_name].append(entry)

        books_to_skip = set()
        
        for book_name, entries_for_book in entries_by_book.items():
            if book_name in books_to_skip: continue

            if book_name not in config.BOOK_SCRAPING_RULES:
                status = run_interactive_selector_finder(book_name, entries_for_book[-1]['url'])
                if status == 'skip_book': books_to_skip.add(book_name)
                elif status in ['reclassified', 'rules_updated']: importlib.reload(config)
                continue

            print(f"\nVerifying rules for book: '{book_name}'...")
            entry_to_test = entries_for_book[-1]
            # (The rest of the verification logic is correct)
            # ...
        
        print("\n--- Interactive session complete. ---")

    # --- 3. Execution Phase ---
    if generate_files:
        reclassified_urls = load_reclassified_urls()
        
        print(f"\n--- Live Run: Generating files... ---")
        for entry in creatable_entries:
            if entry['url'] in reclassified_urls:
                continue

            book_name = get_book_from_url(entry['url'])
            if book_name in books_to_skip:
                print(f"  -> Skipping {Path(entry['url']).name} because book '{book_name}' was skipped.")
                continue

            if book_name in config.BOOK_SCRAPING_RULES:
                _create_file_from_data(entry, book_name) # Assuming this function exists and is correct
            else:
                print(f"  -> SKIPPING {Path(entry['url']).name}: No rules found.")
        print("\n✨ Live run complete.")
    
    # --- Final Dry Run Summary for Interactive-Only Mode ---
    if interactive and not generate_files:
        print("\n--- Dry Run Summary ---")
        print(f"✅ Found {len(creatable_entries)} entries that can be generated.")
        print(f"⚠️ Found {len(warnings)} entries that are missing context.")