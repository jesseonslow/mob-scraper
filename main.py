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
        '--force',
        action='store_true',
        help="Ignore validation checks and generate all creatable files, even with low confidence."
    )
    scrape_parser.add_argument(
        '--interactive',
        action='store_true',
        help="Launch the interactive selector finder for books with missing or failing rules."
    )
    scrape_parser.set_defaults(handler=run_scrape_new)

    # (rest of the parsers are unchanged)

    args = parser.parse_args()
    
    # --- THIS IS THE FIX ---
    # If --force is used, it should always imply that we are generating files.
    if hasattr(args, 'force') and args.force:
        args.generate_files = True

    if hasattr(args, 'handler'):
        if args.command == 'scrape':
            args.handler(generate_files=args.generate_files, interactive=args.interactive, force=args.force)
        elif args.command == 'cleanup':
            args.handler(
                images=args.images,
                groups=args.groups,
                fields=args.fields,
                citations=args.citations
            )
        elif args.command in ['audit', 'redirects']:
            args.handler()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()