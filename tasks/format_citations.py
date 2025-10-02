# tasks/format_citations.py

import frontmatter
from config import SPECIES_DIR
from core.file_system import save_markdown_file
# Import the logic from its new, centralized location
from core.citation_parser import parse_citation, format_citation, _normalize_publication_for_matching

def run_format_citations(publication_title, canonical_name=None):
    """
    Finds and formats all citations for a given publication.
    """
    target_pub = publication_title
    new_pub_name = canonical_name if canonical_name else target_pub
    
    print(f"🚀 Starting citation formatting for publication: '{target_pub}'")
    if canonical_name:
        print(f"   -> Normalizing to: '{new_pub_name}'")
    
    updated_files_count = 0
    
    all_files = list(SPECIES_DIR.glob('**/*.md*'))
    total_files = len(all_files)

    for i, file_path in enumerate(all_files):
        if not file_path.is_file():
            continue
            
        print(f"[{i+1}/{total_files}] Scanning: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)

            book_name = post.metadata.get('book', 'Unknown')
            legacy_url = post.metadata.get('legacy_url', '')
            original_citations = post.metadata.get('citations', [])
            
            if not original_citations:
                continue

            new_citations_list = []
            file_was_modified = False
            for citation in original_citations:
                if '*' in citation:
                    new_citations_list.append(citation)
                    continue

                parsed_list = parse_citation(citation, book_name, legacy_url)
                if parsed_list:
                    temp_formatted_parts = []
                    for parsed in parsed_list:
                        if _normalize_publication_for_matching(parsed["publication"]) == _normalize_publication_for_matching(target_pub):
                            if canonical_name:
                                parsed["publication"] = new_pub_name
                                
                            formatted = format_citation(parsed)
                            temp_formatted_parts.append(formatted)
                            if formatted != citation:
                                file_was_modified = True
                        else:
                            temp_formatted_parts = [citation]
                            file_was_modified = False
                            break
                    new_citations_list.extend(temp_formatted_parts)
                else:
                    new_citations_list.append(citation)
            
            if file_was_modified:
                print(f"  -> Found match. Updating file.")
                post.metadata['citations'] = new_citations
                if save_markdown_file(post, file_path):
                    updated_files_count += 1
                    
        except Exception as e:
            print(f"  [ERROR] Could not process {file_path.name}: {e}")
            
    print(f"\n✨ Citation formatting finished. Updated {updated_files_count} file(s).")