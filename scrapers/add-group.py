import os
from pathlib import Path
import frontmatter

# --- Configuration ---

# 1. Set the path to your content folder.
TARGET_DIRECTORY = Path("./src/content/species/")

# 2. Define the rules for assigning a group based on a substring in the legacy_url.
#    The script will stop checking as soon as it finds the first match.
GROUP_MAPPING = {
    "eugoawalker/": "eugoa",
    "episparis/": "episparis",
    "saroba/": "saroba",
    "throana/": "throana",
}

# --- Script Logic ---

def process_markdown_file(file_path: Path):
    """
    Reads a markdown file and adds a 'group' field if it matches a rule
    and doesn't already have one.
    """
    print(f"Processing: {file_path.name}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        metadata = post.metadata

        # Condition 1: Skip if a 'group' field already exists.
        if 'group' in metadata:
            print(f"  - Skipping, 'group' field already exists.")
            return

        # Condition 2: Check for a legacy_url to process.
        legacy_url = metadata.get('legacy_url')
        if not legacy_url:
            print(f"  - Skipping, no 'legacy_url' found.")
            return
            
        # Find the first matching rule and assign the group
        group_to_add = None
        for url_part, group_name in GROUP_MAPPING.items():
            if url_part in legacy_url:
                group_to_add = group_name
                break # Stop after the first match

        # If a rule matched, update the frontmatter and save the file
        if group_to_add:
            print(f"  -> Match found! Assigning group: '{group_to_add}'")
            post.metadata['group'] = group_to_add
            
            # Use the safe dumps/write method
            new_file_content = frontmatter.dumps(post)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_file_content)
            print(f"  -> Saved changes to {file_path.name}")
        else:
            print("  - No matching group rule found.")

    except Exception as e:
        print(f"  [ERROR] Could not process {file_path.name}: {e}")

def main():
    """
    Main function to find and process all markdown files in the target directory.
    """
    if not TARGET_DIRECTORY.is_dir():
        print(f"Error: Directory not found at '{TARGET_DIRECTORY}'")
        return

    print(f"Scanning for markdown files in '{TARGET_DIRECTORY}'...\n")
    # Recursively find all files ending with .md or .mdx
    for file in TARGET_DIRECTORY.glob('**/*.md*'):
        if file.is_file():
            process_markdown_file(file)

    print("\n✅ Script finished.")


if __name__ == "__main__":
    main()