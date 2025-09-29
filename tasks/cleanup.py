# tasks/cleanup.py

import frontmatter
import re
from pathlib import Path
from bs4 import BeautifulSoup

from config import (
    SPECIES_DIR, PHP_ROOT_DIR, LEGACY_URL_BASE, GROUP_MAPPING,
    FIELDS_TO_DELETE, BOOK_NUMBER_MAP  # <-- Add BOOK_NUMBER_MAP
)
from file_system import save_markdown_file
from scraper import SpeciesScraper, scrape_images_and_labels
from processing import clean_citation_frontmatter

def _update_image_fields(post, genus_name):
    """
    Updates the post's frontmatter with structured and labeled image data.
    """
    legacy_url = post.metadata.get("legacy_url")
    book_name = post.metadata.get("book", "Unknown")

    if not legacy_url or book_name == 'thirteen':
        return post, False

    relative_path = legacy_url.replace(LEGACY_URL_BASE, "")
    php_path = PHP_ROOT_DIR / relative_path
    if not php_path.exists():
        return post, False

    with open(php_path, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # This is the corrected, direct function call
    book_number = BOOK_NUMBER_MAP.get(book_name)
    plates, genitalia, misc_images = scrape_images_and_labels(soup, book_name, book_number)

    # Clean out all old image-related keys before adding new ones
    for key in ['image_urls', 'images', 'genitalia', 'plates', 'misc_images']:
        if key in post.metadata:
            del post.metadata[key]

    if plates: post.metadata['plates'] = plates
    if genitalia: post.metadata['genitalia'] = genitalia
    if misc_images: post.metadata['misc_images'] = misc_images

    return post, True

def _assign_group(post):
    """
    Assigns a group to the post based on its legacy_url.
   
    """
    if 'group' in post.metadata:
        return post, False

    legacy_url = post.metadata.get('legacy_url')
    if not legacy_url:
        return post, False

    for url_part, group_name in GROUP_MAPPING.items():
        if url_part in legacy_url:
            post.metadata['group'] = group_name
            print(f"  - Assigned group: '{group_name}'")
            return post, True

    return post, False

def _remove_fields(post):
    """
    Removes redundant fields and fields with null values.
   
    """
    was_modified = False
    keys_to_delete = list(post.metadata.keys())

    for key in keys_to_delete:
        if key in FIELDS_TO_DELETE:
            del post.metadata[key]
            print(f"  - Removed redundant field: '{key}'")
            was_modified = True
        elif post.metadata.get(key) is None:
            del post.metadata[key]
            print(f"  - Removed null field: '{key}'")
            was_modified = True
            
    return post, was_modified

def _clean_citations(markdown_path):
    """
    Repairs malformed citation blocks in the raw file content.
   
    """
    try:
        # Attempt to load first. If it works, no need to clean.
        with open(markdown_path, 'r', encoding='utf-8-sig') as f:
            frontmatter.load(f)
        return None, False
    except Exception:
        # Parsing failed, so we proceed with cleaning
        content = markdown_path.read_text(encoding='utf-8-sig')
        
        match = re.search(r'^---\s*\n(.*?)\n---\s*(.*)', content, re.DOTALL)
        if not match:
            return None, False
        
        fm_string, body_string = match.groups()
        
        cleaned_fm_string = clean_citation_frontmatter(fm_string)
        
        if cleaned_fm_string != fm_string:
            new_content = f"---\n{cleaned_fm_string}\n---{body_string}"
            repaired_post = frontmatter.loads(new_content)
            print("  - Repaired citations block.")
            return repaired_post, True
            
    return None, False

def run_cleanup(images=False, groups=False, fields=False, citations=False):
    """
    The main task runner for all cleanup operations.
    """
    if not any([images, groups, fields, citations]):
        print("No cleanup tasks selected. Use --help to see available tasks.")
        return

    print("🚀 Starting cleanup process...")
    updated_files_count = 0
    
    all_files = sorted(list(SPECIES_DIR.glob('**/*.md*')))
    total_files = len(all_files)

    for i, markdown_path in enumerate(all_files):
        if not markdown_path.is_file():
            continue

        print(f"[{i+1}/{total_files}] Processing: {markdown_path.name}")
        
        try:
            was_modified = False
            
            # Citation cleaning must run first as it operates on raw text
            if citations:
                repaired_post, modified = _clean_citations(markdown_path)
                if modified:
                    # If citations were fixed, we save immediately and are done with this file
                    save_markdown_file(repaired_post, markdown_path)
                    updated_files_count += 1
                    continue

            # For all other tasks, we load the file once
            with open(markdown_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)

            if images:
                genus_name = post.metadata.get('genus', 'Unknown')
                post, modified = _update_image_fields(post, genus_name)
                if modified: was_modified = True

            if groups:
                post, modified = _assign_group(post)
                if modified: was_modified = True

            if fields:
                post, modified = _remove_fields(post)
                if modified: was_modified = True

            if was_modified:
                save_markdown_file(post, markdown_path)
                updated_files_count += 1
            else:
                print("  - No changes needed.")

        except Exception as e:
            print(f"  [ERROR] Could not process {markdown_path.name}: {e}")

    print(f"\n✨ Cleanup finished. Updated {updated_files_count} file(s).")