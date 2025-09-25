from pathlib import Path
import frontmatter

# --- Configuration ---
MARKDOWN_DIR = Path("./src/content/species/")
DEFAULT_PLATE = [{
    "url": "https://cdn.mothsofborneo.com/images/default.png",
    "label": ""
}]

def main():
    """
    Finds markdown files with an empty `image_urls` array and adds a default plate.
    """
    if not MARKDOWN_DIR.is_dir():
        print(f"Error: Directory not found at '{MARKDOWN_DIR}'")
        return

    print(f"🚀 Scanning for files with empty 'image_urls' field in '{MARKDOWN_DIR}'...")
    
    updated_files_count = 0
    
    for markdown_path in MARKDOWN_DIR.glob('**/*.md*'):
        if not markdown_path.is_file():
            continue
        
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)

            # --- THIS IS THE CORRECTED, PRECISE CONDITION ---
            # Process only if 'image_urls' exists AND is an empty list/array.
            if 'image_urls' in post.metadata and not post.metadata['image_urls']:
                
                print(f"-> Found target file. Updating {markdown_path.name}...")

                # Remove the old, empty key
                del post.metadata['image_urls']

                # Add the new plates field with the default image
                post.metadata['plates'] = DEFAULT_PLATE
                
                # Save the modified file
                new_file_content = frontmatter.dumps(post)
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(new_file_content)
                
                updated_files_count += 1

        except Exception as e:
            print(f"  [ERROR] Could not process {markdown_path.name}: {e}")
            
    print(f"\n✨ Script finished. Updated {updated_files_count} file(s).")

if __name__ == "__main__":
    main()