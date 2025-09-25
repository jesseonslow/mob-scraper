# mob-scraper/main.py

import argparse
import sys

from tasks.scrape_new import run_scrape_new
from tasks.cleanup import run_cleanup
from tasks.audit import run_audit
from tasks.generate_redirects import run_generate_redirects

def main():
    """
    The main entry point for the command-line interface.
    """
    parser = argparse.ArgumentParser(
        description="A multi-purpose scraper and content management tool for the Moths of Borneo website."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Parser for the "scrape" command ---
    scrape_parser = subparsers.add_parser(
        "scrape",
        help="Find and scrape new species entries that are missing."
    )
    scrape_parser.add_argument(
        '--generate-files',
        action='store_true',
        help="Run in 'live mode' to create new files. Default is a 'dry run' report."
    )
    scrape_parser.add_argument(
        '--interactive',
        action='store_true',
        help="Launch the interactive selector finder for books with missing or failing rules."
    )
    scrape_parser.set_defaults(handler=run_scrape_new)

    redirects_parser = subparsers.add_parser(
        "redirects",
        help="Generate a redirects.csv map from legacy URLs to new paths."
    )
    redirects_parser.set_defaults(handler=run_generate_redirects)

    # --- Parser for the "cleanup" command ---
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Perform various cleanup tasks on the frontmatter of existing files."
    )
    cleanup_parser.add_argument(
        '--images', action='store_true', help='Update and categorize image fields from the PHP source.'
    )
    cleanup_parser.add_argument(
        '--groups', action='store_true', help='Assign species to groups based on legacy URL rules.'
    )
    cleanup_parser.add_argument(
        '--fields', action='store_true', help='Remove redundant and null-valued fields.'
    )
    cleanup_parser.add_argument(
        '--citations', action='store_true', help='Repair malformed citation blocks that cause parsing errors.'
    )
    cleanup_parser.set_defaults(handler=run_cleanup)

    # --- Parser for the "audit" command ---
    audit_parser = subparsers.add_parser(
        "audit",
        help="Run audits on existing content, checking for empty or unfinished pages."
    )
    audit_parser.set_defaults(handler=run_audit)

    args = parser.parse_args()

    # Call the handler function associated with the chosen command
    if hasattr(args, 'handler'):
        if args.command == 'scrape':
            args.handler(generate_files=args.generate_files, interactive=args.interactive)
        elif args.command == 'cleanup':
            args.handler(
                images=args.images,
                groups=args.groups,
                fields=args.fields,
                citations=args.citations
            )
        elif args.command in ['audit', 'redirects']:
            args.handler() # Audit command doesn't need arguments
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()