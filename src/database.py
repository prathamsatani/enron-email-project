"""
Database Module
Handles SQLite database operations: schema creation, email storage, queries, duplicate flagging.
"""

import sqlite3
import os
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass


class EmailDatabase:
    """
    Manages SQLite database for email storage and queries.
    """

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_directory(db_path)
        self.connection = None

    def _ensure_directory(self, db_path: str) -> None:
        """Ensure directory exists for database file."""
        directory = os.path.dirname(db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """
        Initialize database schema from schema.sql file.
        """
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'schema.sql')

        if not os.path.exists(schema_path):
            raise DatabaseError(f"Schema file not found: {schema_path}")

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(schema_sql)
            logger.info("Database schema initialized")

    def store_email(self, email_data: Dict) -> bool:
        """
        Store parsed email in database.

        Args:
            email_data: Dictionary with email fields

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Insert into emails table
                cursor.execute("""
                    INSERT INTO emails (
                        message_id, date, from_address, subject, body, source_file,
                        content_type, has_attachment, forwarded_content, quoted_content,
                        headings, x_folder, x_origin
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    email_data['message_id'],
                    email_data['date'],
                    email_data['from_address'],
                    email_data['subject'],
                    email_data['body'],
                    email_data['source_file'],
                    email_data['content_type'],
                    email_data['has_attachment'],
                    email_data['forwarded_content'],
                    email_data['quoted_content'],
                    email_data['headings'],
                    email_data['x_folder'],
                    email_data['x_origin'],
                ))

                # Insert recipients into normalized table
                for email_addr in email_data.get('to_addresses', []):
                    self._insert_recipient(cursor, email_data['message_id'], email_addr, 'to')

                for email_addr in email_data.get('cc_addresses', []):
                    self._insert_recipient(cursor, email_data['message_id'], email_addr, 'cc')

                for email_addr in email_data.get('bcc_addresses', []):
                    self._insert_recipient(cursor, email_data['message_id'], email_addr, 'bcc')

                return True

        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' in str(e):
                logger.debug(f"Email already exists: {email_data['message_id']}")
                return False
            raise DatabaseError(f"Integrity error storing email: {str(e)}")
        except Exception as e:
            logger.error(f"Error storing email: {str(e)}")
            return False

    def _insert_recipient(self, cursor: sqlite3.Cursor, message_id: str, email_addr: str, rec_type: str) -> None:
        """Insert recipient, ignoring duplicates."""
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO recipients (message_id, email_address, recipient_type)
                VALUES (?, ?, ?)
            """, (message_id, email_addr, rec_type))
        except Exception as e:
            logger.debug(f"Error inserting recipient: {str(e)}")

    def get_email(self, message_id: str) -> Optional[Dict]:
        """Retrieve email by message_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emails WHERE message_id = ?", (message_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_emails(self) -> List[Dict]:
        """Retrieve all emails from database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emails")
            return [dict(row) for row in cursor.fetchall()]

    def get_total_emails(self) -> int:
        """Get total count of emails in database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM emails")
            return cursor.fetchone()[0]

    def get_flagged_duplicates(self) -> List[Dict]:
        """Get all emails flagged as duplicates."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emails WHERE is_duplicate = TRUE ORDER BY date DESC")
            return [dict(row) for row in cursor.fetchall()]

    def flag_as_duplicate(self, duplicate_msg_id: str, original_msg_id: str) -> bool:
        """
        Flag an email as duplicate of another.

        Args:
            duplicate_msg_id: Message ID of duplicate
            original_msg_id: Message ID of original

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get original email's database ID
                cursor.execute("SELECT id FROM emails WHERE message_id = ?", (original_msg_id,))
                original_row = cursor.fetchone()
                if not original_row:
                    logger.warning(f"Original email not found: {original_msg_id}")
                    return False

                original_id = original_row[0]

                # Update duplicate record
                cursor.execute("""
                    UPDATE emails
                    SET is_duplicate = TRUE, duplicate_of = ?
                    WHERE message_id = ?
                """, (original_id, duplicate_msg_id))

                return True

        except Exception as e:
            logger.error(f"Error flagging duplicate: {str(e)}")
            return False

    def get_email_recipients(self, message_id: str, rec_type: Optional[str] = None) -> List[str]:
        """
        Get recipients for an email.

        Args:
            message_id: Message ID
            rec_type: Filter by type ('to', 'cc', 'bcc'), or None for all

        Returns:
            List of email addresses
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if rec_type:
                cursor.execute(
                    "SELECT email_address FROM recipients WHERE message_id = ? AND recipient_type = ?",
                    (message_id, rec_type)
                )
            else:
                cursor.execute(
                    "SELECT email_address FROM recipients WHERE message_id = ?",
                    (message_id,)
                )

            return [row[0] for row in cursor.fetchall()]

    def record_notification_sent(self, duplicate_msg_id: str, recipient_email: str, status: str, error_msg: str = None) -> None:
        """Record that a notification was sent."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notification_sent (duplicate_message_id, recipient_email, status, error_message, sent_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (duplicate_msg_id, recipient_email, status, error_msg))
        except Exception as e:
            logger.error(f"Error recording notification: {str(e)}")

    def get_statistics(self) -> Dict:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total emails
            cursor.execute("SELECT COUNT(*) FROM emails")
            total = cursor.fetchone()[0]

            # Duplicates
            cursor.execute("SELECT COUNT(*) FROM emails WHERE is_duplicate = TRUE")
            duplicates = cursor.fetchone()[0]

            # Notifications
            cursor.execute("SELECT COUNT(*) FROM notification_sent WHERE status = 'sent'")
            sent_notifications = cursor.fetchone()[0]

            return {
                'total_emails': total,
                'duplicate_emails': duplicates,
                'notifications_sent': sent_notifications,
            }

    def query_sample_1(self) -> List[Dict]:
        """Sample Query 1: Count emails per sender."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT from_address, COUNT(*) as email_count
                FROM emails
                GROUP BY from_address
                ORDER BY email_count DESC
                LIMIT 10
            """)
            return [dict(row) for row in cursor.fetchall()]

    def query_sample_2(self) -> List[Dict]:
        """Sample Query 2: Find emails in a date range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message_id, date, from_address, subject
                FROM emails
                WHERE date BETWEEN '2000-01-01' AND '2002-12-31'
                ORDER BY date DESC
                LIMIT 20
            """)
            return [dict(row) for row in cursor.fetchall()]

    def query_sample_3(self) -> List[Dict]:
        """Sample Query 3: Find emails with CC recipients."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT e.message_id, e.from_address, e.subject,
                       GROUP_CONCAT(r.email_address, '; ') as cc_recipients
                FROM emails e
                JOIN recipients r ON e.message_id = r.message_id
                WHERE r.recipient_type = 'cc'
                GROUP BY e.message_id
                LIMIT 20
            """)
            return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
