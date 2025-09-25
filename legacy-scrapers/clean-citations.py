import os
from pathlib import Path
import frontmatter
import yaml # We need to catch specific yaml errors
import re

# --- Script Logic ---

def repair_and_reload(file_path: Path):
    """
    Performs a surgical repair on the raw frontmatter text using re.sub().
    """
    print(f"  - Parsing failed. Attempting surgical repair...")

    content = file_path.read_text(encoding='utf-8-sig')
    
    match = re.search(r'^---\s*\n(.*?)\n---\s*(.*)', content, re.DOTALL)
    if not match:
        print("  - [ERROR] Could not split frontmatter from content.")
        return None
    fm_string, body_string = match.groups()

    # This function will be called by re.sub for the matched block
    def replacer(match):
        raw_citation_block = match.group(1)
        
        if "*" in raw_citation_block:
            lines = raw_citation_block.split('\n')
            clean_lines = [re.sub(r'^\s*-\s*', '', line).strip() for line in lines if not line.startswith('citations:')]
            full_citation_text = " ".join(filter(None, clean_lines))
            full_citation_text = " ".join(full_citation_text.split())
            full_citation_text = full_citation_text.replace("'", "''") # Escape single quotes
            replacement_text = f"citations:\n- '{full_citation_text}'"
            print(f"  - Repaired block containing '*'.")
        else:
            replacement_text = "citations: []"
            print(f"  - Replaced block with empty array.")
            
        return replacement_text

    # --- THIS REGEX IS THE DEFINITIVE FIX ---
    # It captures from the start of the 'citations:' line until it sees the start of a new key or the end of the string.
    # [\s\S] matches ANY character, including newlines.
    regex_pattern = r'(^citations:[\s\S]*?)(?=\n^\w+:|\Z)'
    new_fm_string, num_replacements = re.subn(
        regex_pattern, 
        replacer, 
        fm_string, 
        count=1, 
        flags=re.MULTILINE
    )

    if num_replacements == 0:
        print("  - [ERROR] Could not find the citations block to repair.")
        return None

    # Rebuild the post object from the new parts
    try:
        new_post = frontmatter.Post(content=body_string)
        new_post.metadata = yaml.safe_load(new_fm_string)
        return new_post
    except yaml.YAMLError as e:
        print(f"  - [FATAL] Repair failed. The new frontmatter is still invalid: {e}")
        return None


def process_markdown_file(file_path: Path):
    """
    Reads a markdown file, trying to load it. If it fails, it calls the repair function.
    """
    print(f"Processing: {file_path.name}...")
    post = None
    modified = False

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            post = frontmatter.load(f)
        print("  -> Parsed successfully. No changes needed.")

    except yaml.YAMLError as e:
        repaired_post = repair_and_reload(file_path)
        if repaired_post:
            post = repaired_post
            modified = True
    
    except Exception as e:
        print(f"  [ERROR] An unexpected error occurred: {e}")

    if modified and post:
        new_file_content = frontmatter.dumps(post)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_file_content)
        print(f"  -> Saved changes to {file_path.name}")


def main():
    TARGET_DIRECTORY = Path("./src/content/species/")
    if not TARGET_DIRECTORY.is_dir():
        print(f"Error: Directory not found at '{TARGET_DIRECTORY}'")
        return

    print(f"Scanning for markdown files in '{TARGET_DIRECTORY}'...\n")
    for file in TARGET_DIRECTORY.glob('**/*.md*'):
        if file.is_file():
            process_markdown_file(file)

    print("\n✅ Script finished.")

if __name__ == "__main__":
    main()