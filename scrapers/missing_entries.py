import argparse
import re
from pathlib import Path
import frontmatter
from bs4 import BeautifulSoup, NavigableString
import collections
from datetime import datetime
from html import escape
from markdownify import markdownify as md
from itertools import groupby

# --- Configuration ---
MARKDOWN_DIR = Path("./src/content/species/")
GENERA_DIR = Path("./src/content/genera/")
PHP_ROOT_DIR = Path("../MoB-PHP/")
REPORT_FILENAME = "audit_report.html"
LEGACY_URL_BASE = "https://www.mothsofborneo.com/"
DEFAULT_PLATE = [{"url": "https://cdn.mothsofborneo.com/images/default.png", "label": ""}]
CDN_BASE_URL = "https://cdn.mothsofborneo.com"

BOOK_WORD_MAP = {
    '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
    '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten',
    '11': 'eleven', '12': 'twelve', '13': 'thirteen', '14': 'fourteen',
    '15-16': 'fifteen', '16': 'sixteen', '17': 'seventeen', '18': 'eighteen'
}
BOOK_NUMBER_MAP = {v: k.split('-')[0] for k, v in BOOK_WORD_MAP.items()}

BOOK_CONTENT_SELECTORS = {
    'three': 'p[align="justify"]', 'four': 'p[align="justify"]',
    'five': 'p[align="justify"], p[class="MsoNormal"][style*="text-align:justify"], p[class="MsoNormal"][align="justify"]',
    'eight': 'p[align="justify"], p[style*="text-align:justify"]',
    'nine': 'p[style*="text-align:justify"]',
}

def format_headings_and_cleanup(markdown_text):
    """Applies a robust "re-flowing" strategy to format the text correctly."""
    processed_text = re.sub(r'^\s*\*\*\*.*\n', '', markdown_text.strip(), count=1)
    processed_text = re.sub(r'\s+', ' ', processed_text)
    def create_replacer(heading_str): return lambda match: f"\n\n{heading_str}\n\n"
    def create_holotype_replacer(match):
        symbol = match.group(1) or ""; return f"\n\n### Holotype {symbol.strip()}\n\n"
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
    
    # Clean up stray periods that are now at the start of a line
    processed_text = re.sub(r'\n\s*\.\s+', '\n', processed_text)
    
    processed_text = re.sub(r'([a-z]{2,})\.\s+(?=[A-Z])', r'\1.\n\n', processed_text)
    processed_text = re.sub(r'\n{3,}', '\n\n', processed_text)
    return processed_text.strip()

def scrape_images_and_labels(soup, book_name):
    """Implementation of the robust image and label scraper."""
    plates, genitalia, misc_images = [], [], []
    book_number = BOOK_NUMBER_MAP.get(book_name)
    if not book_number: return plates, genitalia, misc_images

    plate_tags = []
    all_img_tags = soup.find_all('img')
    for img in all_img_tags:
        src = img.get('src', '')
        clean_src = src.replace('../images/', '').replace('../', '')
        cdn_url = f"{CDN_BASE_URL}/{book_number}/{clean_src}"
        filename = Path(cdn_url).name.lower()
        is_plate, is_genitalia, is_misc = False, False, False
        if book_name == 'three':
            if re.match(r'^p.*?\d+.*', filename): is_plate = True
            elif re.match(r'^\d+\..*', filename): is_genitalia = True
            else: is_misc = True
        else:
            if 'plate' in cdn_url.lower(): is_plate = True
            elif 'genitalia' in cdn_url.lower(): is_genitalia = True
            else: is_misc = True
        if is_plate: plate_tags.append(img)
        elif is_genitalia: genitalia.append(cdn_url)
        elif is_misc: misc_images.append(cdn_url)

    if not plate_tags: return plates, genitalia, misc_images
    
    label_strings = []
    for element in soup.find_all(['td', 'p']):
        text = element.get_text()
        if re.search(r'(♂|♀|\(holotype\)|\(paratype\))', text, re.IGNORECASE):
            label_parts = []
            symbol_match = re.search(r'(♂|♀)', text); type_match = re.search(r'(\(holotype\)|\(paratype\))', text, re.IGNORECASE)
            if symbol_match: label_parts.append(symbol_match.group(0))
            if type_match: label_parts.append(type_match.group(0).lower())
            label_strings.append(' '.join(label_parts))
    
    label_map = {tag.get('src'): label_strings[i] for i, tag in enumerate(plate_tags) if i < len(label_strings)}
    
    for tag in plate_tags:
        src = tag.get('src')
        clean_src = src.replace('../images/', '').replace('../', '')
        cdn_url = f"{CDN_BASE_URL}/{book_number}/{clean_src}"
        plates.append({'url': cdn_url, 'label': label_map.get(src)})
    return plates, genitalia, misc_images

