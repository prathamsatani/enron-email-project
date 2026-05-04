"""
Database Module
Handles SQLite database operations: schema creation, email storage, queries, duplicate flagging.
"""

import sqlite3
import os
from typing import Dict, List, Optional
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
        self.db_path = db_path
        self._ensure_directory(db_path)

    def _ensure_directory(self, db_path: str) -> None:
        directory = os.path.dirname(db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
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
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
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
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO recipients (message_id, email_address, recipient_type)
                VALUES (?, ?, ?)
            """, (message_id, email_addr, rec_type))
        except Exception as e:
            logger.debug(f"Error inserting recipient: {str(e)}")

    def get_email(self, message_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emails WHERE message_id = ?", (message_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_emails(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emails ORDER BY date ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_total_emails(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM emails")
            return cursor.fetchone()[0]

    def get_flagged_duplicates(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM emails
                WHERE is_duplicate = TRUE
                ORDER BY date DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def flag_as_duplicate(self, duplicate_msg_id: str, original_msg_id: str, similarity_score: float = None) -> bool:
        """
        Flag an email as duplicate, storing the original's message_id and similarity score.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE emails
                    SET is_duplicate = TRUE,
                        duplicate_of = ?,
                        similarity_score = ?
                    WHERE message_id = ?
                """, (original_msg_id, similarity_score, duplicate_msg_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error flagging duplicate: {str(e)}")
            return False

    def update_notification_sent(self, message_id: str) -> None:
        """Mark email notification as sent with current timestamp."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE emails
                    SET notification_sent = TRUE,
                        notification_date = CURRENT_TIMESTAMP
                    WHERE message_id = ?
                """, (message_id,))
        except Exception as e:
            logger.error(f"Error updating notification status: {str(e)}")

    def get_email_recipients(self, message_id: str, rec_type: Optional[str] = None) -> List[str]:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM emails")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM emails WHERE is_duplicate = TRUE")
            duplicates = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM emails WHERE notification_sent = TRUE")
            sent_notifications = cursor.fetchone()[0]
            return {
                'total_emails': total,
                'duplicate_emails': duplicates,
                'notifications_sent': sent_notifications,
            }

    def query_sample_1(self) -> List[Dict]:
        """Count emails per sender."""
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
        """Find emails in a date range."""
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
        """Find emails with CC recipients."""
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
