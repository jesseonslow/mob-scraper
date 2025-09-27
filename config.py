#mob-scraper/config.py

from pathlib import Path

# --- CORE FILE SYSTEM PATHS ---
# These paths define the root directories for your content, the PHP source files,
# and where to save generated reports. They are fundamental to all operations.
MARKDOWN_DIR = Path("../moths-of-borneo/src/content/species/")
GENERA_DIR = Path("../moths-of-borneo/src/content/genera/")
PHP_ROOT_DIR = Path("../MoB-PHP/")
REPORT_DIR = Path("./html/")

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
BOOK_SCRAPING_RULES = {
    'nine': {
        'name_selector': {'selector': 'b', 'index': 2, 'method': 'position_2'},
        'content_selector': {'selector': 'p', 'index': 4, 'method': 'full_text'},
    },
    'seven': {
        'name_selector': {'selector': 'b', 'index': 1, 'method': 'position_2'},
        'content_selector': {'selector': 'p', 'index': 5, 'method': 'full_text'},
    },
    'five': {
        'name_selector': {'selector': 'b', 'index': 3, 'method': 'full_text'},
        'citation_selector': {'selector': 'p', 'index': 3, 'method': 'full_text'},
        'content_selector': {'selector': 'p', 'index': 4, 'method': 'full_text'},
    },
    'four': {
        'name_selector': {'selector': 'b', 'index': 2, 'method': 'position_2'},
        'content_selector': {'selector': 'p', 'index': 6, 'method': 'full_text'},
    },
    'three': {
        'name_selector': {'selector': 'b', 'index': 2, 'method': 'position_2'},
        'content_selector': {'selector': 'p', 'index': 5, 'method': 'full_text'},
    },
    'eighteen': {
        'name_selector': {'selector': 'b', 'index': 3, 'method': 'position_1'},
        'citation_selector': {'selector': 'p', 'index': 3, 'method': 'full_text'},
        'content_selector': {'selector': 'p', 'index': 5, 'method': 'full_text'},
    },
    'seventeen': {
        'name_selector': {'selector': 'b', 'index': 2, 'method': 'first_lowercase'},
        'content_selector': {'selector': 'p', 'index': 3, 'method': 'full_text'},
    },
    'fifteen': {
        'name_selector': {'selector': 'b', 'index': 2, 'method': 'first_lowercase'},
        'citation_selector': {'selector': 'p', 'index': 3, 'method': 'full_text'},
        'content_selector': {'selector': 'p', 'index': 6, 'method': 'full_text'},
    },
    'fourteen': {
        'name_selector': {'selector': 'b', 'index': 3, 'method': 'first_lowercase'},
        'citation_selector': {'selector': 'p', 'index': 3, 'method': 'full_text'},
        'content_selector': {'selector': 'p', 'index': 4, 'method': 'full_text'},
    },
    'thirteen': {
        'name_selector': {'selector': 'b', 'index': 2, 'method': 'first_lowercase'},
    },
    'ten': {
        'name_selector': {'selector': 'b', 'index': 2, 'method': 'first_lowercase'},
        'content_selector': {'selector': 'p', 'index': 4, 'method': 'full_text'},
    },
    'eight': {
        'name_selector': {'selector': 'b', 'method': 'last_word'},
        'genus_selector': {'selector': 'b i', 'method': 'first_word'},
        'content_selector': {'selector': 'p[align="justify"]', 'method': 'full_text'},
    },
    'default': {
        'content_container_selector': 'p[align="justify"]',
        'name_selector': 'b',
    },
    'eleven': {
        'content_container_selector': 'p[align="justify"]',
        'content_extraction_method': 'last_span_text', # Custom method flag
        'name_selector': 'b',
        'genus_selector': 'b i', # Genus is in an <i> tag inside the <b> tag
        'citation_selector': 'p[align="justify"] > span',
        'citation_extraction_method': 'first_span_text' # Custom method flag
    }
    # You can add rules for 'three', 'four', etc. here as needed.
}

KNOWN_TAXONOMIC_STATUSES = [
    'stat. rev.',
    'stat. n.',
    'comb. rev.',
    'comb. n.',
    'sp. rev.',
    'sp. n.',
    'ssp.'
]

# --- DATA CLEANUP RULES ---
# A list of frontmatter fields to be unconditionally removed during cleanup tasks.
FIELDS_TO_DELETE = {}