def scrape_name_author_status(soup, genus_name):
    """Scrapes the name, author, and taxonomic status from the soup."""
    name_tag = soup.find('b')
    if not name_tag: return {"name": "Unknown", "author": None, "taxonomic_status": []}

    # 1. Pre-process text: remove brackets, clean corrupted chars and quotes
    raw_text = name_tag.get_text(strip=True, separator=' ')
    processed_text = re.sub(r'\[.*?\]', ' ', raw_text)
    clean_text = processed_text.replace('', '').replace('"', '').replace("'", "").strip()
    clean_genus = genus_name.replace('"', '').replace("'", "")

    # 2. Extract taxonomic statuses
    statuses = []
    status_patterns = [r'sp\.\s*n\.', r'comb\.\s*n\.', r'sp\.\s*rev\.', r'comb\.\s*rev\.']
    temp_text = clean_text
    for pattern in status_patterns:
        match = re.search(pattern, temp_text, re.IGNORECASE)
        if match:
            statuses.append(match.group(0))
            temp_text = temp_text.replace(match.group(0), '')
    
    # 3. Extract Author (simple heuristic: last capitalized word(s))
    author = None
    parts = temp_text.split()
    author_parts = []
    for part in reversed(parts):
        if part.istitle() or part.isupper() or (part.startswith('(') and part.endswith(')')):
            author_parts.insert(0, part)
        else:
            break
    if author_parts:
        author = " ".join(author_parts)
        temp_text = temp_text.replace(author, '').strip()

    # 4. Extract Name by removing genus
    name = re.sub(f'^{re.escape(clean_genus)}', '', temp_text, flags=re.IGNORECASE).strip()

    # 5. Handle special rules
    if 'sp. n.' in [s.lower() for s in statuses]:
        author = "Holloway"

    return {"name": name or "Unknown", "author": author, "taxonomic_status": statuses}

def get_master_php_urls():
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

def get_contextual_data(missing_url, existing_species, existing_genera_by_url, existing_genera_by_slug):
    url_pattern = re.compile(r'(.+)_(\d+)_(\d+)\.php$')
    match = url_pattern.search(missing_url)
    if not match: return None, None
    base, major, minor = match.groups()
    neighbor_minor = int(minor) - 1
    if neighbor_minor > 0:
        neighbor_url = f"{base}_{major}_{neighbor_minor}.php"
        neighbor_data = existing_species.get(neighbor_url)
        if neighbor_data: return neighbor_data, 'species'
    genus_url = f"{base}_{major}.php"
    genus_data = existing_genera_by_url.get(genus_url)
    if genus_data: return genus_data, 'genus by URL'
    if '/part-4/' in missing_url:
        try:
            genus_slug = missing_url.split('/part-4/', 1)[1].split('/')[0]
            genus_data = existing_genera_by_slug.get(genus_slug)
            if genus_data: return genus_data, 'genus by slug'
        except IndexError: pass
    try:
        weird_genus_url = f"{base}_{major}_1.php"
        genus_data = existing_genera_by_url.get(weird_genus_url)
        if genus_data: return genus_data, 'genus by unusual URL'
    except (AttributeError, IndexError): pass
    return None, None

