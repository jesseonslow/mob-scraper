# mob-scraper/models/genus.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class Genus:
    """
    A data model representing a single genus, mirroring the AstroJS content schema.
    """
    name: str
    legacy_url: str
    book: str
    family: str
    author: Optional[str] = None
    subfamily: Optional[str] = None
    tribe: Optional[str] = None
    group: Optional[str] = None
    type_species: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    taxonomic_status: List[str] = field(default_factory=list)
    legacy: Optional[bool] = None
    body_content: str = ""

    @property
    def slug(self) -> str:
        """Generates the file slug from the genus name."""
        return self.name.lower().replace(' ', '-')

    @property
    def filepath(self) -> Path:
        """Constructs the full path to the markdown file."""
        from config import GENERA_DIR
        return GENERA_DIR / f"{self.slug}.md"