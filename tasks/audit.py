# mob-scraper/tasks/audit.py

import collections
import frontmatter
import re

from config import (
    SPECIES_DIR, GENERA_DIR, CONTENT_QUALITY_REPORT_FILENAME
)
from core.file_system import get_master_php_urls, index_entries_by_url, index_entries_by_slug, get_all_referenced_genera
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
    
    creatable_species_files = []
    uncreatable_files = []
    for url in missing_urls:
        context, context_type = get_contextual_data(url, existing_species_by_url, existing_genera_by_url, existing_genera_by_slug)
        if context:
            creatable_species_files.append(url)
        else:
            uncreatable_files.append(url)
            
    # --- Part 1a: Check for missing genera ---
    referenced_genera = get_all_referenced_genera()
    existing_genera_slugs = set(existing_genera_by_slug.keys())
    missing_genera = sorted(list(referenced_genera - existing_genera_slugs))


    # --- Part 2: Audit Existing File Quality ---
    print("🔎 Auditing quality of existing content...")
    empty_species_files = []
    unfinished_species_files = []
    legacy_links_found = []
    book_data = collections.defaultdict(lambda: collections.defaultdict(int))
    
    empty_genera_files = []
    unfinished_genera_files = []
    bad_format_genera_files = []
    
    legacy_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+\.php)\)')

    # Audit Species Files
    for file_path in SPECIES_DIR.glob('**/*.md*'):
        if not file_path.is_file(): continue
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            
            if legacy_link_pattern.search(post.content):
                legacy_links_found.append(file_path.name)

            clean_content = post.content.strip()
            book = post.metadata.get('book', 'Unknown Book')
            book_data[book]['total'] += 1

            if not clean_content:
                empty_species_files.append(file_path.name)
                book_data[book]['empty'] += 1
            elif not clean_content.endswith('.'):
                unfinished_species_files.append(file_path.name)
                book_data[book]['unfinished'] += 1
                
        except Exception as e:
            print(f"  [ERROR] Could not process {file_path.name}: {e}")

    # Audit Genera Files
    for file_path in GENERA_DIR.glob('**/*.md*'):
        if not file_path.is_file(): continue
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            
            clean_content = post.content.strip()
            
            if not clean_content:
                empty_genera_files.append(file_path.name)
            elif not clean_content.endswith('.'):
                unfinished_genera_files.append(file_path.name)
            
            if '<' in post.content or '>' in post.content:
                bad_format_genera_files.append(file_path.name)

        except Exception as e:
            print(f"  [ERROR] Could not process {file_path.name}: {e}")

    # --- Part 3: Prepare and Generate Report ---
    summary = {
        "Action Required: Files with Legacy `.php` Links": len(legacy_links_found),
        "Action Required: Files Missing Context": len(uncreatable_files),
        "Action Required: Missing Genera Files": len(missing_genera),
        "Files Ready to Scrape (Species)": len(creatable_species_files),
        "Total Missing Species Files": len(missing_urls),
        "Existing Species Pages (No Content)": len(empty_species_files),
        "Existing Species Pages (Unfinished)": len(unfinished_species_files),
        "Existing Genera Pages (No Content)": len(empty_genera_files),
        "Existing Genera Pages (Unfinished)": len(unfinished_genera_files),
        "Existing Genera Pages (Badly Formatted)": len(bad_format_genera_files),
    }

    report_sections = []

    # --- Section 1: Existing Content Quality Breakdown (Always Visible) ---
    species_table_rows = []
    for book, data in sorted(book_data.items()):
        total, empty, unfinished = data['total'], data['empty'], data['unfinished']
        p_empty = (empty / total * 100) if total > 0 else 0
        p_unfinished = (unfinished / total * 100) if total > 0 else 0
        species_table_rows.append(f"<tr><td>{book}</td><td>{empty}</td><td>{p_empty:.1f}%</td><td>{unfinished}</td><td>{p_unfinished:.1f}%</td><td>{total}</td></tr>")
    
    species_table_html = f"""
        <h4>Species Content Quality</h4>
        <table style="width:100%; border-collapse: collapse; text-align: left;">
            <thead><tr><th>Book Name</th><th>Empty</th><th>% Empty</th><th>Unfinished</th><th>% Unfinished</th><th>Total</th></tr></thead>
            <tbody>{''.join(species_table_rows)}</tbody>
        </table>"""

    genera_stats = {
        "Empty": len(empty_genera_files),
        "Unfinished": len(unfinished_genera_files),
        "Badly Formatted": len(bad_format_genera_files),
        "Total": len(list(GENERA_DIR.glob('**/*.md*')))
    }
    genera_table_html = f"""
        <h4>Genera Content Quality</h4>
        <p>A brief overview of the content quality for genera files.</p>
        <ul>
            <li><strong>Empty Files:</strong> {genera_stats['Empty']}</li>
            <li><strong>Unfinished Files:</strong> {genera_stats['Unfinished']}</li>
            <li><strong>Badly Formatted Files:</strong> {genera_stats['Badly Formatted']}</li>
            <li><strong>Total Files:</strong> {genera_stats['Total']}</li>
        </ul>
    """
    
    report_sections.append({
        "title": "Existing Content Quality Breakdown", 
        "content": species_table_html + genera_table_html,
        "collapsible": False  # This ensures it's not collapsible
    })

    # --- Section 2: Files Ready to Scrape (Always Visible) ---
    # For now, we only create species files, but the report can mention both
    ready_to_scrape_content = (
        f"<p>Run <code>python main.py --generate-files</code> to create the files listed below. "
        f"This command will check for both creatable species and genera files.</p>"
        f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(creatable_species_files))}</ul>"
    )
    report_sections.append({
        "title": f"Files Ready to Scrape ({len(creatable_species_files)} total)",
        "content": ready_to_scrape_content,
        "collapsible": False
    })
    
    # --- Section 3: Collapsible Sections (Conditional) ---
    conditional_sections = [
        (f"Action Required: Files with Legacy `.php` Links", legacy_links_found, "The following files contain markdown links to `.php` files."),
        (f"Action Required: Files Missing Context", uncreatable_files, "These files could not find a parent genus or neighbor and need manual investigation."),
        (f"Action Required: Missing Genera Files", missing_genera, "These genera are referenced by species but do not have a corresponding file."),
        (f"Genera Files with NO Content", empty_genera_files, ""),
        (f"Genera Files with UNFINISHED Content", unfinished_genera_files, "These files have content but do not end with a period, suggesting they are incomplete."),
        (f"Species Files with NO Content", empty_species_files, ""),
        (f"Species Files with UNFINISHED Content", unfinished_species_files, "These files have content but do not end with a period, suggesting they are incomplete."),
    ]

    for title, file_list, description in conditional_sections:
        if file_list:
            content = f"<p>{description}</p>" if description else ""
            content += f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(file_list))}</ul>"
            report_sections.append({
                "title": f"{title} ({len(file_list)} total)",
                "content": content,
                "collapsible": True
            })

    # --- Generate the final report ---
    generate_html_report(
        report_title="📊 Comprehensive Content Audit",
        summary_items=summary,
        sections=report_sections,
        output_filename=CONTENT_QUALITY_REPORT_FILENAME
    )
    
    audit_results_for_index = {
        'legacy_links_count': len(legacy_links_found)
    }
    update_index_page(audit_results=audit_results_for_index)

    print("\n" + "="*50)
    run_citation_audit()