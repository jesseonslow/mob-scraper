# mob-scraper/tasks/scrape_genera.py

import frontmatter
from bs4 import BeautifulSoup
from config import GENERA_DIR, PHP_ROOT_DIR, LEGACY_URL_BASE
from core.file_system import save_markdown_file
from markdownify import markdownify

def run_scrape_genera():
    """
    Scans all genera files and scrapes their body content if it's missing.
    """
    print("🚀 Starting genera scraping process...")
    updated_files_count = 0

    for file_path in GENERA_DIR.glob('**/*.md*'):
        if not file_path.is_file():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)

            if post.content.strip():
                continue

            legacy_url = post.metadata.get('legacy_url')
            if not legacy_url:
                continue

            relative_path = legacy_url.replace(LEGACY_URL_BASE, "")
            php_path = PHP_ROOT_DIR / relative_path

            if not php_path.exists():
                continue

            with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, 'html.parser')
            
            type_species_tag = soup.find(string=lambda text: "type species:" in text.lower())

            if type_species_tag:
                content_start_node = type_species_tag.find_parent('p') or type_species_tag
                
                body_html = ""
                for sibling in content_start_node.find_next_siblings():
                    body_html += str(sibling)
                
                post.content = markdownify(body_html).strip()

                if post.content:
                    save_markdown_file(post, file_path)
                    updated_files_count += 1
                    print(f"  -> Scraped and saved: {file_path.name}")


        except Exception as e:
            print(f"  -> ERROR processing {file_path.name}: {e}")

    print(f"\n✨ Genera scraping finished. Updated {updated_files_count} file(s).")