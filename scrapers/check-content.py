import collections
from pathlib import Path
import frontmatter

# --- Configuration ---
TARGET_DIRECTORY = Path("./src/content/species/")
REPORT_FILENAME = "report.html"

# --- HTML & CSS Template with embedded JavaScript for sorting ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Quality Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            background-color: #f9f9f9;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 900px;
            margin: 20px auto;
            padding: 20px;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px_4px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #1a1a1a;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        h2 {{ margin-top: 40px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        thead th {{
            background-color: #f2f2f2;
            cursor: pointer;
            user-select: none;
        }}
        thead th:hover {{ background-color: #e9e9e9; }}
        tbody tr:nth-of-type(even) {{ background-color: #fcfcfc; }}
        ul {{ list-style-type: none; padding-left: 0; }}
        li {{
            background-color: #fdfdfd; border: 1px solid #eee;
            padding: 10px; margin-bottom: 5px; border-radius: 4px;
        }}
        code {{
            background-color: #eef; padding: 2px 5px;
            border-radius: 3px; font-family: "Courier New", Courier, monospace;
        }}
        strong {{ color: #c0392b; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Content Quality Report</h1>
        
        <h2>Summary</h2>
        <ul>
            <li>Total pages with NO content: <strong>{total_empty}</strong></li>
            <li>Total pages with UNFINISHED content: <strong>{total_unfinished}</strong></li>
        </ul>

        <h2>Book Breakdown</h2>
        <table id="book-breakdown-table">
            <thead>
                <tr>
                    <th onclick="sortTable(0, 'str')">Book Name</th>
                    <th onclick="sortTable(1, 'num')">Empty</th>
                    <th onclick="sortTable(2, 'num')">% Empty</th>
                    <th onclick="sortTable(3, 'num')">Unfinished</th>
                    <th onclick="sortTable(4, 'num')">% Unfinished</th>
                    <th onclick="sortTable(5, 'num')">Total Files</th>
                </tr>
            </thead>
            <tbody>
                {book_breakdown_table_body}
            </tbody>
        </table>

        <h2>Files with NO Content ({total_empty} total)</h2>
        {empty_files_html}

        <h2>Files with UNFINISHED Content ({total_unfinished} total)</h2>
        {unfinished_files_html}
    </div>
<script>
    let sortDirection = {{}};

    function sortTable(columnIndex, type) {{
        const table = document.getElementById("book-breakdown-table");
        const tbody = table.querySelector("tbody");
        const rows = Array.from(tbody.querySelectorAll("tr"));

        const direction = sortDirection[columnIndex] === 'asc' ? 'desc' : 'asc';
        sortDirection = {{ [columnIndex]: direction }};

        rows.sort((a, b) => {{
            const aText = a.cells[columnIndex].textContent.trim();
            const bText = b.cells[columnIndex].textContent.trim();

            if (type === 'num') {{
                const aNum = parseFloat(aText.replace('%', ''));
                const bNum = parseFloat(bText.replace('%', ''));
                return direction === 'asc' ? aNum - bNum : bNum - aNum;
            }} else {{
                return direction === 'asc' ? aText.localeCompare(bText) : bText.localeCompare(aText);
            }}
        }});

        tbody.innerHTML = "";
        rows.forEach(row => tbody.appendChild(row));
    }}
</script>
</body>
</html>
"""

def format_list_as_html(items):
    """Helper function to format a Python list of filenames into an HTML list."""
    if not items:
        return "<p>None found.</p>"
    list_items = "".join(f"<li><code>{item}</code></li>" for item in sorted(items))
    return f"<ul>{list_items}</ul>"

def generate_html_report(empty_files, unfinished_files, book_data):
    """Generates and saves the final HTML report file."""
    
    # Generate the HTML table rows from our processed book data
    table_rows = []
    for book, data in sorted(book_data.items()):
        total = data['total']
        empty = data['empty']
        unfinished = data['unfinished']
        
        percent_empty = (empty / total * 100) if total > 0 else 0
        percent_unfinished = (unfinished / total * 100) if total > 0 else 0
        
        table_rows.append(f"""
        <tr>
            <td>{book}</td>
            <td>{empty}</td>
            <td>{percent_empty:.1f}%</td>
            <td>{unfinished}</td>
            <td>{percent_unfinished:.1f}%</td>
            <td>{total}</td>
        </tr>""")
    
    book_breakdown_table_body = "".join(table_rows)

    final_html = HTML_TEMPLATE.format(
        total_empty=len(empty_files),
        total_unfinished=len(unfinished_files),
        book_breakdown_table_body=book_breakdown_table_body,
        empty_files_html=format_list_as_html(empty_files),
        unfinished_files_html=format_list_as_html(unfinished_files)
    )

    with open(REPORT_FILENAME, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"\n✅ Report successfully generated: {REPORT_FILENAME}")

def main():
    if not TARGET_DIRECTORY.is_dir():
        print(f"Error: Directory not found at '{TARGET_DIRECTORY}'")
        return

    print(f"Scanning for markdown files in '{TARGET_DIRECTORY}'...")

    empty_content_files = []
    unfinished_content_files = []
    # Use a nested defaultdict to store all stats for each book
    book_data = collections.defaultdict(lambda: collections.defaultdict(int))

    for file_path in TARGET_DIRECTORY.glob('**/*.md*'):
        if not file_path.is_file():
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            clean_content = post.content.strip()
            book = post.metadata.get('book', 'Unknown Book')

            # Increment total count for every file
            book_data[book]['total'] += 1

            if not clean_content:
                empty_content_files.append(file_path.name)
                book_data[book]['empty'] += 1
            elif not clean_content.endswith('.'):
                unfinished_content_files.append(file_path.name)
                book_data[book]['unfinished'] += 1

        except Exception as e:
            print(f"  [ERROR] Could not process {file_path.name}: {e}")
    
    generate_html_report(empty_content_files, unfinished_content_files, book_data)

if __name__ == "__main__":
    main()