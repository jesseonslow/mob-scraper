import argparse
import re
from pathlib import Path
import frontmatter
from bs4 import BeautifulSoup, NavigableString
import collections
from itertools import groupby
from datetime import datetime
from html import escape

# --- Configuration ---
MARKDOWN_DIR = Path("./src/content/species/")
PHP_ROOT_DIR = Path("../MoB-PHP/")
REPORT_FILENAME = "image_update_report.html"
DEFAULT_IMAGE_URL = "https://cdn.mothsofborneo.com/images/default.png"

BOOK_NUMBER_MAP = {
    "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8",
    "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
    "thirteen": "13", "fourteen": "14", "fifteen": "15",
    "sixteen": "16", "seventeen": "17", "eighteen": "18"
}

def process_file(markdown_path, dry_run=True):
    """
    Processes a single markdown file to update image_urls with labels
    scraped from the corresponding PHP file and categorizes them.
    """
    book_name = "Unknown"
    try:
        with open(markdown_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        legacy_url = post.metadata.get("legacy_url")
        book_name = post.metadata.get("book", "Unknown")
        existing_image_urls = post.metadata.get("image_urls", [])

        if book_name == 'thirteen':
            return {"status": "skip", "reason": "Book thirteen has no images", "book": book_name}
        if not legacy_url:
            return {"status": "error", "reason": "No legacy_url found", "book": book_name}
        if not existing_image_urls:
            return {"status": "skip", "reason": "No existing image_urls to process", "book": book_name}
        if book_name not in BOOK_NUMBER_MAP and book_name != "Unknown":
            return {"status": "error", "reason": f"Book '{book_name}' not in BOOK_NUMBER_MAP", "book": book_name}

        relative_path = legacy_url.replace("https://www.mothsofborneo.com/", "")
        php_path = PHP_ROOT_DIR / relative_path
        if not php_path.exists():
            return {"status": "error", "reason": "PHP file not found", "book": book_name}

        with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        plates = []
        genitalia = []
        misc_images = []
        warnings = []
        
        plate_tags = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            filename = Path(src).name.lower()
            is_plate = False
            if book_name == 'three':
                if re.match(r'^p.*?\d+.*', filename): is_plate = True
            else:
                if 'plate' in src.lower(): is_plate = True
            if is_plate:
                plate_tags.append(img)
        
        label_strings = []
        for element in soup.find_all(['td', 'p']):
            text = element.get_text()
            symbol_match = re.search(r'(♂|♀)', text)
            type_match = re.search(r'(\(holotype\)|\(paratype\))', text, re.IGNORECASE)
            if symbol_match or type_match:
                label_parts = []
                if symbol_match: label_parts.append(symbol_match.group(0))
                if type_match: label_parts.append(type_match.group(0).lower())
                label_strings.append(' '.join(label_parts))

        label_map = {}
        if len(plate_tags) != len(label_strings):
            warning_msg = f"<b>Mismatch:</b> Found {len(plate_tags)} plates but {len(label_strings)} labels."
            plate_srcs = [escape(tag.get('src', 'Unknown Src')) for tag in plate_tags]
            warning_msg += f"<br><b>Plates Found:</b><ul><li>" + "</li><li>".join(plate_srcs) + "</li></ul>"
            label_list_str = [escape(lbl) for lbl in label_strings]
            warning_msg += f"<b>Labels Found:</b><ul><li>" + "</li><li>".join(label_list_str) + "</li></ul>"
            mapping_info = []
            for i, tag in enumerate(plate_tags):
                src = escape(tag.get('src', 'Unknown Src'))
                if i < len(label_strings):
                    label = escape(label_strings[i])
                    mapping_info.append(f"<code>{src}</code> → <code>{label}</code>")
                else:
                    mapping_info.append(f"<code>{src}</code> → (no label)")
            warning_msg += f"<b>Resulting Mapping:</b><ul><li>" + "</li><li>".join(mapping_info) + "</li></ul>"
            warnings.append(warning_msg)

        for i, tag in enumerate(plate_tags):
            src_path = tag.get('src')
            if src_path and i < len(label_strings):
                label_map[src_path] = label_strings[i]
        
        for url in existing_image_urls:
            category = None; filename = Path(url).name.lower()
            if book_name == 'three':
                if re.match(r'^p.*?\d+.*', filename): category = 'plate'
                elif re.match(r'^\d+\..*', filename): category = 'genitalia'
                else: category = 'misc'
            else:
                if 'plate' in url.lower(): category = 'plate'
                elif 'genitalia' in url.lower(): category = 'genitalia'
                else: category = 'misc'

            if category == 'plate':
                try: partial_path = "/".join(url.split('/')[-2:])
                except IndexError: warnings.append(f"Could not parse URL for plate: {url}"); continue
                
                search_key = partial_path
                if book_name == 'three': search_key = Path(search_key).name
                elif book_name == 'twelve':
                    search_key = re.sub(r'(plate)(\d+)', r'Plate%20\2', search_key, flags=re.IGNORECASE)
                    search_key = search_key.replace(' ', '%20')

                found_key_in_map = None
                for key in label_map:
                    if key.endswith(search_key): found_key_in_map = key; break
                
                label = label_map.get(found_key_in_map)
                
                if not label and not any("Mismatch" in w for w in warnings):
                    warnings.append(f"Could not map a label for plate: {filename}")
                plates.append({"url": url, "label": label})
            elif category == 'genitalia': genitalia.append(url)
            elif category == 'misc': misc_images.append(url)

        # --- NEW: ADD DEFAULT IMAGE IF NO PLATES WERE FOUND ---
        if not plates:
            plates.append({"url": DEFAULT_IMAGE_URL, "label": ""})
            warnings.append("No plates found in source; added default image.")

        if not plates and not genitalia and not misc_images:
             return {"status": "warning", "reason": "Could not match any URLs in the PHP file", "warnings": warnings, "book": book_name}

        if dry_run:
            return {"status": "success", "plates": plates, "genitalia": genitalia, "misc_images": misc_images, "warnings": warnings, "book": book_name}
        else:
            for key in ['image_urls', 'images', 'genitalia', 'plates', 'misc_images']:
                if key in post.metadata: del post.metadata[key]
            
            if plates: post.metadata['plates'] = plates
            if genitalia: post.metadata['genitalia'] = genitalia
            if misc_images: post.metadata['misc_images'] = misc_images
            
            new_file_content = frontmatter.dumps(post)
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(new_file_content)
            return {"status": "success_live", "book": book_name}

    except Exception as e:
        return {"status": "error", "reason": str(e), "book": book_name}

def generate_html_report(results):
    # This function remains the same as the previous version
    book_stats = collections.defaultdict(lambda: {"files": 0, "success": 0, "errors": 0, "skips": 0, "warnings": 0, "total_plates": 0, "labels_found": 0})
    
    for res in results.values():
        book = res.get('book', 'Unknown'); book_stats[book]['files'] += 1; status = res.get('status', 'error')
        if status == 'success':
            book_stats[book]['success'] += 1
            # Exclude default image from stats
            plate_list = [p for p in res.get('plates', []) if p['url'] != DEFAULT_IMAGE_URL]
            book_stats[book]['total_plates'] += len(plate_list)
            book_stats[book]['labels_found'] += sum(1 for img in plate_list if img['label'])
        elif status == 'error': book_stats[book]['errors'] += 1
        elif status == 'skip': book_stats[book]['skips'] += 1
        elif status == 'warning': book_stats[book]['warnings'] += 1

    table_rows = []
    grand_totals = {"files": 0, "success": 0, "errors": 0, "total_plates": 0, "labels_found": 0}
    for book, stats in sorted(book_stats.items()):
        for key in grand_totals: grand_totals[key] += stats.get(key, 0)
        label_rate = (stats['labels_found'] / stats['total_plates'] * 100) if stats['total_plates'] > 0 else 0
        table_rows.append(f"""
        <tr><td>{book}</td><td>{stats['success']} / {stats['files']}</td>
            <td>{stats['errors']}</td><td>{stats['total_plates']}</td>
            <td>{stats['labels_found']}</td><td>{label_rate:.1f}%</td>
        </tr>""")
    
    total_label_rate = (grand_totals['labels_found'] / grand_totals['total_plates'] * 100) if grand_totals['total_plates'] > 0 else 0
    total_row = f"""
    <tr class="total-row">
        <td><b>Grand Total</b></td><td><b>{grand_totals['success']} / {grand_totals['files']}</b></td>
        <td><b>{grand_totals['errors']}</b></td><td><b>{grand_totals['total_plates']}</b></td>
        <td><b>{grand_totals['labels_found']}</b></td><td><b>{total_label_rate:.1f}%</b></td>
    </tr>"""
    table_body_html = "".join(table_rows) + total_row

    errors_html = "".join([f"<li><b>{file}:</b> {res['reason']} <i>(Book: {res.get('book', 'N/A')})</i></li>" for file, res in sorted(results.items()) if res['status'] == 'error'])
    
    warnings_list = []
    for file, res in sorted(results.items()):
        if res['status'] == 'warning':
            warnings_list.append(f"<li><b>{file}:</b> {res['reason']} <i>(Book: {res.get('book', 'N/A')})</i></li>")
        if res.get('warnings'): # Includes warnings from 'success' status
            for w in res['warnings']:
                warnings_list.append(f"<li><b>{file}:</b> {w} <i>(Book: {res.get('book', 'N/A')})</i></li>")
    warnings_html = "".join(warnings_list)

    success_results = {k: v for k, v in results.items() if v['status'] == 'success'}
    sorted_success = sorted(success_results.items(), key=lambda item: item[1].get('book', 'Unknown'))
    detailed_html = ""
    for book, group in groupby(sorted_success, key=lambda item: item[1].get('book', 'Unknown')):
        detailed_html += f"<div class='results-section'><h2>Book: {book}</h2>"
        for file, res in group:
            detailed_html += f"<h3>{file}</h3>"
            if res.get('plates'):
                detailed_html += f"<h4>Plates ({len(res['plates'])})</h4><ul>{''.join([f'<li><code>{str(img)}</code></li>' for img in res['plates']])}</ul>"
            if res.get('genitalia'):
                detailed_html += f"<h4>Genitalia ({len(res['genitalia'])})</h4><ul>{''.join([f'<li><code>{str(gen)}</code></li>' for gen in res['genitalia']])}</ul>"
            if res.get('misc_images'):
                detailed_html += f"<h4>Misc Images ({len(res['misc_images'])})</h4><ul>{''.join([f'<li><code>{str(misc)}</code></li>' for misc in res['misc_images']])}</ul>"
        detailed_html += "</div>"

    html = f"""
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Image Update Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; margin: 0; background-color: #f9f9f9; color: #333; }}
        .container {{ max-width: 900px; margin: 2em auto; background: white; padding: 2em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .summary, .results-section {{ border: 1px solid #ddd; padding: 1.5em; margin-bottom: 2em; border-radius: 8px; }}
        h1, h2, h3, h4 {{ color: #333; }} h2 {{ border-bottom: 1px solid #eee; padding-bottom: 0.5em;}}
        code {{ background-color: #eee; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.9em; word-break: break-all; }}
        pre code {{ display: block; white-space: pre-wrap; padding: 1em; margin-top: 0.5em;}}
        li {{ margin-bottom: 1em; }} .warning-item, .error-item {{ color: #c0392b; }} .warning-item b {{ color: #9d2b28; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
        thead th {{ background-color: #f2f2f2; cursor: pointer; user-select: none; }}
        thead th:hover {{ background-color: #e9e9e9; }}
        .total-row {{ background-color: #e8f4fd; font-weight: bold; }}
        .footer {{ text-align: center; color: #777; font-size: 0.9em; margin-top: 2em; }}
    </style></head>
    <body><div class="container">
        <h1>🖼️ Image Update Dry Run Report</h1>
        <div class="summary"><h2>Breakdown by Book</h2><table id="book-table">
            <thead><tr>
                <th onclick="sortTable(0, 'str')">Book Name</th><th onclick="sortTable(1, 'str')">Success/Total</th>
                <th onclick="sortTable(2, 'num')">Errors</th><th onclick="sortTable(3, 'num')">Plates Found</th>
                <th onclick="sortTable(4, 'num')">Labels Found</th><th onclick="sortTable(5, 'num')">Label Rate</th>
            </tr></thead><tbody>{table_body_html}</tbody>
        </table></div>
        <div class="results-section"><h2>Actionable Issues</h2>
            {"<h3>Errors</h3><ul class='error-item'>" + errors_html + "</ul>" if errors_html else ""}
            {"<h3>Warnings</h3><ul class='warning-item'>" + warnings_html + "</ul>" if warnings_html else ""}
        </div>
        <h1>File-by-File Success Details</h1>{detailed_html}
        <div class="footer"><p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p></div>
    </div>
    <script>
        let sortDirection = {{}};
        function sortTable(col, type) {{
            const table = document.getElementById("book-table");
            const tbody = table.querySelector("tbody");
            const rows = Array.from(tbody.querySelectorAll("tr"));
            const totalRow = document.querySelector('.total-row');
            if (totalRow) rows.pop(); // Exclude total row from sorting
            const dir = sortDirection[col] === 'asc' ? 'desc' : 'asc';
            sortDirection = {{ [col]: dir }};
            rows.sort((a, b) => {{
                let aText = a.cells[col].textContent.trim(); let bText = b.cells[col].textContent.trim();
                if (type === 'num') {{
                    const aNum = parseFloat(aText.replace('%', '')); const bNum = parseFloat(bText.replace('%', ''));
                    return dir === 'asc' ? aNum - bNum : bNum - aNum;
                }} else {{
                    if (aText.includes('/')) aText = eval(aText); if (bText.includes('/')) bText = eval(bText);
                    return dir === 'asc' ? String(aText).localeCompare(bText, undefined, {{numeric: true}}) : String(bText).localeCompare(aText, undefined, {{numeric: true}});
                }}
            }});
            tbody.innerHTML = ""; rows.forEach(row => tbody.appendChild(row));
            if (totalRow) tbody.appendChild(totalRow); // Re-add total row at the end
        }}
    </script>
    </body></html>"""
    with open(REPORT_FILENAME, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n✅ Dry run complete. Report generated: {REPORT_FILENAME}")

def main():
    # This function remains the same
    parser = argparse.ArgumentParser(description="Scrape and update image URLs in markdown frontmatter.")
    parser.add_argument(
        '--live-run', action='store_true',
        help="Actually modify the files. Default is a dry run that generates a report."
    )
    args = parser.parse_args()
    results = {}
    total_updated = 0
    all_files = list(MARKDOWN_DIR.glob('**/*.md*'))
    print(f"Found {len(all_files)} markdown files to process...")
    for markdown_path in all_files:
        if not markdown_path.is_file():
            continue
        result = process_file(markdown_path, dry_run=not args.live_run)
        if args.live_run:
            status_msg = result['status'].upper()
            if result['status'] == 'success_live':
                status_msg = "✅ SUCCESS"
                total_updated += 1
            elif result['status'] == 'skip':
                 status_msg = "ℹ️ SKIPPED"
            else:
                status_msg = f"❌ {status_msg}"
            print(f"-> {markdown_path.name}: {status_msg}")
        else:
            results[markdown_path.name] = result
    if not args.live_run:
        generate_html_report(results)
    else:
        print(f"\n✨ Live run complete. Updated {total_updated} file(s).")

if __name__ == "__main__":
    main()