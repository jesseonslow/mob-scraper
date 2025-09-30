# tasks/citation_audit.py

import collections
import frontmatter
from config import SPECIES_DIR, CITATION_HEALTH_REPORT_FILENAME
from reporting import generate_html_report, update_index_page

def run_citation_audit():
    """
    Scans all species files and generates a report on the health of their citations.
    """
    print("🚀 Starting citation health audit...")

    citations_empty = []
    citations_no_markdown = []
    citations_badly_formatted = []
    citations_formatted_correctly = []

    total_files = 0

    for file_path in SPECIES_DIR.glob('**/*.md*'):
        if not file_path.is_file():
            continue
        
        total_files += 1
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)

            citations = post.metadata.get('citations', [])
            if not citations:
                citations_empty.append(file_path.name)
            else:
                is_badly_formatted = False
                has_markdown = False
                for citation in citations:
                    if '*' in citation:
                        has_markdown = True
                        # A simple check for an obvious formatting error
                        if '\\n' in repr(citation):
                            is_badly_formatted = True
                
                if is_badly_formatted:
                    citations_badly_formatted.append(file_path.name)
                elif not has_markdown:
                    citations_no_markdown.append(file_path.name)
                else:
                    citations_formatted_correctly.append(file_path.name)

        except Exception as e:
            print(f"  [ERROR] Could not process {file_path.name}: {e}")

    # --- Prepare and Generate Report ---
    summary = {
        "Total Files Scanned": total_files,
        "Correctly Formatted": len(citations_formatted_correctly),
        "Empty": len(citations_empty),
        "No Markdown": len(citations_no_markdown),
        "Badly Formatted": len(citations_badly_formatted),
    }

    report_sections = [
        {
            "title": f"Correctly Formatted ({len(citations_formatted_correctly)} total)",
            "content": f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(citations_formatted_correctly))}</ul>"
        },
        {
            "title": f"Empty ({len(citations_empty)} total)",
            "content": f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(citations_empty))}</ul>"
        },
        {
            "title": f"No Markdown ({len(citations_no_markdown)} total)",
            "content": f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(citations_no_markdown))}</ul>"
        },
        {
            "title": f"Badly Formatted ({len(citations_badly_formatted)} total)",
            "content": f"<ul>{''.join(f'<li><code>{f}</code></li>' for f in sorted(citations_badly_formatted))}</ul>"
        }
    ]

    generate_html_report(
        report_title="📝 Citation Health Report",
        summary_items=summary,
        sections=report_sections,
        output_filename=CITATION_HEALTH_REPORT_FILENAME
    )
    
    update_index_page()