def scrape_images_and_labels(soup, book_name):
    """Re-implementation of the robust image and label scraper."""
    plates, genitalia, misc_images = [], [], []
    book_number = BOOK_NUMBER_MAP.get(book_name)
    if not book_number:
        return plates, genitalia, misc_images # Cannot build URLs

    # Positional Mapping Logic
    plate_tags = []
    all_img_tags = soup.find_all('img')

    for img in all_img_tags:
        src = img.get('src', '')
        # Convert to full CDN URL to categorize
        clean_src = src.replace('../images/', '').replace('../', '')
        cdn_url = f"{CDN_BASE_URL}/{book_number}/{clean_src}"
        filename = Path(cdn_url).name.lower()
        
        is_plate, is_genitalia, is_misc = False, False, False
        if book_name == 'three':
            if re.match(r'^p.*?\d+.*', filename): is_plate = True
            elif re.match(r'^\d+\..*', filename): is_genitalia = True
            else: is_misc = True
        else:
            if 'plate' in cdn_url.lower(): is_plate = True
            elif 'genitalia' in cdn_url.lower(): is_genitalia = True
            else: is_misc = True
        
        if is_plate: plate_tags.append(img)
        elif is_genitalia: genitalia.append(cdn_url)
        elif is_misc: misc_images.append(cdn_url)

    if not plate_tags:
        return plates, genitalia, misc_images
    
    label_strings = []
    for element in soup.find_all(['td', 'p']):
        text = element.get_text()
        if re.search(r'(♂|♀|\(holotype\)|\(paratype\))', text, re.IGNORECASE):
            label_parts = []
            symbol_match = re.search(r'(♂|♀)', text)
            type_match = re.search(r'(\(holotype\)|\(paratype\))', text, re.IGNORECASE)
            if symbol_match: label_parts.append(symbol_match.group(0))
            if type_match: label_parts.append(type_match.group(0).lower())
            label_strings.append(' '.join(label_parts))

    label_map = {tag.get('src'): label_strings[i] for i, tag in enumerate(plate_tags) if i < len(label_strings)}
    
    for tag in plate_tags:
        src = tag.get('src')
        clean_src = src.replace('../images/', '').replace('../', '')
        cdn_url = f"{CDN_BASE_URL}/{book_number}/{clean_src}"
        plates.append({'url': cdn_url, 'label': label_map.get(src)})

    return plates, genitalia, misc_images


def scrape_and_create_file(missing_entry):
    """Scrapes a PHP file for frontmatter and body content, then creates a new markdown file."""
    url = missing_entry['url']; neighbor_data = missing_entry['neighbor_data']; context_type = missing_entry['context_type']
    relative_path = url.split('.com/', 1)[-1]; php_path = PHP_ROOT_DIR / relative_path
    if not php_path.exists(): print(f"  -> ❌ SKIPPING: Source PHP file not found for {url}"); return
    with open(php_path, 'r', encoding='utf-8', errors='ignore') as f: soup = BeautifulSoup(f.read(), 'html.parser')

    # Determine book from URL
    book = "Unknown"
    book_match = re.search(r'/part-([\d-]+)/', url)
    if book_match:
        part_str = book_match.group(1)
        book_num = '15-16' if part_str == '15-16' else part_str.split('-')[0]
        book = BOOK_WORD_MAP.get(book_num, "Unknown")

    # Scrape Name, Author, Status
    genus_name = neighbor_data.get('genus') if context_type == 'species' else neighbor_data.get('name')
    if not genus_name: print(f"  -> ❌ SKIPPING: Could not determine genus for {url}"); return
    scraped_name_data = scrape_name_author_status(soup, genus_name)
    name = scraped_name_data['name']
    author = scraped_name_data['author']
    taxonomic_status = scraped_name_data['taxonomic_status']

    # Scrape Images and Body Content
    plates, genitalia, misc_images = scrape_images_and_labels(soup, book)
    scraped_content = ""
    selector = BOOK_CONTENT_SELECTORS.get(book)
    if selector:
        content_paragraphs = soup.select(selector)
        if content_paragraphs:
            html_content = "".join(str(p) for p in content_paragraphs)
            scraped_content = format_headings_and_cleanup(md(html_content))
    if not plates: plates = DEFAULT_PLATE
    
    # Generate Filename and Assemble Frontmatter
    name_for_frontmatter = name if name != "Unknown" else f"sp. {url.split('_')[-1].split('.')[0]}"
    name_for_slug = name_for_frontmatter.lower().replace('sp. ', 'sp-').replace(' ', '-')
    slug = f"{genus_name.lower()}-{name_for_slug}"
    filepath = MARKDOWN_DIR / f"{slug}.md"
    if filepath.exists(): print(f"  -> ℹ️ SKIPPING: File already exists at {filepath.name}"); return

    new_metadata = {
        'name': name_for_frontmatter, 'author': author, 'legacy_url': url, 'book': book,
        'family': neighbor_data.get('family'), 'subfamily': neighbor_data.get('subfamily'),
        'tribe': neighbor_data.get('tribe'), 'genus': genus_name, 'taxonomic_status': taxonomic_status,
        'plates': plates, 'genitalia': genitalia, 'misc_images': misc_images, 'citations': []
    }
    
    new_post = frontmatter.Post(content=scraped_content)
    new_post.metadata = {k: v for k, v in new_metadata.items() if v} # Only add non-empty/non-None values
    with open(filepath, 'w', encoding='utf-8') as f: f.write(frontmatter.dumps(new_post))
    print(f"  -> ✅ CREATED: {filepath.name}")

