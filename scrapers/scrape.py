import collections
import re
from pathlib import Path
import frontmatter
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# --- Configuration ---
MARKDOWN_DIR = Path("./src/content/species/")
PHP_ROOT_DIR = Path("../MoB-PHP/")
TARGET_BOOK = "seven" # The 'book' value in frontmatter to target

def format_headings_and_cleanup(markdown_text):
    """
    Applies a robust "re-flowing" strategy to format the text correctly.
    """
    processed_text = re.sub(r'^\s*\*\*\*.*\n', '', markdown_text.strip(), count=1)
    processed_text = re.sub(r'\s+', ' ', processed_text)

    def create_replacer(heading_str):
        return lambda match: f"\n\n{heading_str}\n\n"

    def create_holotype_replacer(match):
        symbol = match.group(1) or ""
        return f"\n\n### Holotype {symbol.strip()}\n\n"

    rules = {
        re.compile(r'\*Taxonomic notes?[\.:]?\*', re.IGNORECASE): create_replacer("### Taxonomic Notes"),
        re.compile(r'\*Paratypes?[\.:]?\*', re.IGNORECASE): create_replacer("### Paratype"),
        re.compile(r'\*Holotype[\.:]?\*\s*(♂|♀)?', re.IGNORECASE): create_holotype_replacer,
        re.compile(r'\*Diagnosis[\.:]?\*', re.IGNORECASE): create_replacer("### Diagnosis"),
        re.compile(r'\*Geographical range[\.:]?\*', re.IGNORECASE): create_replacer("### Geographical range"),
        re.compile(r'\*Habitat preference[\.:]?\*', re.IGNORECASE): create_replacer("### Habitat preference"),
        re.compile(r'\*Biology[\.:]?\*', re.IGNORECASE): create_replacer("### Biology"),
    }

    for pattern, replacer in rules.items():
        processed_text = pattern.sub(replacer, processed_text)
        
    processed_text = re.sub(r'(♂|♀)(?=[a-zA-Z0-9])', r'\1 ', processed_text)
    processed_text = re.sub(r'(?<=[a-zA-Z0-9])(♂|♀)', r' \1', processed_text)

    processed_text = re.sub(
        r'([a-z]{2,})\.\s+(?=[A-Z])', 
        r'\1.\n\n', 
        processed_text
    )
    
    processed_text = re.sub(r'\n\s*\.\s*', '\n', processed_text)
    processed_text = re.sub(r'\n\s+', '\n', processed_text)
    processed_text = re.sub(r'\n{3,}', '\n\n', processed_text)
    
    return processed_text.strip()


def scrape_and_fill(post, markdown_path):
    legacy_url = post.metadata.get("legacy_url")
    if not legacy_url:
        print(f"  - ❌ SKIPPING: No 'legacy_url' found.")
        return

    relative_path = legacy_url.replace("https://www.mothsofborneo.com/", "")
    php_path = PHP_ROOT_DIR / relative_path

    if not php_path.exists():
        print(f"  - ❌ SKIPPING: Source PHP file not found at '{php_path}'")
        return

    print(f"  - 🔎 Reading source: {php_path.name}")
    with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    nav_link = soup.find(string=re.compile(r'Return\s+to\s+Contents\s+page'))
    if nav_link:
        nav_parent = nav_link.find_parent('p')
        if nav_parent:
            print("  - 🧹 Removing navigation links from HTML.")
            nav_parent.decompose()

    selector = 'p[id="content"]'
    content_paragraphs = soup.select(selector)

    if not content_paragraphs:
        print(f"  - ❌ SKIPPING: No matching content paragraphs found.")
        return

    for p in content_paragraphs:
        for italic_tag in p.find_all('i'):
            if italic_tag.string and '\n' in italic_tag.string:
                italic_tag.string.replace_with(italic_tag.string.replace('\n', ' '))
                print("  - 🧹 Fixing multi-line heading in HTML.")

    html_content = "".join(str(p) for p in content_paragraphs)
    raw_markdown = md(html_content, heading_style="ATX")
    
    clean_markdown = format_headings_and_cleanup(raw_markdown)

    post.content = clean_markdown
    new_file_content = frontmatter.dumps(post)
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(new_file_content)
    
    print(f"  - ✅ SUCCESS: Content scraped and written to {markdown_path.name}")

def main():
    if not MARKDOWN_DIR.is_dir() or not PHP_ROOT_DIR.is_dir():
        print("Error: Make sure both MARKDOWN_DIR and PHP_ROOT_DIR paths are correct.")
        return

    print(f"🚀 Starting scraper for book '{TARGET_BOOK}'...")
    
    processed_files = 0
    for markdown_path in MARKDOWN_DIR.glob('**/*.md*'):
        if not markdown_path.is_file():
            continue
        
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            if not post.content.strip() and post.metadata.get("book") == TARGET_BOOK:
                print(f"Processing '{markdown_path.name}'...")
                scrape_and_fill(post, markdown_path)
                processed_files += 1

        except Exception as e:
            print(f"  [ERROR] Could not process {markdown_path.name}: {e}")
            
    print(f"\n✨ Scraper finished. Updated {processed_files} file(s).")

if __name__ == "__main__":
    main()