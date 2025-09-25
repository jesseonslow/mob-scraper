import os
import re
from pathlib import Path
import frontmatter

# --- Configuration ---

# 1. Set the path to your content folder.
#    The script assumes it's run from the project root.
TARGET_DIRECTORY = Path("./src/content/species/")

# 2. List of fields to unconditionally delete, regardless of their value.
FIELDS_TO_DELETE = {
    "holotype",
    "paratype",
    "paratypes"
}

# --- Script Logic ---

def process_markdown_file(file_path: Path):
    """
    Reads a markdown file, cleans its frontmatter, and saves it back.
    Uses a line-by-line method to handle malformed multi-line strings.
    """
    print(f"Processing: {file_path.name}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # --- Part 1: Pre-process with line-by-line filtering ---
        
        parts = original_content.split('---', 2)
        if len(parts) < 3:
            if original_content.startswith('---'):
                print("  -> Malformed frontmatter (missing closing '---'). Skipping.")
            else:
                print("  -> No frontmatter found. Skipping.")
            return

        frontmatter_text = parts[1]
        body_text = parts[2]
        
        lines = frontmatter_text.split('\n')
        kept_lines = []
        is_deleting = False
        deleted_fields = []

        # This simple regex just identifies if a line looks like a key.
        key_pattern = re.compile(r"^\s*[^:\s]+:")

        for line in lines:
            # Check if the line is the start of a new key-value pair.
            is_a_key_line = bool(key_pattern.match(line))
            
            if is_a_key_line:
                # It's a key. Find out which one it is.
                key_name = line.split(':', 1)[0].strip()
                if key_name in FIELDS_TO_DELETE:
                    # It's a key we want to delete. Start deleting.
                    is_deleting = True
                    if key_name not in deleted_fields:
                        deleted_fields.append(key_name)
                else:
                    # It's a different key. Stop deleting.
                    is_deleting = False
            
            # Only keep the line if we are NOT in the middle of deleting a field.
            if not is_deleting:
                kept_lines.append(line)
        
        pre_processed_frontmatter = "\n".join(kept_lines)
        content_for_parsing = f"---\n{pre_processed_frontmatter}\n---{body_text}"

        # --- Part 2: Parse the cleaned content with the frontmatter library ---
        
        post = frontmatter.loads(content_for_parsing)
        
        # --- Part 3: Remove any null-valued fields ---
        
        keys_to_check = list(post.metadata.keys())
        null_deleted_fields = []
        
        for key in keys_to_check:
            if post.metadata.get(key) is None:
                del post.metadata[key]
                null_deleted_fields.append(key)

        # --- Part 4: Save if any modifications were made ---
        
        modified = bool(deleted_fields or null_deleted_fields)

        if modified:
            for key in sorted(deleted_fields):
                 print(f"  - Deleted field: '{key}'")
            for key in sorted(null_deleted_fields):
                 print(f"  - Deleted null field: '{key}'")

            new_file_content = frontmatter.dumps(post)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_file_content)
            
            print(f"  -> Saved changes to {file_path.name}")
        else:
            print("  -> No changes needed.")

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
    for file in TARGET_DIRECTORY.glob('**/*.md*'):
        if file.is_file():
            process_markdown_file(file)

    print("\n✅ Script finished.")


if __name__ == "__main__":
    main()