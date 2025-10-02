# tasks/reporting.py

import re
from datetime import datetime
from pathlib import Path
from html import escape
from bs4 import BeautifulSoup
import shutil

from config import REPORT_DIR, TEMPLATE_DIR, CITATION_HEALTH_REPORT_FILENAME, CONTENT_QUALITY_REPORT_FILENAME
from core.file_system import get_master_php_urls, index_entries_by_url
from reclassification_manager import load_reclassified_urls

def _copy_asset_files():
    """
    Copies static CSS and JS files from the template directory to the report
    output directory.
    """
    if not TEMPLATE_DIR.is_dir():
        print(f"  [WARNING] Template directory not found at {TEMPLATE_DIR}")
        return
        
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    for asset in ["style.css", "script.js"]:
        source_path = TEMPLATE_DIR / asset
        dest_path = REPORT_DIR / asset
        if source_path.exists():
            shutil.copy2(source_path, dest_path)


def generate_html_report(report_title: str, summary_items: dict, sections: list, output_filename: str):
    _copy_asset_files()
    
    summary_html = "<h2>Summary</h2><ul>"
    for key, value in summary_items.items():
        style = ' style="color: #c0392b;"' if "Action Required" in key or "Badly" in key or "Broken" in key else ""
        summary_html += f'<li class="summary-item"{style}>{key}: <strong>{value}</strong></li>'
    summary_html += "</ul>"
    
    sections_html = ""
    for section in sections:
        sections_html += f"<h2>{escape(section['title'])}</h2>"
        sections_html += section['content']
    
    template_path = TEMPLATE_DIR / "report_template.html"
    if not template_path.exists():
        print(f"  [ERROR] Report template not found at {template_path}")
        return

    html_template_content = template_path.read_text(encoding='utf-8')
    final_html = html_template_content.format(
        report_title=report_title,
        summary_html=summary_html,
        sections_html=sections_html,
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    report_path = REPORT_DIR / output_filename
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"\n✅ Report successfully generated: {report_path.resolve()}")


def update_index_page(audit_results=None):
    _copy_asset_files()
    print("Updating reports index page...")
    reports = []
    if not REPORT_DIR.is_dir():
        return
    
    data_integrity_html = ""
    if audit_results:
        legacy_links = audit_results.get('legacy_links_count', 0)
        
        if legacy_links > 0:
            data_integrity_html = f"""
            <div class="summary-stats">
                <h2>Data Integrity Issues</h2>
                <div class="health-grid">
                    <div class="stat-card {'critical' if legacy_links > 0 else ''}">
                        <h3>Legacy PHP Links</h3>
                        <div class="value">{legacy_links}</div>
                        <div class="description">Files with links to old .php pages.</div>
                    </div>
                </div>
            </div>
            """

    citation_summary_html = ""
    citation_report_path = REPORT_DIR / CITATION_HEALTH_REPORT_FILENAME
    if citation_report_path.exists():
        with open(citation_report_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        summary_list_items = soup.select('.summary-item')
        stats = {li.contents[0].strip().replace(':', ''): int(li.find('strong').text) for li in summary_list_items if li.find('strong')}
        
        # --- THIS IS THE FIX ---
        # Use the new, correct keys from the summary.
        total_files = stats.get("Total Files Scanned", 0)
        formatted = stats.get("Number of Files with Formatted Citations", 0)
        unformatted = stats.get("Number of Files with Unformatted Citations", 0)
        empty = stats.get("Number of Files with No Citations", 0)
        broken = stats.get("Number of Files with Broken Citations", 0)

        citation_summary_html = f"""
        <div class="summary-stats">
            <h2>Citation Health</h2>
            <div class="health-grid">
                <div class="stat-card">
                    <h3>Formatted</h3>
                    <div class="value">{formatted}</div>
                </div>
                <div class="stat-card">
                    <h3>Unformatted</h3>
                    <div class="value">{unformatted}</div>
                </div>
                <div class="stat-card">
                    <h3>Empty</h3>
                    <div class="value">{empty}</div>
                </div>
                <div class="stat-card {'critical' if broken > 0 else ''}">
                    <h3>Broken</h3>
                    <div class="value">{broken}</div>
                </div>
            </div>
        </div>
        """
        
    genera_summary_html = ""
    content_report_path = REPORT_DIR / CONTENT_QUALITY_REPORT_FILENAME
    if content_report_path.exists():
        with open(content_report_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        summary_list_items = soup.select('.summary-item')
        stats = {li.contents[0].strip().replace(':', ''): int(li.find('strong').text) for li in summary_list_items if li.find('strong')}

        missing = stats.get("Action Required Missing Genera Files", 0)
        empty = stats.get("Existing Genera Pages with NO content", 0)
        bad_format = stats.get("Existing Genera Pages with BADLY FORMATTED content", 0)

        genera_summary_html = f"""
        <div class="summary-stats">
            <h2>Genera Health</h2>
            <div class="health-grid">
                <div class="stat-card {'critical' if missing > 0 else ''}">
                    <h3>Missing Files</h3>
                    <div class="value">{missing}</div>
                </div>
                <div class="stat-card">
                    <h3>Empty Content</h3>
                    <div class="value">{empty}</div>
                </div>
                <div class="stat-card {'critical' if bad_format > 0 else ''}">
                    <h3>Badly Formatted</h3>
                    <div class="value">{bad_format}</div>
                </div>
            </div>
        </div>
        """

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
    if reports:
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
    
    template_path = TEMPLATE_DIR / "index_template.html"
    if not template_path.exists():
        print(f"  [ERROR] Index template not found at {template_path}")
        return
        
    index_template_content = template_path.read_text(encoding='utf-8')
    index_content = index_template_content.format(
        report_list_html=report_list_html,
        citation_summary_html=citation_summary_html,
        data_integrity_html=data_integrity_html,
        genera_summary_html=genera_summary_html
    )
    index_path = REPORT_DIR / "index.html"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print(f"✅ Index page updated: {index_path.resolve()}")