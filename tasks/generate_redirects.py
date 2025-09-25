import csv
import frontmatter
from urllib.parse import urlparse

from config import MARKDOWN_DIR, REPORT_DIR, REDIRECT_REPORT_FILENAME
from reporting import update_index_page

def run_generate_redirects():
    """
    Generates a CSV file mapping legacy URLs to new site paths for redirects.
    """
    print("🚀 Starting redirect map generation...")

    redirect_map = []
    # Use glob to find all markdown files in the species directory
    all_species_files = list(MARKDOWN_DIR.glob('**/*.md*'))
    total_files = len(all_species_files)
    print(f"Found {total_files} species files to process.")

    for i, md_path in enumerate(all_species_files):
        if not md_path.is_file():
            continue
        
        print(f"[{i+1}/{total_files}] Processing: {md_path.name}")
        
        try:
            with open(md_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            
            legacy_url = post.metadata.get('legacy_url')
            if legacy_url:
                # Extract the path from the full legacy URL (e.g., /part-11/...)
                source_path = urlparse(legacy_url).path
                
                # The new path is based on the file's slug
                destination_path = f"/species/{md_path.stem}"
                
                redirect_map.append([source_path, destination_path])
            else:
                print(f"  - ⚠️ WARNING: No 'legacy_url' found in {md_path.name}")

        except Exception as e:
            print(f"  - ❌ ERROR: Could not process {md_path.name}: {e}")

    if not redirect_map:
        print("No redirect mappings were generated.")
        return

    # Ensure the report directory exists
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORT_DIR / REDIRECT_REPORT_FILENAME

    # Write the data to a CSV file
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['source', 'destination']) # Write header
        writer.writerows(sorted(redirect_map))

    print(f"\n✨ Success! Generated {len(redirect_map)} redirects.")
    print(f"✅ Report saved to: {output_path.resolve()}")
    
    # Optional: Update the main index page to show the new report
    update_index_page()