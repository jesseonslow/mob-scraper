from pathlib import Path

# --- File System Paths ---
MARKDOWN_DIR = Path("../moths-of-borneo/src/content/species/")
GENERA_DIR = Path("../moths-of-borneo/src/content/genera/")
PHP_ROOT_DIR = Path("../MoB-PHP/")

# --- Report Configuration ---
REPORT_FILENAME = "audit_report.html"

# --- URLs and Defaults ---
LEGACY_URL_BASE = "https://www.mothsofborneo.com/"
DEFAULT_PLATE = [{"url": "https://cdn.mothsofborneo.com/images/default.png", "label": ""}]

# --- Mappings and Selectors ---
BOOK_WORD_MAP = {
    '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
    '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten',
    '11': 'eleven', '12': 'twelve', '13': 'thirteen', '14': 'fourteen',
    '15-16': 'fifteen', '16': 'sixteen', '17': 'seventeen', '18': 'eighteen'
}

BOOK_CONTENT_SELECTORS = {
    'three': 'p[align="justify"]',
    'four': 'p[align="justify"]',
    'five': 'p[align="justify"], p[class="MsoNormal"][style*="text-align:justify"], p[class="MsoNormal"][align="justify"]',
    'eight': 'p[align="justify"], p[style*="text-align:justify"]',
    'nine': 'p[style*="text-align:justify"]',
}