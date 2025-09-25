import frontmatter
from pathlib import Path
import re
from config import PHP_ROOT_DIR, LEGACY_URL_BASE

def get_master_php_urls():
    """Crawls the MoB-PHP directory to build a master list of all valid species URLs."""
    master_urls = set()
    url_pattern = re.compile(r'([a-zA-Z0-9_-]+)_(\d+)_(\d+)\.php$')
    for php_path in PHP_ROOT_DIR.glob('part-*/**/*.php'):
        if 'images' in [part.lower() for part in php_path.parts]: continue
        if not url_pattern.match(php_path.name): continue
        relative_path = php_path.relative_to(PHP_ROOT_DIR)
        url = f"{LEGACY_URL_BASE}{relative_path.as_posix()}"
        master_urls.add(url)
    print(f"Found {len(master_urls)} potential species pages in source files.")
    return master_urls

def get_existing_entries_by_url(directory):
    """Scans a markdown directory and returns a map of legacy_url to its frontmatter data."""
    print(f"Building legacy_url index for {directory.name}...")
    url_map = {}
    for md_path in directory.glob('**/*.md*'):
        if not md_path.is_file(): continue
        try:
            with open(md_path, 'r', encoding='utf-8') as f: post = frontmatter.load(f)
            if post.metadata.get('legacy_url'):
                url_map[post.metadata['legacy_url']] = post.metadata
        except Exception: continue
    print(f"Indexed {len(url_map)} entries by legacy_url.")
    return url_map

def get_existing_entries_by_slug(directory):
    """Scans a markdown directory and returns a map of slug to its frontmatter data."""
    print(f"Building slug index for {directory.name}...")
    slug_map = {}
    for md_path in directory.glob('**/*.md*'):
        if not md_path.is_file(): continue
        try:
            with open(md_path, 'r', encoding='utf-8') as f: post = frontmatter.load(f)
            slug_map[md_path.stem] = post.metadata
        except Exception: continue
    print(f"Indexed {len(slug_map)} entries by slug.")
    return slug_map