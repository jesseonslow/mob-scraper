import argparse
import sys

from tasks.scrape_new import run_scrape_new
from tasks.cleanup import run_cleanup
from tasks.audit import run_audit
from tasks.generate_redirects import run_generate_redirects
from tasks.citation_audit import run_citation_audit
from tasks.build_publication_index import run_build_publication_index
from tasks.format_citations import run_format_citations

def main():
    """
    The main entry point for the command-line interface.
    """
    parser = argparse.ArgumentParser(
        description="A multi-purpose scraper and content management tool for the Moths of Borneo website."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

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

    audit_parser = subparsers.add_parser(
        "audit",
        help="Run a comprehensive audit on content files and generate a report."
    )
    audit_parser.set_defaults(handler=run_audit)

    citation_audit_parser = subparsers.add_parser(
        "citation-audit",
        help="Generate a report on the health of citations in all species files."
    )
    citation_audit_parser.set_defaults(handler=run_citation_audit)
    
    build_publication_index_parser = subparsers.add_parser(
        "build-publication-index",
        help="Build a publication index from all references.php files."
    )
    build_publication_index_parser.set_defaults(handler=run_build_publication_index)

    format_citations_parser = subparsers.add_parser(
        "format-citation",
        help="Finds and formats citations for a given publication, with an option to normalize the name."
    )
    format_citations_parser.add_argument(
        "publication",
        type=str,
        help="The title of the publication to find."
    )
    format_citations_parser.add_argument(
        "--to",
        type=str,
        dest="canonical_name",
        help="The new, canonical name to apply to the publication."
    )
    format_citations_parser.set_defaults(handler=run_format_citations)

    args = parser.parse_args()
    
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
        elif args.command == 'format-citation':
            args.handler(publication_title=args.publication, canonical_name=args.canonical_name)
        elif args.command in ['audit', 'redirects', 'citation-audit', 'build-publication-index']:
            args.handler()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()