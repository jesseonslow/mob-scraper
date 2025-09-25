# mob-scraper/file_system.py

import frontmatter
import re
from pathlib import Path
from config import PHP_ROOT_DIR, LEGACY_URL_BASE

def get_master_php_urls():
    """
    Crawls the MoB-PHP directory to build a master list of all valid species URLs.
    
    This function is crucial for discovering which species exist on the legacy site,
    forming the basis for audit and scraping tasks.
    """
    master_urls = set()
    # This pattern specifically targets species pages (e.g., 'genus_1_2.php') and ignores genus pages (e.g., 'genus_1.php')
    url_pattern = re.compile(r'([a-zA-Z0-9_-]+)_(\d+)_(\d+)\.php$')
    
    print(f"Scanning for PHP files in '{PHP_ROOT_DIR}'...")
    for php_path in PHP_ROOT_DIR.glob('part-*/**/*.php'):
        # Skip any files within an 'images' directory
        if 'images' in [part.lower() for part in php_path.parts]:
            continue
        if not url_pattern.match(php_path.name):
            continue
            
        relative_path = php_path.relative_to(PHP_ROOT_DIR)
        url = f"{LEGACY_URL_BASE}{relative_path.as_posix()}"
        master_urls.add(url)
        
    print(f"Found {len(master_urls)} potential species pages in source files.")
    return master_urls

def index_entries_by_url(directory: Path):
    """
    Scans a markdown directory and returns a map of legacy_url to its frontmatter data.
    
    This creates a fast lookup index to check for the existence of a page based on its
    original URL, preventing duplicate entries.
    """
    print(f"Building legacy_url index for '{directory.name}'...")
    url_map = {}
    for md_path in directory.glob('**/*.md*'):
        if not md_path.is_file():
            continue
        try:
            with open(md_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            if post.metadata.get('legacy_url'):
                url_map[post.metadata['legacy_url']] = post.metadata
        except Exception:
            # Silently continue if a file is malformed, to avoid crashing the whole process.
            continue
    print(f"Indexed {len(url_map)} entries by legacy_url.")
    return url_map

def index_entries_by_slug(directory: Path):
    """
    Scans a markdown directory and returns a map of the file's slug to its frontmatter data.
    
    This is useful for finding parent genera, especially in cases where the legacy_url
    is not consistently formatted (e.g., for Book 4).
    """
    print(f"Building slug index for '{directory.name}'...")
    slug_map = {}
    for md_path in directory.glob('**/*.md*'):
        if not md_path.is_file():
            continue
        try:
            with open(md_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            # The 'stem' is the filename without the extension (e.g., 'my-file.md' -> 'my-file')
            slug_map[md_path.stem] = post.metadata
        except Exception:
            continue
    print(f"Indexed {len(slug_map)} entries by slug.")
    return slug_map

def save_markdown_file(post: frontmatter.Post, filepath: Path):
    """
    Safely saves a frontmatter.Post object to a file.

    Args:
        post: The frontmatter Post object containing metadata and content.
        filepath: The Path object representing the destination file.
    """
    try:
        new_file_content = frontmatter.dumps(post)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_file_content)
        print(f"  -> ✅ Saved changes to {filepath.name}")
        return True
    except Exception as e:
        print(f"  -> ❌ ERROR: Could not save file {filepath.name}: {e}")
        return False