def generate_html_report(creatable_entries, warnings):
    # This function remains the same
    pass

def main():
    parser = argparse.ArgumentParser(description="Audit content and optionally create missing entries.")
    parser.add_argument(
        '--generate-files', action='store_true',
        help="Scrape and create new files for missing entries. Default is a dry run report."
    )
    args = parser.parse_args()
    
    master_urls = get_master_php_urls()
    existing_species = get_existing_entries_by_url(MARKDOWN_DIR)
    existing_genera_by_url = get_existing_entries_by_url(GENERA_DIR)
    existing_genera_by_slug = get_existing_entries_by_slug(GENERA_DIR)
    
    missing_urls = sorted(list(master_urls - set(existing_species.keys())))
    
    if not missing_urls:
        print("🎉 No missing entries found. Everything seems to be in sync!")
        return

    entries_to_process, warnings_grouped = [], collections.defaultdict(lambda: {'urls': [], 'diagnostic': ''})
    for url in missing_urls:
        context_data, context_type = get_contextual_data(url, existing_species, existing_genera_by_url, existing_genera_by_slug)
        if context_data:
            entries_to_process.append({'url': url, 'neighbor_data': context_data, 'context_type': context_type})
        else:
            try:
                diagnostic_msg, expected_key = "", "unknown"
                if '/part-4/' in url:
                    genus_slug = url.split('/part-4/', 1)[1].split('/')[0]
                    expected_key = f"slug: {genus_slug}"
                    if genus_slug in existing_genera_by_slug: diagnostic_msg = f"<b>Debug Info (Book 4):</b> Expected parent (<code>{escape(genus_slug)}</code>) <b style='color:green;'>WAS FOUND</b> in the slug index."
                    else: diagnostic_msg = f"<b>Debug Info (Book 4):</b> Expected parent (<code>{escape(genus_slug)}</code>) <b style='color:red;'>WAS NOT FOUND</b> in the slug index."
                else:
                    genus_url_base = url.rsplit('_', 1)[0]
                    expected_key = f"{genus_url_base}.php"
                    if expected_key in existing_genera_by_url: diagnostic_msg = f"<b>Debug Info:</b> Expected parent URL <b style='color:green;'>WAS FOUND</b> in the index."
                    else: diagnostic_msg = f"<b>Debug Info:</b> Expected parent URL <b style='color:red;'>WAS NOT FOUND</b> in the index. Please check the `legacy_url`."
                warnings_grouped[expected_key]['urls'].append(url)
                warnings_grouped[expected_key]['diagnostic'] = diagnostic_msg
            except Exception:
                warnings_grouped['unknown_error']['urls'].append(url)
                warnings_grouped['unknown_error']['diagnostic'] = "Could not parse the URL to determine the expected parent genus."

    if args.generate_files:
        print(f"\n--- Starting Live Run: Attempting to create {len(entries_to_process)} files ---")
        for entry in entries_to_process:
            scrape_and_create_file(entry)
        print("\n✨ Live run complete.")
    else:
        formatted_warnings = []
        for expected_key, data in warnings_grouped.items():
            msg = f"<h4>Missing Parent Context: <code>{escape(expected_key)}</code></h4><p>{data['diagnostic']}</p>"
            msg += "<ul>" + "".join([f"<li>Failed to find neighbor for: <code>{escape(url)}</code></li>" for url in data['urls']]) + "</ul>"
            formatted_warnings.append(msg)
        # generate_html_report(entries_to_process, formatted_warnings)
        print("\n✅ Dry run complete. (HTML Report generation is disabled in this placeholder).")

if __name__ == "__main__":
    main()