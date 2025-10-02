import frontmatter
import re
import yaml
from pathlib import Path
from urllib.parse import urlparse

from config import (
    PHP_ROOT_DIR, LEGACY_URL_BASE, CONTENT_DIR, SPECIES_DIR
)
import config

def get_master_php_urls():
    """
    Crawls the MoB-PHP directory to build a master list of all valid species URLs.
    """
    master_urls = set()
    url_pattern = re.compile(r'([a-zA-Z0-9_-]+)_(\d+)_(\d+)\.php$')
    
    print(f"Scanning for PHP files in '{PHP_ROOT_DIR}'...")
    for php_path in PHP_ROOT_DIR.glob('part-*/**/*.php'):
        if 'images' in [part.lower() for part in php_path.parts]:
            continue
        if not url_pattern.match(php_path.name):
            continue
            
        relative_path = php_path.relative_to(PHP_ROOT_DIR)
        # --- FIX: Normalize URL to lowercase ---
        url = f"{LEGACY_URL_BASE}{relative_path.as_posix()}".lower()
        master_urls.add(url)
        
    print(f"Found {len(master_urls)} potential species pages in source files.")
    return master_urls

def index_entries_by_url(directory: Path):
    """
    Scans a markdown directory and returns a map of legacy_url to its frontmatter data.
    """
    print(f"Building legacy_url index for '{directory.name}'...")
    url_map = {}
    for md_path in directory.glob('**/*.md*'):
        if not md_path.is_file():
            continue
        try:
            with open(md_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            legacy_url = post.metadata.get('legacy_url')
            if legacy_url:
                # --- FIX: Normalize URL to lowercase ---
                url_map[legacy_url.lower()] = post.metadata
        except Exception:
            continue
    print(f"Indexed {len(url_map)} entries by legacy_url.")
    return url_map

def index_entries_by_slug(directory: Path):
    """
    Scans a markdown directory and returns a map of the file's slug to its frontmatter data.
    """
    print(f"Building slug index for '{directory.name}'...")
    slug_map = {}
    for md_path in directory.glob('**/*.md*'):
        if not md_path.is_file():
            continue
        try:
            with open(md_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            slug_map[md_path.stem] = post.metadata
        except Exception:
            continue
    print(f"Indexed {len(slug_map)} entries by slug.")
    return slug_map

def update_config_file(book_name, confirmed_rules):
    """
    Safely reads, updates, and writes back the scraping_rules.yaml file.
    """
    print(f"\nUpdating 'scraping_rules.yaml' with new rules for book '{book_name}'...")
    try:
        current_rules = config.SCRAPING_RULES
        current_rules[book_name] = confirmed_rules
        sorted_rules = dict(sorted(current_rules.items()))
        rules_path = config.CONFIG_DIR / 'scraping_rules.yaml'
        with open(rules_path, 'w', encoding='utf-8') as f:
            yaml.dump(sorted_rules, f, default_flow_style=False, sort_keys=False, indent=2)
        print("✅ Config file updated successfully!")
        
        config.SCRAPING_RULES = sorted_rules

    except Exception as e:
        print(f"❌ Failed to update config file: {e}")

def save_markdown_file(post: frontmatter.Post, filepath: Path):
    """
    Safely saves a frontmatter.Post object to a file.
    """
    try:
        new_file_content = frontmatter.dumps(post)
        filepath.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_file_content)
        print(f"  -> ✅ Saved: {filepath.name}")
        return True
    except Exception as e:
        print(f"  -> ❌ ERROR: Could not save file {filepath.name}: {e}")
        return False

def build_legacy_to_new_url_map():
    """
    Scans the entire content directory to build a mapping of old legacy URL paths
    to their new, correct site paths (e.g., /species/slug).
    This is a shared utility for redirects and link rewriting.
    """
    print("Building legacy-to-new URL map...")
    url_map = {}
    content_dir = config.CONTENT_DIR
    
    if not content_dir.is_dir():
        print(f"  -> WARNING: Content directory not found at '{content_dir}'.")
        return {}

    all_files = list(content_dir.glob('**/*.md*'))
    
    for md_path in all_files:
        if not md_path.is_file():
            continue
        try:
            with open(md_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            
            legacy_url = post.metadata.get('legacy_url')
            if legacy_url:
                source_path = urlparse(legacy_url.lower()).path
                subfolder = md_path.parent.name
                destination_path = f"/{subfolder}/{md_path.stem}"
                url_map[source_path] = destination_path
        except Exception:
            continue
            
    print(f"  -> Successfully mapped {len(url_map)} URLs.")
    return url_map

def get_all_referenced_genera():
    """
    Scans all species files and returns a set of all unique 'genus' slugs.
    """
    print("Finding all referenced genera from species files...")
    referenced_genera = set()
    for md_path in SPECIES_DIR.glob('**/*.md*'):
        if not md_path.is_file():
            continue
        try:
            with open(md_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
            genus = post.metadata.get('genus')
            if genus:
                referenced_genera.add(genus)
        except Exception:
            continue
    print(f"Found {len(referenced_genera)} unique referenced genera.")
    return referenced_genera