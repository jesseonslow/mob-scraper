# mob-scraper/tasks/audit.py

import collections
import frontmatter
import re

# Import the necessary functions to find missing files
from config import (
    MARKDOWN_DIR, GENERA_DIR, CONTENT_QUALITY_REPORT_FILENAME
)
from file_system import (
    get_master_php_urls, index_entries_by_url, index_entries_by_slug
)
from reporting import generate_html_report, update_index_page

# We need this helper function from scrape_new to determine if a missing
# file has enough context to be created.
def _get_contextual_data(missing_url, existing_species, existing_genera_by_url, existing_genera_by_slug):
    """
    Finds a neighboring or parent entry to provide context for a missing species.
   
    """
    url_pattern = re.compile(r'(.+)_(\d+)_(\d+)\.php$')
    match = url_pattern.search(missing_url)
    if not match: return None
    base, major, minor = match.groups()

    neighbor_minor = int(minor) - 1
    if neighbor_minor > 0:
        neighbor_url = f"{base}_{major}_{neighbor_minor}.php"
        if existing_species.get(neighbor_url): return 'species'

    genus_url = f"{base}_{major}.php"
    if existing_genera_by_url.get(genus_url): return 'genus by URL'

    if '/part-4/' in missing_url:
        try:
            genus_slug = missing_url.split('/part-4/', 1)[1].split('/')[0]
            if existing_genera_by_slug.get(genus_slug): return 'genus by slug'
        except IndexError: pass
    
    return None

def run_audit():
    """
    Runs a comprehensive audit on the content, checking for both missing files
    and quality issues in existing files, then generates a single HTML report.
    """
    print("🚀 Starting comprehensive content audit...")

    # --- Part 1: Audit for Missing Files ---
    print("🔎 Checking for missing files...")
    master_urls = get_master_php_urls()
    existing_species = index_entries_by_url(MARKDOWN_DIR)
    existing_genera_by_url = index_entries_by_url(GENERA_DIR)
    existing_genera_by_slug = index_entries_by_slug(GENERA_DIR)
    
    missing_urls = sorted(list(master_urls - set(existing_species.keys())))
    
    creatable_files = []
    uncreatable_files = []
    for url in missing_urls:
        context = _get_contextual_data(url, existing_species, existing_genera_by_url, existing_genera_by_slug)
        if context:
            creatable_files.append(url)
        else:
            uncreatable_files.append(url)

    # --- Part 2: Audit Existing File Quality ---
    print("🔎 Auditing quality of existing content...")
    empty_files = []
    unfinished_files = []
    book_data = collections.defaultdict(lambda: collections.defaultdict(int))

    for file_path in MARKDOWN_DIR.glob('**/*.md*'):
        if not file_path.is_file(): continue
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            
            clean_content = post.content.strip()
            book = post.metadata.get('book', 'Unknown Book')
            book_data[book]['total'] += 1

            if not clean_content:
                empty_files.append(file_path.name)
                book_data[book]['empty'] += 1
            elif not clean_content.endswith('.'):
                unfinished_files.append(file_path.name)
                book_data[book]['unfinished'] += 1
        except Exception as e:
            print(f"  [ERROR] Could not process {file_path.name}: {e}")

    # --- Part 3: Prepare and Generate Report ---
    summary = {
        "Action Required: Files Missing Context": len(uncreatable_files),
        "Files Ready to Scrape": len(creatable_files),
        "Total Missing Files": len(missing_urls),
        "Existing Pages with NO content": len(empty_files),
        "Existing Pages with UNFINISHED content": len(unfinished_files)
    }
    
    table_rows = []
    for book, data in sorted(book_data.items()):
        total, empty, unfinished = data['total'], data['empty'], data['unfinished']
        p_empty = (empty / total * 100) if total > 0 else 0
        p_unfinished = (unfinished / total * 100) if total > 0 else 0
        table_rows.append(f"<tr><td>{book}</td><td>{empty}</td><td>{p_empty:.1f}%</td><td>{unfinished}</td><td>{p_unfinished:.1f}%</td><td>{total}</td></tr>")
    
    table_html = f"""
        <table style="width:100%; border-collapse: collapse; text-align: left;">
            <thead><tr style="background-color: #f2f2f2;"><th style="padding: 8px;">Book Name</th><th style="padding: 8px;">Empty</th><th style="padding: 8px;">% Empty</th><th style="padding: 8px;">Unfinished</th><th style="padding: 8px;">% Unfinished</th><th style="padding: 8px;">Total</th></tr></thead>
            <tbody>{''.join(table_rows)}</tbody>
        </table>"""

    report_sections = [
        {
            "title": f"Action Required: {len(uncreatable_files)} Files Missing Context",
            "content": f"<p>The following files could not find a parent genus or neighbor. They cannot be generated automatically and require manual investigation.</p><ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(uncreatable_files))}</ul>"
        },
        {
            "title": "Existing Content Quality Breakdown", 
            "content": table_html
        },
        {
            "title": f"Files with NO Content ({len(empty_files)} total)", 
            "content": f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(empty_files))}</ul>"
        },
        {
            "title": f"Files with UNFINISHED Content ({len(unfinished_files)} total)", 
            "content": f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(unfinished_files))}</ul>"
        },
        {
            "title": f"Files Ready to Scrape ({len(creatable_files)} total)", 
            "content": f"<p>Run <code>python main.py scrape --generate-files</code> to create these.</p><ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(creatable_files))}</ul>"
        }
    ]

    generate_html_report(
        report_title="📊 Comprehensive Content Audit",
        summary_items=summary,
        sections=report_sections,
        output_filename=CONTENT_QUALITY_REPORT_FILENAME
    )
    
    update_index_page()