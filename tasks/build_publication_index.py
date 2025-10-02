# tasks/build_publication_index.py

import collections
import re
from bs4 import BeautifulSoup
from config import PHP_ROOT_DIR, PUBLICATION_INDEX_REPORT_FILENAME
from .reporting import generate_html_report, update_index_page

def run_build_publication_index():
    """
    Scans all references.php files, parses them, and builds a consolidated
    publication index report.
    """
    print("🚀 Starting publication index build...")

    publication_counts = collections.Counter()
    
    reference_files = list(PHP_ROOT_DIR.glob('**/references.php'))
    print(f"Found {len(reference_files)} references.php files to process.")

    for ref_path in reference_files:
        try:
            with open(ref_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # --- THIS IS THE FIX ---
            # A much more robust way to find the container of the references.
            # We look for a <p> tag that contains a year in parentheses, which is a
            # very strong indicator of a reference list.
            
            reference_container = None
            all_p_tags = soup.find_all('p')
            for p_tag in all_p_tags:
                if re.search(r'\(\d{4}\)', p_tag.get_text()):
                    reference_container = p_tag
                    break # We've found our container, so we can stop looking.

            if not reference_container:
                print(f"  [WARNING] Could not find reference container in {ref_path.name}. Skipping.")
                continue

            # The references are separated by <br> tags within the main <p> tag.
            # We split the inner HTML of the tag by the <br> tags.
            references_html = str(reference_container)
            individual_references = re.split(r'<br\s*/?>', references_html, flags=re.IGNORECASE)
            
            last_publication = None
            
            for ref_html in individual_references:
                # For each snippet, create a new soup to parse it and get clean text
                ref_soup = BeautifulSoup(ref_html, 'html.parser')
                text = ref_soup.get_text(strip=True)
                
                if not text: # Skip empty lines created by the split
                    continue
                    
                # Handle "Ibid." by reusing the last valid publication
                if 'ibid.' in text.lower():
                    if last_publication:
                        publication_counts[last_publication] += 1
                    continue

                # A simple heuristic to identify a valid publication entry
                if re.search(r'\(\d{4}\)', text) and len(text) > 20:
                    clean_text = " ".join(text.split())
                    publication_counts[clean_text] += 1
                    last_publication = clean_text

        except Exception as e:
            print(f"  [ERROR] Could not process {ref_path}: {e}")

    if not publication_counts:
        print("No publications found.")
        return

    # --- Prepare and Generate Report ---
    summary = {
        "Total Unique Publications Found": len(publication_counts)
    }

    # --- Create Publication Report Section ---
    publication_html = "<button onclick=\"copyTableToClipboard('publication-table')\">Copy as Markdown</button>"
    publication_html += "<table class='sortable' id='publication-table'><thead><tr><th>Publication</th><th>Count</th></tr></thead><tbody>"
    for pub, count in publication_counts.most_common():
        publication_html += f"<tr><td><code>{pub}</code></td><td>{count}</td></tr>"
    publication_html += "</tbody></table>"
    
    report_sections = [
        {
            "title": "Publication Index",
            "content": publication_html
        }
    ]

    generate_html_report(
        report_title="📚 Publication Index",
        summary_items=summary,
        sections=report_sections,
        output_filename=PUBLICATION_INDEX_REPORT_FILENAME
    )
    
    update_index_page()