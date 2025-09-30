import yaml
from pathlib import Path

# --- Core Configuration Loading ---

CONFIG_DIR = Path(__file__).parent

def load_yaml_config(filename):
    """Loads a YAML file from the config directory."""
    with open(CONFIG_DIR / filename, 'r') as f:
        return yaml.safe_load(f)

# Load all configurations into constants
SCRAPING_RULES = load_yaml_config('scraping_rules.yaml')
MAPPINGS = load_yaml_config('mappings.yaml')

# --- Expose mapping constants for easy access ---
GROUP_MAPPING = MAPPINGS.get('GROUP_MAPPING', {})
KNOWN_TAXONOMIC_STATUSES = MAPPINGS.get('KNOWN_TAXONOMIC_STATUSES', [])
FIELDS_TO_DELETE = MAPPINGS.get('FIELDS_TO_DELETE', {})

# --- CORE FILE SYSTEM PATHS ---
# These paths are still best defined in Python as they relate to the code's location.
SPECIES_DIR = Path("../moths-of-borneo/src/content/species/")
GENERA_DIR = Path("../moths-of-borneo/src/content/genera/")
CONTENT_DIR = Path("../moths-of-borneo/src/content/")
PHP_ROOT_DIR = Path("../MoB-PHP/")
REPORT_DIR = Path("./html/")

# --- REPORTING ---
AUDIT_REPORT_FILENAME = "audit_report.html"
CONTENT_QUALITY_REPORT_FILENAME = "content_quality_report.html"
IMAGE_UPDATE_REPORT_FILENAME = "image_update_report.html"
REDIRECT_REPORT_FILENAME = "redirects.csv"
CITATION_HEALTH_REPORT_FILENAME = "citation_health_report.html"

# --- URLS & DEFAULTS ---
LEGACY_URL_BASE = "https://www.mothsofborneo.com/"
CDN_BASE_URL = "https://cdn.mothsofborneo.com"
DEFAULT_PLATE = [{
    "url": "https://cdn.mothsofborneo.com/images/default.png",
    "label": ""
}]

# --- DATA MAPPINGS ---
BOOK_WORD_MAP = {
    '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
    '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten',
    '11': 'eleven', '12': 'twelve', '13': 'thirteen', '14': 'fourteen',
    '15-16': 'fifteen', '16': 'sixteen', '17': 'seventeen', '18': 'eighteen'
}
BOOK_NUMBER_MAP = {v: k.split('-')[0] for k, v in BOOK_WORD_MAP.items()}