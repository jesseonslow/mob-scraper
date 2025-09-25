import re
import frontmatter
from pathlib import Path
from bs4 import BeautifulSoup

from config import (
    PHP_ROOT_DIR, MARKDOWN_DIR, GENERA_DIR, LEGACY_URL_BASE,
    BOOK_WORD_MAP, BOOK_CONTENT_SELECTORS
)
from file_system import (
    get_master_php_urls, index_entries_by_url, index_entries_by_slug,
    save_markdown_file
)
from scraper import SpeciesScraper
from processing import format_body_content
# Import the new shared function
from tasks.utils import get_contextual_data

def _create_species_file(entry_data):
    """
    Handles the full scraping and file creation process for a single missing species.
    """
    url = entry_data['url']
    neighbor_data = entry_data['neighbor_data']
    
    relative_path = url.replace(LEGACY_URL_BASE, "")
    php_path = PHP_ROOT_DIR / relative_path
    if not php_path.exists():
        print(f"  -> ❌ SKIPPING: Source PHP file not found for {url}")
        return

    with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # --- Scrape Data using our modules ---
    book_match = re.search(r'/part-([\d-]+)/', url)
    book_name = "Unknown"
    if book_match:
        part_str = book_match.group(1)
        book_name = BOOK_WORD_MAP.get(part_str, "Unknown")
    
    genus_name = neighbor_data.get('genus') or neighbor_data.get('name')
    if not genus_name:
        print(f"  -> ❌ SKIPPING: Could not determine genus for {url}")
        return

    # Instantiate our scraper with all the context it needs
    scraper = SpeciesScraper(soup, book_name, genus_name)
    scraped_data = scraper.scrape_all()

    # Scrape and process the main body content
    selector = BOOK_CONTENT_SELECTORS.get(book_name)
    html_content = ""
    if selector:
        content_tags = soup.select(selector)
        if content_tags:
            html_content = "".join(str(p) for p in content_tags)
    
    from markdownify import markdownify
    body_markdown = format_body_content(markdownify(html_content))

    # --- Assemble Frontmatter and Create File ---
    name_for_slug = scraped_data['name'].lower().replace('sp. ', 'sp-').replace(' ', '-')
    slug = f"{genus_name.lower()}-{name_for_slug}"
    filepath = MARKDOWN_DIR / f"{slug}.md"
    
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
        'genus': genus_name,
        'taxonomic_status': scraped_data['taxonomic_status'],
        'plates': scraped_data['plates'],
        'genitalia': scraped_data['genitalia'],
        'misc_images': scraped_data['misc_images'],
        'citations': [] # Start with an empty list
    }
    
    post = frontmatter.Post(content=body_markdown)
    # Only add metadata fields that have a value
    post.metadata = {k: v for k, v in new_metadata.items() if v}
    
    save_markdown_file(post, filepath)

def run_scrape_new(generate_files=False):
    """
    The main function for the 'scrape_new' task.

    It finds all species in the legacy PHP files, compares them against the existing
    markdown files, and then either reports on the missing entries or actively

    scrapes and creates them.
    """
    # 1. Indexing Phase: Understand what we have and what's available
    master_urls = get_master_php_urls()
    existing_species = index_entries_by_url(MARKDOWN_DIR)
    existing_genera_by_url = index_entries_by_url(GENERA_DIR)
    existing_genera_by_slug = index_entries_by_slug(GENERA_DIR)
    
    # 2. Analysis Phase: Determine what's missing
    missing_urls = sorted(list(master_urls - set(existing_species.keys())))
    
    if not missing_urls:
        print("\n🎉 No missing entries found. Everything seems to be in sync!")
        return

    print(f"\nFound {len(missing_urls)} missing entries. Analyzing for context...")
    
    creatable_entries = []
    warnings = [] 
    for url in missing_urls:
        # Call the imported function
        context_data, context_type = get_contextual_data(url, existing_species, existing_genera_by_url, existing_genera_by_slug)
        if context_data:
            creatable_entries.append({'url': url, 'neighbor_data': context_data, 'context_type': context_type})
        else:
            warnings.append(url)

    # 3. Execution/Reporting Phase
    if generate_files:
        print(f"\n--- Starting Live Run: Attempting to create {len(creatable_entries)} files ---")
        for entry in creatable_entries:
            _create_species_file(entry)
        print("\n✨ Live run complete.")
    else:
        print("\n--- Dry Run Summary ---")
        print(f"✅ Found {len(creatable_entries)} entries that can be generated.")
        print(f"⚠️ Found {len(warnings)} entries that are missing context and cannot be generated.")
        print("Run with the '--generate-files' flag to create the new files.")
        # In the future, this would call the reporting module:
        # generate_audit_report(creatable_entries, warnings)