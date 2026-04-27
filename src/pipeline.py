"""
Pipeline Module
Orchestrates the entire email extraction and processing pipeline.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from src.email_parser import EmailParser
from src.database import EmailDatabase
from src.duplicate_detector import DuplicateDetector
from src.notification_service import NotificationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailExtractionPipeline:
    """
    Main pipeline for email extraction, storage, duplicate detection, and notification.
    """

    def __init__(self, maildir_path: str, db_path: str, error_log_path: str = None):
        """
        Initialize pipeline.

        Args:
            maildir_path: Root directory of Enron maildir
            db_path: Path to SQLite database
            error_log_path: Path to error log file
        """
        self.maildir_path = maildir_path
        self.db_path = db_path
        self.error_log_path = error_log_path or os.path.join(os.path.dirname(db_path), 'error_log.txt')

        self.parser = EmailParser()
        self.db = EmailDatabase(db_path)
        self.detector = None
        self.notifier = None

        self.statistics = {}

    def run(self, send_live: bool = False) -> Dict:
        """
        Execute full pipeline.

        Args:
            send_live: If True, send emails. If False, generate drafts.

        Returns:
            Summary statistics
        """
        logger.info("=" * 60)
        logger.info("Starting Email Extraction Pipeline")
        logger.info("=" * 60)

        try:
            # Step 1: Initialize database
            logger.info("Step 1: Initializing database...")
            self.db.initialize_schema()

            # Step 2: Discover and parse emails
            logger.info("Step 2: Discovering and parsing emails...")
            self._extract_and_store_emails()

            # Step 3: Log parse statistics
            logger.info("Step 3: Analyzing parse statistics...")
            self._log_parse_statistics()

            # Step 4: Detect duplicates
            logger.info("Step 4: Detecting duplicates...")
            self._detect_and_flag_duplicates()

            # Step 5: Send notifications (or generate drafts)
            logger.info("Step 5: Processing notifications...")
            self._process_notifications(send_live)

            # Step 6: Generate summary reports
            logger.info("Step 6: Generating summary reports...")
            self._generate_reports()

            logger.info("=" * 60)
            logger.info("Pipeline completed successfully!")
            logger.info("=" * 60)

            return self.statistics

        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            raise

    def _extract_and_store_emails(self) -> None:
        """Discover and parse all email files, store in database."""
        email_files = self._discover_email_files()
        logger.info(f"Found {len(email_files)} email files")

        stored_count = 0
        for idx, email_file in enumerate(email_files, 1):
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{len(email_files)} emails processed")

            # Parse email
            parsed_data = self.parser.parse_file(email_file)

            if parsed_data:
                # Store in database
                if self.db.store_email(parsed_data):
                    stored_count += 1

        logger.info(f"Stored {stored_count} emails in database")
        self.statistics['extraction'] = {
            'total_files': self.parser.stats['total_files'],
            'successfully_parsed': self.parser.stats['successful_parses'],
            'failed_parses': self.parser.stats['failed_parses'],
            'stored_in_db': stored_count,
        }

    def _discover_email_files(self) -> List[str]:
        """
        Recursively discover all .eml email files in maildir.

        Returns:
            List of email file paths
        """
        email_files = []

        for root, dirs, files in os.walk(self.maildir_path):
            for file in files:
                if file.isdigit():  # Enron emails are named with numbers
                    filepath = os.path.join(root, file)
                    email_files.append(filepath)

        return sorted(email_files)

    def _log_parse_statistics(self) -> None:
        """Log and save parse statistics."""
        stats = self.parser.get_statistics()

        logger.info("\n" + "=" * 60)
        logger.info("PARSE STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total files found: {stats['total_files']}")
        logger.info(f"Successfully parsed: {stats['successfully_parsed']}")
        logger.info(f"Failed to parse: {stats['failed_parses']}")
        logger.info(f"Success rate: {stats['success_rate']:.2f}%")

        logger.info("\nField Completeness Rates:")
        for field, rate in sorted(stats['field_completeness'].items()):
            logger.info(f"  {field}: {rate:.2f}%")

        # Save error log
        errors = self.parser.get_errors()
        if errors:
            logger.info(f"\nSaving {len(errors)} parse errors to {self.error_log_path}")
            os.makedirs(os.path.dirname(self.error_log_path) or '.', exist_ok=True)
            with open(self.error_log_path, 'w') as f:
                for error in errors:
                    f.write(error + '\n')

        self.statistics['parse_statistics'] = stats

    def _detect_and_flag_duplicates(self) -> None:
        """Run duplicate detection on stored emails."""
        self.detector = DuplicateDetector(self.db)
        duplicate_info = self.detector.detect_duplicates()

        logger.info(f"\nDuplicate detection complete:")
        logger.info(f"  Total duplicate groups: {self.detector.statistics['total_groups']}")
        logger.info(f"  Total emails flagged: {self.detector.statistics['total_flagged']}")

        if self.detector.statistics['group_sizes']:
            avg_group_size = sum(self.detector.statistics['group_sizes']) / len(self.detector.statistics['group_sizes'])
            logger.info(f"  Average group size: {avg_group_size:.2f}")

        # Save duplicates report
        duplicates_report_path = os.path.join(os.path.dirname(self.db_path), 'duplicates_report.csv')
        os.makedirs(os.path.dirname(duplicates_report_path) or '.', exist_ok=True)

        report_content = self.detector.generate_report(duplicate_info)
        with open(duplicates_report_path, 'w') as f:
            f.write(report_content)

        logger.info(f"Duplicates report saved to {duplicates_report_path}")

        self.statistics['duplicate_detection'] = self.detector.get_statistics()

    def _process_notifications(self, send_live: bool) -> None:
        """Process notifications for flagged duplicates."""
        self.notifier = NotificationService(self.db)

        output_dir = os.path.dirname(self.db_path)
        notification_stats = self.notifier.send_notifications(send_live=send_live, output_dir=output_dir)

        logger.info("\nNotification Processing:")
        logger.info(f"  Total duplicates processed: {notification_stats['total_duplicates']}")
        logger.info(f"  Notifications sent (live): {notification_stats['notifications_sent']}")
        logger.info(f"  Drafts generated: {notification_stats['drafts_generated']}")
        logger.info(f"  Failed: {notification_stats['notifications_failed']}")

        # Save send log
        send_log_path = self.notifier.save_send_log(output_dir)
        if send_log_path:
            logger.info(f"Send log saved to {send_log_path}")

        self.statistics['notification'] = notification_stats

    def _generate_reports(self) -> None:
        """Generate summary reports."""
        db_stats = self.db.get_statistics()

        logger.info("\n" + "=" * 60)
        logger.info("DATABASE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total emails in database: {db_stats['total_emails']}")
        logger.info(f"Duplicate emails flagged: {db_stats['duplicate_emails']}")
        logger.info(f"Notifications sent: {db_stats['notifications_sent']}")

        self.statistics['database_summary'] = db_stats

    def print_summary(self) -> None:
        """Print execution summary."""
        logger.info("\n" + "=" * 60)
        logger.info("EXECUTION SUMMARY")
        logger.info("=" * 60)

        if 'extraction' in self.statistics:
            ext = self.statistics['extraction']
            logger.info(f"Extraction: {ext['stored_in_db']}/{ext['total_files']} emails stored")

        if 'duplicate_detection' in self.statistics:
            dup = self.statistics['duplicate_detection']
            logger.info(f"Duplicates: {dup['total_flagged']} duplicates found in {dup['total_groups']} groups")

        if 'notification' in self.statistics:
            notif = self.statistics['notification']
            logger.info(f"Notifications: {notif['notifications_sent']} sent, {notif['drafts_generated']} drafted")
