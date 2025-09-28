# mob-scraper/file_system.py

import frontmatter
import re
import ast
import pprint
from pathlib import Path
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
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_file_content)
        print(f"  -> ✅ Saved changes to {filepath.name}")
        return True
    except Exception as e:
        print(f"  -> ❌ ERROR: Could not save file {filepath.name}: {e}")
        return False