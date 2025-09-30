import collections
import frontmatter
import re

from config import (
    SPECIES_DIR, GENERA_DIR, CONTENT_QUALITY_REPORT_FILENAME
)
from core.file_system import get_master_php_urls, index_entries_by_url, index_entries_by_slug
from .reporting import generate_html_report, update_index_page
from tasks.utils import get_contextual_data
from reclassification_manager import load_reclassified_urls
from .citation_audit import run_citation_audit

def run_audit():
    """
    Runs a comprehensive audit on the content, checking for missing files,
    quality issues, and legacy links, then generates a single HTML report.
    Also triggers the citation audit.
    """
    print("🚀 Starting comprehensive content audit...")

    # --- Part 1: File Reconciliation ---
    print("🔎 Reconciling PHP source files with Markdown content...")
    all_php_urls = get_master_php_urls()
    reclassified_urls = load_reclassified_urls()
    master_urls = all_php_urls - reclassified_urls
    
    existing_species_by_url = index_entries_by_url(SPECIES_DIR)
    existing_genera_by_url = index_entries_by_url(GENERA_DIR)
    existing_genera_by_slug = index_entries_by_slug(GENERA_DIR)
    
    php_urls_set = set(master_urls)
    md_urls_set = set(existing_species_by_url.keys())
    missing_urls = sorted(list(php_urls_set - md_urls_set))
    
    creatable_files = []
    uncreatable_files = []
    for url in missing_urls:
        context, context_type = get_contextual_data(url, existing_species_by_url, existing_genera_by_url, existing_genera_by_slug)
        if context:
            creatable_files.append(url)
        else:
            uncreatable_files.append(url)

    # --- Part 2: Audit Existing File Quality ---
    print("🔎 Auditing quality of existing content...")
    empty_files = []
    unfinished_files = []
    legacy_links_found = []
    book_data = collections.defaultdict(lambda: collections.defaultdict(int))
    
    # Regex to find markdown links ending in .php
    legacy_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+\.php)\)')

    for file_path in SPECIES_DIR.glob('**/*.md*'):
        if not file_path.is_file(): continue
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            
            # Check for legacy links in the body content
            if legacy_link_pattern.search(post.content):
                legacy_links_found.append(file_path.name)

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
        "Action Required: Files with Legacy `.php` Links": len(legacy_links_found),
        "Action Required: Files Missing Context": len(uncreatable_files),
        "Files Ready to Scrape": len(creatable_files),
        "Total Missing Files": len(missing_urls),
        "Existing Pages with NO content": len(empty_files),
        "Existing Pages with UNFINISHED content": len(unfinished_files),
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
            "title": f"Action Required: {len(legacy_links_found)} Files with Legacy `.php` Links",
            "content": f"<p>The following files contain one or more markdown hyperlinks pointing to a <code>.php</code> file. These should be updated to point to the new content paths.</p><ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(legacy_links_found))}</ul>"
        },
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
    
    # Pass the new legacy link count to the index page updater
    audit_results_for_index = {
        'legacy_links_count': len(legacy_links_found)
    }
    update_index_page(audit_results=audit_results_for_index)

    print("\n" + "="*50)
    run_citation_audit()