import re
import importlib
import random
import time
from itertools import groupby
import frontmatter
from pathlib import Path
from bs4 import BeautifulSoup

import config
from file_system import (
    get_master_php_urls, index_entries_by_url, index_entries_by_slug,
    create_markdown_file
)
from scraper import SpeciesScraper
from tasks.utils import get_contextual_data, get_book_from_url, is_data_valid
from tasks.interactive_cli import run_interactive_session
from reclassification_manager import load_reclassified_urls

def run_scrape_new(generate_files=False, interactive=False, force=False):
    """
    The main function for the 'scrape_new' task, with a more robust interactive workflow.
    """
    random.seed(time.time())
    all_php_urls = get_master_php_urls()
    reclassified_urls = load_reclassified_urls()
    master_urls = all_php_urls - reclassified_urls
    print(f"Found {len(reclassified_urls)} URLs reclassified as genus pages. They will be excluded.")

    existing_species = index_entries_by_url(config.SPECIES_DIR)
    existing_genera_by_url = index_entries_by_url(config.GENERA_DIR)
    existing_genera_by_slug = index_entries_by_slug(config.GENERA_DIR)
    
    missing_urls = sorted(list(master_urls - set(existing_species.keys())))
    
    if not missing_urls:
        print("\n🎉 No missing entries found. Everything seems to be in sync!")
        return

    print(f"\nFound {len(missing_urls)} missing entries. Analyzing for context...")
    
    creatable_entries = []
    uncreatable_entries = [] 
    for url in missing_urls:
        context_data, context_type = get_contextual_data(url, existing_species, existing_genera_by_url, existing_genera_by_slug)
        if context_data:
            creatable_entries.append({'url': url, 'neighbor_data': context_data, 'context_type': context_type})
        else:
            uncreatable_entries.append(url)

    books_to_skip = set()
    
    if interactive:
        print("\n--- Interactive Mode: Checking for missing or invalid rules ---")
        
        keyfunc = lambda x: get_book_from_url(x['url'])
        sorted_entries = sorted(creatable_entries, key=keyfunc)
        entries_by_book = {k: list(v) for k, v in groupby(sorted_entries, key=keyfunc)}
        
        all_books_to_check = [book for book in entries_by_book.keys() if book != "Unknown" and book not in config.BOOKS_TO_SKIP_INTERACTIVE]
        num_books_to_sample = min(len(all_books_to_check), 5)
        
        if num_books_to_sample > 0:
            sampled_book_names = random.sample(all_books_to_check, num_books_to_sample)
            print(f"\nFound {len(all_books_to_check)} books with missing entries. Randomly sampling {len(sampled_book_names)} of them for verification.")
        else:
            sampled_book_names = []
            print("\nNo books with missing entries to check in interactive mode.")

        for book_name in sampled_book_names:
            if book_name in books_to_skip:
                continue

            entry_to_test = random.choice(entries_by_book[book_name])
            url_to_test = entry_to_test['url']
            context_genus = entry_to_test['neighbor_data'].get('genus') if entry_to_test['context_type'] == 'species' else entry_to_test['neighbor_data'].get('name')

            if book_name not in config.BOOK_SCRAPING_RULES:
                print(f"\n[!] No rules found for book: '{book_name}'.")
                status = run_interactive_session(entry_to_test, existing_rules=None, failed_fields=None)
                if status == 'skip_book': books_to_skip.add(book_name)
                elif status in ['reclassified', 'rules_updated', 'rules_updated_and_file_saved']: importlib.reload(config)
                continue

            print(f"\nVerifying rules for book: '{book_name}'...")
            relative_path = url_to_test.replace(config.LEGACY_URL_BASE, "")
            php_path = config.PHP_ROOT_DIR / relative_path
            with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            scraper = SpeciesScraper(html_content, book_name, context_genus)
            scraped_data = scraper.scrape_all()
            failed_fields = is_data_valid(scraped_data)

            if failed_fields:
                print(f"  -> [!] Low confidence for {Path(url_to_test).name}. Failing fields: {failed_fields}")
                existing_rules = config.BOOK_SCRAPING_RULES.get(book_name, {})
                status = run_interactive_session(
                    entry_to_test, existing_rules=existing_rules, failed_fields=failed_fields
                )
                if status == 'skip_book': books_to_skip.add(book_name)
                elif status in ['reclassified', 'rules_updated', 'rules_updated_and_file_saved']: importlib.reload(config)
            else:
                print("  -> ✅ Rules seem to be working correctly.")
        
        print("\n--- Interactive session complete. ---")
    
    if generate_files:
        if force:
            print("\n--- Live Run (FORCE MODE): Generating all creatable files, ignoring validation... ---")
        else:
            print(f"\n--- Live Run: Generating files... ---")
        
        created_count = 0
        skipped_count = 0
        for entry in creatable_entries:
            url = entry['url']
            book_name = get_book_from_url(url)
            if book_name in books_to_skip: continue
            
            if book_name not in config.BOOK_SCRAPING_RULES:
                print(f"  -> SKIPPING {Path(url).name}: No rules defined for book '{book_name}'.")
                continue

            relative_path = url.replace(config.LEGACY_URL_BASE, "")
            php_path = config.PHP_ROOT_DIR / relative_path
            if not php_path.exists(): continue

            with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            context_genus = entry['neighbor_data'].get('genus') if entry['context_type'] == 'species' else entry['neighbor_data'].get('name')
            scraper = SpeciesScraper(html_content, book_name, context_genus)
            scraped_data = scraper.scrape_all()
            
            if force:
                if create_markdown_file(entry, scraped_data, book_name):
                    created_count += 1
            else:
                failed_fields = is_data_valid(scraped_data)
                if not failed_fields:
                    if create_markdown_file(entry, scraped_data, book_name):
                        created_count += 1
                else:
                    skipped_count += 1
                    print(f"\n-> [SKIPPED] {Path(url).name}: Scraped data is invalid.")
                    print(f"   - Failed Fields: {', '.join(failed_fields)}")

        remaining_count = len(missing_urls) - created_count
        final_message = f"\n✨ Live run complete. Generated {created_count} file(s)."
        if skipped_count > 0:
            final_message += f" Skipped {skipped_count} file(s) due to validation errors."
        if remaining_count > 0:
            final_message += f" {remaining_count} missing files remain."
        print(final_message)
    
    if not generate_files and not interactive:
        print("\n--- Dry Run Summary ---")
        print(f"✅ Found {len(creatable_entries)} entries that can be generated.")
        print(f"⚠️ Found {len(uncreatable_entries)} entries that are missing context.")