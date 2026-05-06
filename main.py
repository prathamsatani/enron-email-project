#!/usr/bin/env python3
"""
Main Entry Point
Executes the full Enron email extraction and processing pipeline.

Usage:
    python main.py --maildir-path ./data/enron_mail --db-path ./data/output/database.db
    python main.py --maildir-path ./data/enron_mail --db-path ./data/output/database.db --send-live
"""

import sys
import argparse
import logging
from pathlib import Path

from src.pipeline import EmailExtractionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Enron Email Extraction & Deduplication Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract and store emails (dry-run for email notifications)
  python main.py --maildir-path ./data/enron_mail --db-path ./data/output/database.db

  # Extract, store, and send live email notifications
  python main.py --maildir-path ./data/enron_mail --db-path ./data/output/database.db --send-live

  # Use custom error log path
  python main.py --maildir-path ./data/enron_mail --db-path ./data/output/database.db --error-log ./logs/errors.txt
        """
    )

    parser.add_argument(
        '--maildir-path',
        required=True,
        help='Path to Enron maildir root directory'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=50000,
        help='Maximum number of emails to process (default: 50000)'
    )


    parser.add_argument(
        '--db-path',
        required=True,
        help='Path to SQLite database file'
    )

    parser.add_argument(
        '--error-log',
        help='Path to error log file (default: data/output/error_log.txt)'
    )

    parser.add_argument(
        '--send-live',
        action='store_true',
        help='Actually send emails via MCP (default: generate drafts only)'
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    try:
        args = parse_arguments()

        # Validate paths
        if not Path(args.maildir_path).exists():
            logger.error(f"Maildir path does not exist: {args.maildir_path}")
            return 1

        # Ensure output directory exists
        db_dir = Path(args.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Create and run pipeline
        pipeline = EmailExtractionPipeline(
            maildir_path=args.maildir_path,
            db_path=args.db_path,
            error_log_path=args.error_log
        )

        # Execute pipeline
        statistics = pipeline.run(send_live=args.send_live, limit=50000)
        pipeline.print_summary()

        logger.info("Pipeline execution completed successfully!")
        return 0

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
