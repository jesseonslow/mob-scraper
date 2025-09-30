# mob-scraper/models/species.py

import re
import frontmatter
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from core.file_system import save_markdown_file
from config import SPECIES_DIR, KNOWN_TAXONOMIC_STATUSES

@dataclass
class Plate:
    """Represents a single plate image with its URL and label."""
    url: str
    label: Optional[str] = ""

@dataclass
class Species:
    """
    A data model representing a single species, mirroring the AstroJS content schema.
    This class centralizes data handling, validation, and file operations.
    """
    # Core Identity
    name: str
    genus: str
    legacy_url: str
    book: str

    # Taxonomy
    family: Optional[str] = None
    subfamily: Optional[str] = None
    tribe: Optional[str] = None
    author: Optional[str] = None
    taxonomic_status: List[str] = field(default_factory=list)
    group: Optional[str] = None

    # Image Fields
    plates: List[Plate] = field(default_factory=list)
    genitalia: List[str] = field(default_factory=list)
    misc_images: List[str] = field(default_factory=list)

    # Citations and Content
    citations: List[str] = field(default_factory=list)
    body_content: str = ""

    # --- Instance Methods ---

    @property
    def slug(self) -> str:
        """Generates the file slug from the genus and species name."""
        name_for_slug = self.name.lower().replace('sp. ', 'sp-').replace(' ', '-').replace('?', '').replace('.', '')
        clean_genus = re.sub(r'[^a-z]', '', self.genus.strip().lower())
        return f"{clean_genus}-{name_for_slug}"

    @property
    def filepath(self) -> Path:
        """Constructs the full path to the markdown file."""
        return SPECIES_DIR / f"{self.slug}.md"

    def to_frontmatter(self) -> dict:
        """Converts the dataclass instance to a dictionary for frontmatter serialization."""
        output = {
            'name': self.name,
            'author': self.author,
            'legacy_url': self.legacy_url,
            'book': self.book,
            'family': self.family,
            'subfamily': self.subfamily,
            'tribe': self.tribe,
            'genus': self.genus,
            'group': self.group,
            'taxonomic_status': self.taxonomic_status,
            'plates': [{'url': p.url, 'label': p.label} for p in self.plates],
            'genitalia': self.genitalia,
            'misc_images': self.misc_images,
            'citations': self.citations
        }
        return {k: v for k, v in output.items() if v is not None and v != []}

    def save(self) -> bool:
        """Saves the species data as a markdown file with YAML frontmatter."""
        if self.filepath.exists():
            print(f"  -> ℹ️ SKIPPING: File already exists at {self.filepath.name}")
            return False
        post = frontmatter.Post(content=self.body_content)
        post.metadata = self.to_frontmatter()
        return save_markdown_file(post, self.filepath)

    def validate(self) -> List[str]:
        """Performs a quality check and returns a list of failing fields."""
        failures = []
        if not self.name or self.name == "Unknown" or self.name in KNOWN_TAXONOMIC_STATUSES:
            failures.append('name')
        if not self.genus or self.genus == "Unknown" or self.genus in KNOWN_TAXONOMIC_STATUSES:
            failures.append('genus')
        if self.author is not None and self.author.strip('., ').lower() == 'spp':
            failures.append('author')
        if '<' in self.body_content or '>' in self.body_content or len(self.body_content.strip()) < 50:
            failures.append('content')
        return failures

    @classmethod
    def from_scraped_data(cls, entry_data: dict, scraped_data: dict, book_name: str) -> "Species":
        """Factory method to create a Species instance from scraper output."""
        neighbor_data = entry_data.get('neighbor_data', {})
        plate_objects = [Plate(**p) for p in scraped_data.get('plates', [])]
        return cls(
            name=scraped_data.get('name', 'Unknown'),
            author=scraped_data.get('author'),
            legacy_url=entry_data['url'],
            book=book_name,
            family=neighbor_data.get('family'),
            subfamily=neighbor_data.get('subfamily'),
            tribe=neighbor_data.get('tribe'),
            genus=scraped_data.get('genus', 'Unknown'),
            group=neighbor_data.get('group'),
            taxonomic_status=scraped_data.get('taxonomic_status', []),
            plates=plate_objects,
            genitalia=scraped_data.get('genitalia', []),
            misc_images=scraped_data.get('misc_images', []),
            citations=scraped_data.get('citations', []),
            body_content=scraped_data.get('body_content', '')
        )