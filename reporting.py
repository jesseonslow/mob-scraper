# mob-scraper/reporting.py

import re
from datetime import datetime
from pathlib import Path
from html import escape
from bs4 import BeautifulSoup

from config import REPORT_DIR, SPECIES_DIR
from file_system import get_master_php_urls, index_entries_by_url

INDEX_TEMPLATE = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Scraper Reports Index</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; margin: 0; background-color: #f9f9f9; color: #333; }}
    .container {{ max-width: 900px; margin: 2em auto; padding: 0 1em; }}
    h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 0.5em; }}
    .summary-stats {{ background: #fff; border: 1px solid #ddd; padding: 1.5em; margin-bottom: 2em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .progress-bar {{ background-color: #e9ecef; border-radius: .25rem; height: 2rem; display: flex; overflow: hidden; font-size: .75rem; }}
    .progress-bar-inner {{ background-color: #28a745; display: flex; flex-direction: column; justify-content: center; color: #fff; text-align: center; white-space: nowrap; transition: width .6s ease; font-weight: bold; font-size: 1rem; }}
    .stats-label {{ margin-top: 0.5rem; text-align: right; color: #555; font-size: 0.9em; }}
    .report-item {{ background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2em; overflow: hidden; }}
    .report-header {{ background-color: #f7f7f7; padding: 1em 1.5em; border-bottom: 1px solid #eee; }}
    .report-header h2 {{ margin: 0; font-size: 1.5em; }}
    .report-header a {{ color: #005a9c; text-decoration: none; }}
    .report-header a:hover {{ text-decoration: underline; }}
    .report-meta {{ font-size: 0.9em; color: #555; }}
    .report-summary {{ padding: 1.5em; }}
    .report-summary ul {{ margin: 0; padding-left: 1.2em; }}
    .report-summary li {{ margin-bottom: 0.5em; }}
</style></head><body>
<div class="container">
    <h1>📊 Scraper Reports Index</h1>
    <div class="summary-stats">
        <h2>Migration Progress</h2>
        <div class="progress-bar"><div class="progress-bar-inner" style="width: {percentage_complete:.2f}%;">{percentage_complete:.2f}%</div></div>
        <p class="stats-label">Completed: <strong>{total_markdown_species}</strong> of <strong>{total_php_species}</strong> species files.</p>
    </div>
    {report_list_html}
</div></body></html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>{report_title}</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; margin: 0; background-color: #f9f9f9; color: #333; }}
    .container {{ max-width: 900px; margin: 2em auto; background: white; padding: 2em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    h1, h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 0.5em; }}
    ul {{ list-style-type: none; padding-left: 0; }}
    li {{ background-color: #fdfdfd; border: 1px solid #eee; padding: 10px; margin-bottom: 5px; border-radius: 4px; }}
    code {{ background-color: #eef; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; word-break: break-all; }}
    .summary-item strong {{ color: #005a9c; }}
    .footer {{ text-align: center; color: #777; font-size: 0.9em; margin-top: 2em; }}
</style></head>
<body><div class="container"><h1>{report_title}</h1>{summary_html}{sections_html}
<div class="footer"><p>Report generated on {generation_date}</p></div>
</div></body></html>
"""

def generate_html_report(report_title: str, summary_items: dict, sections: list, output_filename: str):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # --- MODIFIED SECTION ---
    summary_html = "<h2>Summary</h2><ul>"
    for key, value in summary_items.items():
        # Add a style attribute if the key indicates an action is required
        style = ' style="color: #c0392b;"' if "Action Required" in key else ""
        summary_html += f'<li class="summary-item"{style}>{key}: <strong>{value}</strong></li>'
    summary_html += "</ul>"
    # --- END MODIFIED SECTION ---
    
    sections_html = ""
    for section in sections:
        sections_html += f"<h2>{escape(section['title'])}</h2>"
        sections_html += section['content']
    
    final_html = HTML_TEMPLATE.format(
        report_title=report_title,
        summary_html=summary_html,
        sections_html=sections_html,
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    report_path = REPORT_DIR / output_filename
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"\n✅ Report successfully generated: {report_path.resolve()}")


def update_index_page():
    # ... (This function remains exactly the same) ...
    print("Updating reports index page...")
    master_urls = get_master_php_urls()
    existing_species = index_entries_by_url(SPECIES_DIR)
    total_php_species = len(master_urls)
    total_markdown_species = len(existing_species)
    percentage_complete = (total_markdown_species / total_php_species * 100) if total_php_species > 0 else 0
    reports = []
    if not REPORT_DIR.is_dir():
        return

    for report_file in REPORT_DIR.glob("*.html"):
        if report_file.name == "index.html":
            continue

        with open(report_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        title_tag = soup.find('h1')
        title = title_tag.text if title_tag else report_file.stem.replace('_', ' ').title()
        
        summary_html = "<p>No summary found.</p>"
        summary_h2 = soup.find('h2', string='Summary')
        if summary_h2:
            summary_ul = summary_h2.find_next_sibling('ul')
            if summary_ul:
                summary_html = str(summary_ul)
        
        date_text = datetime.fromtimestamp(report_file.stat().st_mtime)
        footer_p = soup.find('p', string=re.compile("Report generated on"))
        if footer_p:
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', footer_p.text)
            if match:
                date_text = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")

        reports.append({
            'filename': report_file.name,
            'title': title,
            'date': date_text,
            'summary_html': summary_html
        })

    reports.sort(key=lambda r: r['date'], reverse=True)

    report_list_html = ""
    if not reports:
        report_list_html = "<p>No reports found.</p>"
    else:
        for report in reports:
            report_list_html += f"""
            <div class="report-item">
                <div class="report-header">
                    <h2><a href="{report['filename']}" target="_blank">{escape(report['title'])}</a></h2>
                    <p class="report-meta">
                        Generated on {report['date'].strftime("%Y-%m-%d %H:%M:%S")} | File: <code>{report['filename']}</code>
                    </p>
                </div>
                <div class="report-summary">
                    {report['summary_html']}
                </div>
            </div>
            """
    
    index_content = INDEX_TEMPLATE.format(
        report_list_html=report_list_html,
        total_php_species=total_php_species,
        total_markdown_species=total_markdown_species,
        percentage_complete=percentage_complete
    )
    index_path = REPORT_DIR / "index.html"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print(f"✅ Index page updated: {index_path.resolve()}")