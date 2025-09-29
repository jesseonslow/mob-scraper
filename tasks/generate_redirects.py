# tasks/generate_redirects.py

import csv
from file_system import build_legacy_to_new_url_map
from config import REPORT_DIR, REDIRECT_REPORT_FILENAME
from reporting import update_index_page

def run_generate_redirects():
    """
    Generates a CSV file mapping legacy URLs to new site paths for redirects.
    """
    print("🚀 Starting redirect map generation...")

    # Use the new, shared utility function to get the URL map
    redirect_map = build_legacy_to_new_url_map()

    if not redirect_map:
        print("No redirect mappings were generated.")
        return

    # Ensure the report directory exists
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORT_DIR / REDIRECT_REPORT_FILENAME

    # Convert the dictionary to a list of lists for the CSV writer
    rows = [[source, destination] for source, destination in redirect_map.items()]

    # Write the data to a CSV file
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['source', 'destination']) # Write header
        writer.writerows(sorted(rows))

    print(f"\n✨ Success! Generated {len(rows)} redirects.")
    print(f"✅ Report saved to: {output_path.resolve()}")
    
    update_index_page()