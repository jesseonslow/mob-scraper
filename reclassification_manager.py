import json
from pathlib import Path

RECLASSIFICATION_FILE = Path("./reclassified_urls.json")

def load_reclassified_urls() -> set:
    """Loads the set of URLs that have been reclassified as genus pages."""
    if not RECLASSIFICATION_FILE.exists():
        return set()
    with open(RECLASSIFICATION_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return set(data.get("genus_urls", []))

def add_reclassified_url(url: str):
    """Adds a new URL to the reclassification list."""
    urls = load_reclassified_urls()
    urls.add(url)
    with open(RECLASSIFICATION_FILE, 'w', encoding='utf-8') as f:
        json.dump({"genus_urls": sorted(list(urls))}, f, indent=2)
    print(f"  -> Reclassified '{url}' as a genus page. It will be skipped in future runs.")
