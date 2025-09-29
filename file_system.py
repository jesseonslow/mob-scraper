# mob-scraper/file_system.py

import frontmatter
import re
import ast
import pprint
from pathlib import Path
import config
from config import (
    PHP_ROOT_DIR, LEGACY_URL_BASE, CONFIG_PATH, RULES_VAR_NAME
)

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
        url = f"{LEGACY_URL_BASE}{relative_path.as_posix()}"
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
            if post.metadata.get('legacy_url'):
                url_map[post.metadata['legacy_url']] = post.metadata
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
    Safely reads, updates, and writes back the configuration file using an Abstract Syntax Tree (AST).
    This method is robust against formatting changes and guarantees syntactically correct output.
    """
    print(f"\nUpdating '{CONFIG_PATH}' with new rules for book '{book_name}'...")
    try:
        content = CONFIG_PATH.read_text(encoding='utf-8')
        tree = ast.parse(content)

        # Find the assignment node for BOOK_SCRAPING_RULES
        assignment_node = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and
                    len(node.targets) == 1 and
                    isinstance(node.targets[0], ast.Name) and
                    node.targets[0].id == RULES_VAR_NAME):
                assignment_node = node
                break
        
        if not assignment_node or not isinstance(assignment_node.value, ast.Dict):
            print(f"Error: Could not find the '{RULES_VAR_NAME}' dictionary in {CONFIG_PATH}.")
            return

        # Convert the AST dictionary to a Python dictionary
        current_rules = ast.literal_eval(assignment_node.value)
        
        # Update the rules for the specific book
        current_rules[book_name] = confirmed_rules
        
        # Sort the dictionary by book name for consistent ordering
        sorted_rules = dict(sorted(current_rules.items()))

        # Find the line numbers of the dictionary to replace
        start_line = assignment_node.lineno
        end_line = assignment_node.end_lineno
        
        original_lines = content.splitlines(keepends=True)
        lines_before = original_lines[:start_line-1]
        lines_after = original_lines[end_line:]

        # Pretty-print the updated dictionary to a string
        new_rules_str = pprint.pformat(sorted_rules, indent=4, width=120)
        
        # Reconstruct the file
        new_content = "".join(lines_before)
        new_content += f"{RULES_VAR_NAME} = {new_rules_str}\n"
        new_content += "".join(lines_after)

        CONFIG_PATH.write_text(new_content, encoding='utf-8')
        print("✅ Config file updated successfully!")

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
                source_path = urlparse(legacy_url).path
                subfolder = md_path.parent.name
                destination_path = f"/{subfolder}/{md_path.stem}"
                url_map[source_path] = destination_path
        except Exception:
            continue
            
    print(f"  -> Successfully mapped {len(url_map)} URLs.")
    return url_map

def create_markdown_file(entry_data: dict, scraped_data: dict, book_name: str):
    """
    Creates and saves a new markdown file for a species from scraped data.
    """
    url = entry_data['url']
    neighbor_data = entry_data['neighbor_data']
    
    # --- GENUS CLEANING SOLUTION ---
    # 1. Get the raw genus name.
    raw_genus = scraped_data.get('genus')
    
    # 2. Clean it for use in the frontmatter and slug.
    #    - Remove any leading/trailing whitespace.
    #    - Convert to lowercase.
    #    - Remove any character that is not a standard letter.
    clean_genus = ""
    if raw_genus:
        clean_genus = re.sub(r'[^a-z]', '', raw_genus.strip().lower())

    # --- SLUG CREATION ---
    name_for_slug = scraped_data.get('name', 'unknown').lower().replace('sp. ', 'sp-').replace(' ', '-').replace('?', '').replace('.', '')
    # Use the cleaned genus for the slug.
    slug = f"{clean_genus.replace(' ', '-')}-{name_for_slug}"
    filepath = config.SPECIES_DIR / f"{slug}.md"
    
    if filepath.exists():
        print(f"  -> ℹ️ SKIPPING: File already exists at {filepath.name}")
        return

    # --- FRONTMATTER CREATION ---
    new_metadata = {
        'name': scraped_data.get('name'),
        'author': scraped_data.get('author'),
        'legacy_url': url,
        'book': book_name,
        'family': neighbor_data.get('family'),
        'subfamily': neighbor_data.get('subfamily'),
        'tribe': neighbor_data.get('tribe'),
        'genus': clean_genus,
        'group': neighbor_data.get('group'),
        'taxonomic_status': scraped_data.get('taxonomic_status', []),
        'plates': scraped_data.get('plates', []),
        'genitalia': scraped_data.get('genitalia', []),
        'misc_images': scraped_data.get('misc_images', []),
        'citations': []
    }
    
    post = frontmatter.Post(content=scraped_data.get('body_content', ''))
    
    # --- PLATES SAVING SOLUTION ---
    # Change the filter from 'if v' to 'if v is not None'.
    # This will correctly save fields with empty lists (`[]`) as their value.
    post.metadata = {k: v for k, v in new_metadata.items() if v is not None}
    
    save_markdown_file(post, filepath)