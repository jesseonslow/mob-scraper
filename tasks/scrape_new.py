# tasks/scrape_new.py
import re
import importlib
import random
from itertools import groupby
import frontmatter
from pathlib import Path
from bs4 import BeautifulSoup

import config
from file_system import (
    get_master_php_urls, index_entries_by_url, index_entries_by_slug,
    save_markdown_file
)
from scraper import SpeciesScraper
from tasks.utils import get_contextual_data
from selector_finder import run_interactive_selector_finder
from reclassification_manager import load_reclassified_urls


def _is_data_valid(scraped_data: dict):
    """
    Performs a comprehensive quality check and returns a list of failing fields.
    """
    failures = []
    name = scraped_data.get("name")
    genus = scraped_data.get("genus")
    body = scraped_data.get("body_content", "")
    author = scraped_data.get("author")

    if (not name or name == "Unknown" or '\ufffd' in name or
            name in config.KNOWN_TAXONOMIC_STATUSES or name == author):
        failures.append('name')
    
    if not genus or genus == "Unknown":
        failures.append('genus')

    if len(body.strip()) < 50:
        failures.append('content')

    return failures


def _create_file_from_data(entry_data: dict, scraped_data: dict, book_name: str):
    """
    Creates a markdown file from pre-scraped data.
    """
    url = entry_data['url']
    neighbor_data = entry_data['neighbor_data']
    final_genus = scraped_data.get('genus')
    
    name_for_slug = scraped_data['name'].lower().replace('sp. ', 'sp-').replace(' ', '-').replace('?', '').replace('.', '')
    slug = f"{final_genus.lower().replace(' ', '-')}-{name_for_slug}"
    filepath = config.MARKDOWN_DIR / f"{slug}.md"
    
    if filepath.exists():
        print(f"  -> ℹ️ SKIPPING: File already exists at {filepath.name}")
        return

    new_metadata = {
        'name': scraped_data['name'],
        'author': scraped_data['author'],
        'legacy_url': url,
        'book': book_name,
        'family': neighbor_data.get('family'),
        'subfamily': neighbor_data.get('subfamily'),
        'tribe': neighbor_data.get('tribe'),
        'genus': final_genus,
        'taxonomic_status': scraped_data.get('taxonomic_status', []),
        'plates': scraped_data['plates'],
        'genitalia': scraped_data['genitalia'],
        'misc_images': scraped_data['misc_images'],
        'citations': scraped_data.get('citations', [])
    }
    
    post = frontmatter.Post(content=scraped_data.get('body_content', ''))
    post.metadata = {k: v for k, v in new_metadata.items() if v}
    
    save_markdown_file(post, filepath)


def run_scrape_new(generate_files=False, interactive=False):
    """
    The main function for the 'scrape_new' task, with a more robust interactive workflow.
    """
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
    
    def get_book_from_url(url):
        match = re.search(r'/part-([\d-]+)/', url)
        if match:
            part_str = match.group(1)
            book_num = '15-16' if part_str == '15-16' else part_str.split('-')[0]
            return config.BOOK_WORD_MAP.get(book_num, "Unknown")
        return "Unknown"

    books_to_skip = set()
    
    if interactive:
        print("\n--- Interactive Mode: Checking for missing or invalid rules ---")
        
        entries_by_book = {}
        for entry in creatable_entries:
            book_name = get_book_from_url(entry['url'])
            if book_name not in entries_by_book: entries_by_book[book_name] = []
            entries_by_book[book_name].append(entry)
        
        for book_name, entries_for_book in entries_by_book.items():
            if book_name in books_to_skip or book_name == "Unknown":
                continue

            entry_to_test = entries_for_book[-1]
            url_to_test = entry_to_test['url']
            context_genus = entry_to_test['neighbor_data'].get('genus') if entry_to_test['context_type'] == 'species' else entry_to_test['neighbor_data'].get('name')

            if book_name not in config.BOOK_SCRAPING_RULES:
                print(f"\n[!] No rules found for book: '{book_name}'.")
                status = run_interactive_selector_finder(book_name, url_to_test, context_genus)
                if status == 'skip_book': books_to_skip.add(book_name)
                elif status in ['reclassified', 'rules_updated']: importlib.reload(config)
                continue

            print(f"\nVerifying rules for book: '{book_name}'...")
            relative_path = url_to_test.replace(config.LEGACY_URL_BASE, "")
            php_path = config.PHP_ROOT_DIR / relative_path
            with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            scraper = SpeciesScraper(soup, book_name, context_genus)
            scraped_data = scraper.scrape_all()
            failed_fields = _is_data_valid(scraped_data)

            if failed_fields:
                print(f"  -> [!] Low confidence for {Path(url_to_test).name}. Failing fields: {failed_fields}")
                existing_rules = config.BOOK_SCRAPING_RULES.get(book_name, {})
                status = run_interactive_selector_finder(
                    book_name, url_to_test, context_genus, existing_rules=existing_rules, failed_fields=failed_fields
                )
                if status == 'skip_book': books_to_skip.add(book_name)
                elif status in ['reclassified', 'rules_updated']: importlib.reload(config)
            else:
                print("  -> ✅ Rules seem to be working correctly.")
        
        print("\n--- Interactive session complete. ---")
    
    if generate_files:
        reclassified_urls = load_reclassified_urls()
        
        print(f"\n--- Live Run: Generating files... ---")
        created_count = 0
        for entry in creatable_entries:
            url = entry['url']
            if url in reclassified_urls: continue

            book_name = get_book_from_url(url)
            if book_name in books_to_skip:
                continue

            if book_name in config.BOOK_SCRAPING_RULES:
                relative_path = url.replace(config.LEGACY_URL_BASE, "")
                php_path = config.PHP_ROOT_DIR / relative_path
                if not php_path.exists(): continue

                with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                
                context_genus = entry['neighbor_data'].get('genus') if entry['context_type'] == 'species' else entry['neighbor_data'].get('name')
                scraper = SpeciesScraper(soup, book_name, context_genus)
                scraped_data = scraper.scrape_all()
                
                failed_fields = _is_data_valid(scraped_data)
                
                if not failed_fields:
                    _create_file_from_data(entry, scraped_data, book_name)
                    created_count += 1
                else:
                    # --- NEW ENHANCED DEBUGGING OUTPUT ---
                    print(f"\n-> [ERROR] Skipping {Path(url).name}: Scraped data is invalid.")
                    print(f"   - Book: {book_name}")
                    print(f"   - Failed Fields: {', '.join(failed_fields)}")
                    print("   --- Scraped Data ---")
                    print(f"   Name:     '{scraped_data.get('name')}'")
                    print(f"   Genus:    '{scraped_data.get('genus')}'")
                    print(f"   Author:   '{scraped_data.get('author')}'")
                    content_snippet = scraped_data.get('body_content', '').strip().replace('\n', ' ')
                    print(f"   Content:  '{content_snippet[:100]}...'")
                    print("   --------------------")
            else:
                print(f"  -> SKIPPING {Path(url).name}: No rules defined for book '{book_name}'.")
        print(f"\n✨ Live run complete. Generated {created_count} file(s).")
    
    if not generate_files and not interactive:
        print("\n--- Dry Run Summary ---")
        print(f"✅ Found {len(creatable_entries)} entries that can be generated.")
        print(f"⚠️ Found {len(warnings)} entries that are missing context.")