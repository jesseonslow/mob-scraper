# tasks/build_citations.py

import frontmatter
from bs4 import BeautifulSoup
from config import SPECIES_DIR, PHP_ROOT_DIR, LEGACY_URL_BASE
from core.file_system import save_markdown_file
from core.scraper import SpeciesScraper
from tasks.utils import get_book_from_url
from .citation_audit import run_citation_audit

def run_build_citations():
    """
    Finds all files with empty citations and attempts to scrape them
    from the legacy PHP files.
    """
    print("🚀 Starting citation build process...")

    # First, run the citation audit to get the list of files with empty citations.
    # We can suppress the report generation for this run.
    report_data = run_citation_audit(generate_report=False)
    files_to_process = report_data.get('citations_empty', [])

    if not files_to_process:
        print("✅ No files with empty citations found.")
        return

    print(f"Found {len(files_to_process)} file(s) with empty citations. Attempting to scrape...")
    updated_files_count = 0

    for filename in files_to_process:
        file_path = SPECIES_DIR / filename
        if not file_path.is_file():
            continue

        print(f"Processing: {filename}")
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)

            legacy_url = post.metadata.get('legacy_url')
            if not legacy_url:
                print(f"  -> ⚠️ SKIPPING: No legacy_url found.")
                continue

            relative_path = legacy_url.replace(LEGACY_URL_BASE, "")
            php_path = PHP_ROOT_DIR / relative_path
            if not php_path.exists():
                print(f"  -> ⚠️ SKIPPING: PHP file not found at {php_path}")
                continue

            with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()

            book_name = get_book_from_url(legacy_url)
            genus_name = post.metadata.get('genus', 'Unknown')
            
            scraper = SpeciesScraper(html_content, book_name, genus_name)
            scraped_data = scraper.scrape_all()

            new_citations = scraped_data.get('citations')
            if new_citations:
                post.metadata['citations'] = new_citations
                save_markdown_file(post, file_path)
                updated_files_count += 1
            else:
                print(f"  -> ℹ️ No citation found in the source file.")

        except Exception as e:
            print(f"  -> ❌ ERROR: Could not process {filename}: {e}")

    print(f"\n✨ Citation build finished. Updated {updated_files_count} file(s).")