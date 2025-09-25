import re
import json

def parse_references(file_path):
    """
    Parses a text file of references into a structured JSON format.
    Handles multiple authors, publication types, and "Ibid." entries.
    """
    references = []
    last_record = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Normalize line endings and multiple spaces for easier parsing
    content = content.replace('\n', ' ').replace('  ', ' ')
    
    # Split the content into individual references using a pattern that matches "Author, " or "Author & " followed by a year or "in press"
    entries = re.split(r'(?=\b[A-Z][a-z]+, [A-Z].*?\([0-9]{4}\)|(?=\b[A-Z][a-z]+, [A-Z].*?in press))', content)
    
    # The first element will be an empty string or header text, so we discard it
    if entries and not entries[0].strip():
        entries = entries[1:]
    
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        record = {}
        
        # Handle Ibid. entries
        if entry.startswith('Ibid.'):
            if last_record:
                record['author'] = last_record['author']
                record['title'] = last_record['title']
                record['publication'] = last_record['publication']
                record['publisher'] = last_record['publisher']
                
                # Extract year from Ibid. entry
                year_match = re.search(r'\(([0-9]{4})\)', entry)
                if year_match:
                    record['year'] = int(year_match.group(1))
            else:
                print(f"Warning: 'Ibid.' found without a preceding record. Skipping: {entry}")
                continue
        else:
            # Regular expression to extract components
            match = re.search(r'^(.*?)\s+\(([0-9]{4}|in press)\)\.?\s+(.*?)(?:\.(?:\s+In:\s+.*?\))?)?$', entry, re.I | re.DOTALL)
            if not match:
                # Handle cases with no year or publication
                match = re.search(r'^(.*?)\s+\((.*?)\)\.?\s+(.*?)(?:\.(?:\s+In:\s+.*?\))?)?$', entry, re.I | re.DOTALL)
                if not match:
                    print(f"Could not parse entry: {entry}")
                    continue
            
            author_str, year_str, rest = match.groups()
            
            # Authors as an array
            author_list = [a.strip() for a in re.split(r'&| and |, and |,|;|,', author_str) if a.strip()]
            record['author'] = author_list

            # Year as number or string
            record['year'] = int(year_str) if year_str.isdigit() else year_str

            # Extract publication and publisher
            # A lot of this requires custom logic due to the varied formatting
            # Check for common phrases like "In: ...", "Vol. ...", etc.
            
            # Use regex to find the title, assuming it's the first quoted/italicized
            # or first complete sentence-like phrase
            title_match = re.search(r'\"(.*?)\"|’‘(.*?)\’‘|‘(.*?)’', rest)
            
            if title_match:
                record['title'] = title_match.group(1) or title_match.group(2) or title_match.group(3)
                rest = re.sub(r'\"(.*?)\"|’‘(.*?)\’‘|‘(.*?)’', '', rest)
            else:
                record['title'] = rest.split('.')[0].strip()
                rest = '.'.join(rest.split('.')[1:])

            # Find the publisher. This part is tricky and often requires manual tuning.
            # Look for common patterns like "City: Publisher", "Journal", etc.
            publication_match = re.search(r'(\w+\s+[A-Z].*?)\b(?!\.)', rest)
            if publication_match:
                record['publication'] = publication_match.group(1).strip()
                rest = rest.replace(publication_match.group(1), '')
            else:
                record['publication'] = rest.split('.')[0].strip()
                
            record['publisher'] = rest.strip()
            
        # Add the parsed record to our list
        references.append(record)
        
        # Update the last record for Ibid. functionality
        if 'title' in record and 'publication' in record and 'publisher' in record:
            last_record = record.copy()
            
    return references

if __name__ == '__main__':
    file_path = 'references.txt'
    parsed_data = parse_references(file_path)

    # Compile the final consolidated list
    final_references = []
    seen = set()

    for item in parsed_data:
        # Create a unique key for each reference to detect duplicates
        unique_key = (
            tuple(sorted(item.get('author', []))),
            item.get('title', ''),
            item.get('year', '')
        )
        if unique_key not in seen:
            seen.add(unique_key)
            final_references.append(item)

    # Write the consolidated JSON to a file
    with open('references.json', 'w', encoding='utf-8') as json_file:
        json.dump(final_references, json_file, indent=2, ensure_ascii=False)

    print("References parsed and saved to references.json")
