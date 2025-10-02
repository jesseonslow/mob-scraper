# core/config_manager.py

import yaml
from pathlib import Path

# Define paths relative to this file's location
CONFIG_DIR = Path(__file__).parent.parent / "config"
SCRAPING_RULES_PATH = CONFIG_DIR / 'scraping_rules.yaml'
MAPPINGS_PATH = CONFIG_DIR / 'mappings.yaml'

class ConfigManager:
    """
    A singleton class to manage loading and saving of YAML configuration files.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # The __init__ is called every time ConfigManager() is invoked,
        # but we only want to load the files once.
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._scraping_rules = self._load_yaml(SCRAPING_RULES_PATH)
        self._mappings = self._load_yaml(MAPPINGS_PATH)
        self._initialized = True
        print("ConfigManager initialized.")

    def _load_yaml(self, filepath):
        """Loads a single YAML file."""
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def get_rules_for_book(self, book_name: str) -> dict:
        """Gets the specific rules for a book, falling back to default."""
        return self._scraping_rules.get(book_name, self._scraping_rules.get('default', {}))

    def get_mappings(self) -> dict:
        """Gets all data from mappings.yaml."""
        return self._mappings

    def update_rules_for_book(self, book_name: str, new_rules: dict):
        """Updates the scraping rules for a book in memory and saves to file."""
        self._scraping_rules[book_name] = new_rules
        print(f"\nUpdated rules for book '{book_name}' in memory.")
        self._save_scraping_rules()

    def _save_scraping_rules(self):
        """Saves the current state of scraping rules back to the YAML file."""
        print(f"Saving updated rules to '{SCRAPING_RULES_PATH}'...")
        try:
            # Sort by book name for consistent file output
            sorted_rules = dict(sorted(self._scraping_rules.items()))
            with open(SCRAPING_RULES_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(sorted_rules, f, default_flow_style=False, sort_keys=False, indent=2)
            print("✅ Config file saved successfully!")
        except Exception as e:
            print(f"❌ Failed to save config file: {e}")

# Create a single, shared instance that the whole application can import and use
config_manager = ConfigManager()