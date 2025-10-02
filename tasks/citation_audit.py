# tasks/citation_audit.py

import collections
import frontmatter
import re
import json
from config import SPECIES_DIR, CITATION_HEALTH_REPORT_FILENAME
from .reporting import generate_html_report, update_index_page
from .utils import load_reference_lookup
# Import the shared functions from our new single source of truth
from .format_citations import parse_citation, format_citation, _normalize_publication_for_matching

def run_citation_audit(generate_report=True):
    print("🚀 Starting citation health audit...")
    
    # For Summary Metrics
    files_with_formatted = set()
    files_with_unformatted = set()
    files_with_no_citations = set()
    files_with_broken_citations = set()

    # For Detailed Report
    parsed_citations, invalid_citations = [], []
    
    total_files = 0
    for file_path in SPECIES_DIR.glob('**/*.md*'):
        if not file_path.is_file():
            continue
        total_files += 1
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)

            book_name = post.metadata.get('book', 'Unknown')
            legacy_url = post.metadata.get('legacy_url', '')
            citations = post.metadata.get('citations', [])

            if not citations:
                files_with_no_citations.add(file_path.name)
                continue

            has_broken = False
            is_fully_formatted = True
            
            for citation in citations:
                if '*' not in citation:
                    is_fully_formatted = False
                    parsed_list = parse_citation(citation, book_name, legacy_url)
                    if parsed_list:
                        for parsed in parsed_list:
                            if parsed["pattern"] == "[INVALID CITATION]":
                                invalid_citations.append(parsed)
                                has_broken = True
                            else:
                                parsed["formatted_output"] = format_citation(parsed)
                                parsed_citations.append(parsed)
                else:
                    parsed_list = parse_citation(citation, book_name, legacy_url)
                    if parsed_list and parsed_list[0]["pattern"] == "[INVALID CITATION]":
                        invalid_citations.append(parsed_list[0])
                        has_broken = True

            if has_broken:
                files_with_broken_citations.add(file_path.name)
            elif is_fully_formatted:
                files_with_formatted.add(file_path.name)
            else:
                files_with_unformatted.add(file_path.name)

        except Exception as e:
            print(f"  [ERROR] Could not process {file_path.name}: {e}")

    # --- Group valid citations by publication (case-insensitively and punctuation-insensitively) ---
    citations_by_publication_normalized = collections.defaultdict(list)
    for citation in parsed_citations:
        publication_key = _normalize_publication_for_matching(citation['publication'])
        citations_by_publication_normalized[publication_key].append(citation)

    # Use the first-seen capitalization for display
    citations_by_publication = {}
    for norm_pub, citation_list in citations_by_publication_normalized.items():
        if norm_pub != "uncategorized":
            display_key = citation_list[0]['publication']
            citations_by_publication[display_key] = citation_list
        else:
            citations_by_publication["Uncategorized"] = citation_list

    sorted_publications = sorted(citations_by_publication.items(), key=lambda item: len(item[1]), reverse=True)
    
    unique_publication_names = [pub[0] for pub in sorted_publications if pub[0] != "Uncategorized"]
    publications_json = json.dumps(unique_publication_names, indent=2)

    summary = {
        "Total Files Scanned": total_files,
        "Number of Files with Formatted Citations": len(files_with_formatted),
        "Number of Files with Unformatted Citations": len(files_with_unformatted),
        "Number of Files with No Citations": len(files_with_no_citations),
        "Number of Files with Broken Citations": len(files_with_broken_citations),
    }
    
    report_html = ""
    for publication, citations in sorted_publications:
        table_id = f"table-{re.sub(r'[^a-zA-Z0-9]', '-', publication)}"
        report_html += f"<details><summary>{publication} ({len(citations)} citations)</summary><div>"
        report_html += f"<button onclick=\"copyTableToClipboard('{table_id}')\">Copy as Markdown</button>"
        report_html += f"<table class='sortable' id='{table_id}'><thead><tr><th>Original</th><th>Formatted</th><th>Pattern</th><th>Source</th></tr></thead><tbody>"
        for item in citations:
            report_html += (
                f"<tr><td><code>{item['original']}</code></td><td>{item['formatted_output']}</td>"
                f"<td><code>{item['pattern']}</code></td><td><a href='{item['canonical_url']}' target='_blank'>Link</a></td></tr>"
            )
        report_html += "</tbody></table></div></details>"
    
    invalid_html = "<ul>"
    for c in invalid_citations:
        invalid_html += f"<li><code>{c['original']}</code> (<a href='{c['canonical_url']}' target='_blank'>Source</a>)</li>"
    invalid_html += "</ul>"
    
    json_export_html = f"""
    <p>Click the button to copy the list of unique publication names as a JSON array.</p>
    <button onclick="copyJsonToClipboard()">Copy JSON</button>
    <textarea id="json-export" style="width: 100%; height: 150px; margin-top: 1em;">{publications_json}</textarea>
    """

    report_sections = [
        {"title": "Parsed Citation Analysis (Unformatted Citations Only)", "content": report_html},
        {"title": "Export Unique Publications", "content": json_export_html},
        {"title": f"Files with Invalid Citations ({len(files_with_broken_citations)} total)", "content": invalid_html},
        {"title": f"Files with No Citations ({len(files_with_no_citations)} total)", "content": f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(files_with_no_citations))}</ul>"}
    ]

    generate_html_report(
        report_title="📝 Citation Health Report",
        summary_items=summary,
        sections=report_sections,
        output_filename=CITATION_HEALTH_REPORT_FILENAME
    )
    
    update_index_page()
    return {"summary": summary}