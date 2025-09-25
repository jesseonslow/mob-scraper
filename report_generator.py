from datetime import datetime
from html import escape

def generate_html_report(creatable_entries, warnings):
    """Generates a detailed HTML report with an improved summary."""
    no_neighbor_count = len(warnings)
    creatable_count = len(creatable_entries)
    total_missing_count = creatable_count + no_neighbor_count
    not_ready_percent = (no_neighbor_count / total_missing_count * 100) if total_missing_count > 0 else 0

    missing_html = ""
    if creatable_entries:
        for entry in creatable_entries:
            match = re.search(r'([a-zA-Z0-9_-]+_\d+)_\d+\.php$', entry['url'])
            entry['group'] = match.group(1) if match else 'unknown'
        sorted_missing = sorted(creatable_entries, key=lambda x: x['group'])
        for group_name, group in groupby(sorted_missing, key=lambda x: x['group']):
            missing_html += f"<h3>{group_name}</h3><ul>{''.join([f'<li><code>{escape(entry['url'])}</code></li>' for entry in group])}</ul>"
    else: missing_html = "<p>No entries can be generated as no neighbors could be found.</p>"

    html = f"""
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Content Audit Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; margin: 0; background-color: #f9f9f9; color: #333; }}
        .container {{ max-width: 900px; margin: 2em auto; background: white; padding: 2em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .summary, .results-section {{ border: 1px solid #ddd; padding: 1.5em; margin-bottom: 2em; border-radius: 8px; }}
        h1, h2, h3 {{ color: #333; }} h2 {{ border-bottom: 1px solid #eee; padding-bottom: 0.5em;}}
        code {{ background-color: #eee; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.9em; word-break: break-all; }}
        li {{ margin-bottom: 1em; }} .warning-item b {{ color: #9d2b28; }}
        .footer {{ text-align: center; color: #777; font-size: 0.9em; margin-top: 2em; }}
    </style></head>
    <body><div class="container">
        <h1>🔍 Content Audit Report</h1>
        <div class="summary">
            <h2>Summary</h2>
            <p><b>Total Missing Entries Found: {total_missing_count}</b></p>
            <ul style="list-style-type: none; padding-left: 0;">
                <li style="color: green;"><b>Ready for Generation:</b> {creatable_count}</li>
                <li style="color: red;"><b>Could Not Find Neighbor/Genus:</b> {no_neighbor_count} ({not_ready_percent:.1f}% of total)</li>
            </ul>
        </div>
        {"<div class='results-section'><h2>Actionable Issues (Warnings)</h2><ul class='warning-item'>" + "".join([f'<li>{w}</li>' for w in warnings]) + "</ul></div>" if warnings else ""}
        <div class="results-section"><h2>Entries Ready to Generate</h2>{missing_html}</div>
        <div class="footer"><p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p></div>
    </div></body></html>"""
    with open(REPORT_FILENAME, 'w', encoding='utf-8') as f: f.write(html)
    print(f"\n✅ Dry run complete. Report generated: {REPORT_FILENAME}")