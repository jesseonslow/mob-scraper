#mob-scraper/config.py

from pathlib import Path

# --- CORE FILE SYSTEM PATHS ---
# These paths define the root directories for your content, the PHP source files,
# and where to save generated reports. They are fundamental to all operations.
MARKDOWN_DIR = Path("../moths-of-borneo/src/content/species/")
GENERA_DIR = Path("../moths-of-borneo/src/content/genera/")
PHP_ROOT_DIR = Path("../MoB-PHP/")
REPORT_DIR = Path("./html/")
CONFIG_PATH = Path(__file__)

# --- REPORTING ---
# Centralized filenames for any generated reports.
AUDIT_REPORT_FILENAME = "audit_report.html"
CONTENT_QUALITY_REPORT_FILENAME = "content_quality_report.html"
IMAGE_UPDATE_REPORT_FILENAME = "image_update_report.html"
REDIRECT_REPORT_FILENAME = "redirects.csv"

# --- URLS & DEFAULTS ---
# Base URLs for constructing links and a default image for species without one.
LEGACY_URL_BASE = "https://www.mothsofborneo.com/"
CDN_BASE_URL = "https://cdn.mothsofborneo.com"
DEFAULT_PLATE = [{
    "url": "https://cdn.mothsofborneo.com/images/default.png",
    "label": ""
}]

# --- DATA MAPPINGS ---
# These dictionaries are used to translate data from the old site to the new format.
# This includes book names, group mappings for species, etc.

# Maps book numbers to their string representation.
BOOK_WORD_MAP = {
    '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
    '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten',
    '11': 'eleven', '12': 'twelve', '13': 'thirteen', '14': 'fourteen',
    '15-16': 'fifteen', '16': 'sixteen', '17': 'seventeen', '18': 'eighteen'
}

# The reverse of BOOK_WORD_MAP, for looking up book numbers from names.
BOOK_NUMBER_MAP = {v: k.split('-')[0] for k, v in BOOK_WORD_MAP.items()}

# Rules for assigning a 'group' based on a substring in the legacy_url.
GROUP_MAPPING = {
    "eugoawalker/": "eugoa",
    "episparis/": "episparis",
    "saroba/": "saroba",
    "throana/": "throana",
}

# --- BOOK-SPECIFIC SCRAPING RULES ---
# This is the new, flexible rule-based system for the scraper.
# Each book can have its own set of CSS selectors and extraction methods.
RULES_VAR_NAME = "BOOK_SCRAPING_RULES"
BOOK_SCRAPING_RULES = {   'default': {   'content_container_selector': 'p[align="justify"]',
                   'name_selector': {'index': 2, 'method': 'first_lowercase', 'selector': 'b'}},
    'eight': {   'content_selector': {'index': -1, 'method': 'full_text', 'selector': 'p[style*="text-align:justify"]'},
                 'genus_selector': {'method': 'first_word', 'selector': 'b i'},
                 'name_selector': {'method': 'last_word', 'selector': 'b'}},
    'eighteen': {   'citation_selector': {'index': 3, 'method': 'full_text', 'selector': 'p'},
                    'content_selector': {'index': 5, 'method': 'full_text', 'selector': 'p'},
                    'genus_selector': {'index': 2, 'method': 'position_1', 'selector': 'b'},
                    'name_selector': {'index': 3, 'method': 'position_1', 'selector': 'b'}},
    'eleven': {   'content_selector': {'index': 4, 'method': 'full_text', 'selector': 'p'},
                  'genus_selector': {'index': 2, 'method': 'position_1', 'selector': 'b'},
                  'name_selector': {'index': 2, 'method': 'position_2', 'selector': 'b'}},
    'fifteen': {   'citation_selector': {'index': 3, 'method': 'full_text', 'selector': 'p'},
                   'content_selector': {'index': 6, 'method': 'full_text', 'selector': 'p'},
                   'genus_selector': {'index': 2, 'method': 'position_1', 'selector': 'b'},
                   'name_selector': {'index': 2, 'method': 'position_2', 'selector': 'b'}},
    'five': {   'citation_selector': {'index': 3, 'method': 'full_text', 'selector': 'p'},
                'content_selector': {'index': 4, 'method': 'full_text', 'selector': 'p'},
                'genus_selector': {'index': 2, 'method': 'position_1', 'selector': 'b'},
                'name_selector': {'index': 2, 'method': 'position_2', 'selector': 'b'}},
    'four': {   'content_selector': {'index': 6, 'method': 'full_text', 'selector': 'p'},
                'name_selector': {'index': 2, 'method': 'position_2', 'selector': 'b'}},
    'fourteen': {   'citation_selector': {'index': 3, 'method': 'full_text', 'selector': 'p'},
                    'content_selector': {'index': 4, 'method': 'full_text', 'selector': 'p'},
                    'genus_selector': {'index': 3, 'method': 'position_1', 'selector': 'b'},
                    'name_selector': {'index': 3, 'method': 'position_2', 'selector': 'b'}},
    'nine': {   'content_selector': {'index': 4, 'method': 'full_text', 'selector': 'p'},
                'genus_selector': {'index': 2, 'method': 'position_1', 'selector': 'b'},
                'name_selector': {'index': 2, 'method': 'position_2', 'selector': 'b'}},
    'seven': {   'content_selector': {'index': 5, 'method': 'full_text', 'selector': 'p'},
                 'genus_selector': {'index': 1, 'method': 'position_1', 'selector': 'b'},
                 'name_selector': {'index': 1, 'method': 'position_2', 'selector': 'b'}},
    'seventeen': {   'content_selector': {'index': 3, 'method': 'full_text', 'selector': 'p'},
                     'name_selector': {'index': 2, 'method': 'first_lowercase', 'selector': 'b'}},
    'ten': {   'content_selector': {'index': 4, 'method': 'full_text', 'selector': 'p'},
               'genus_selector': {'index': 2, 'method': 'position_1', 'selector': 'b'},
               'name_selector': {'index': 2, 'method': 'position_2', 'selector': 'b'}},
    'thirteen': {   'content_selector': {'index': 4, 'method': 'full_text', 'selector': 'p'},
                    'genus_selector': {'index': 2, 'method': 'position_1', 'selector': 'b'},
                    'name_selector': {'index': 2, 'method': 'first_lowercase', 'selector': 'b'}},
    'three': {   'content_selector': {'index': 5, 'method': 'full_text', 'selector': 'p'},
                 'genus_selector': {'index': 2, 'method': 'position_1', 'selector': 'b'},
                 'name_selector': {'index': 2, 'method': 'position_2', 'selector': 'b'}}}

KNOWN_TAXONOMIC_STATUSES = [
    'stat. rev.',
    'stat. n.',
    'comb. rev.',
    'comb. n.',
    'syns. n.',
    'syn. n.',
    'sp. rev.',
    'sp. n.',
    'ssp.',
    'sp.'
]

# --- DATA CLEANUP RULES ---
# A list of frontmatter fields to be unconditionally removed during cleanup tasks.
FIELDS_TO_DELETE = {}