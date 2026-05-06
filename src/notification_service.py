"""
Notification Service Module
Handles email notifications via MCP Gmail server integration.
Sends duplicate notification emails to senders of flagged duplicates.
"""

import base64
import os
import json
import csv
import logging
from email.mime.text import MIMEText
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Manages email notifications for duplicate flagging via MCP.
    """

    def __init__(self, database, mcp_config_path: Optional[str] = None):
        """
        Initialize notification service.

        Args:
            database: EmailDatabase instance
            mcp_config_path: Path to MCP configuration JSON
        """
        self.db = database
        self.mcp_config = self._load_mcp_config(mcp_config_path)
        self.sent_log = []

    def _load_mcp_config(self, config_path: Optional[str]) -> Dict:
        """
        Load MCP configuration from JSON file.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        if not config_path:
            config_path = os.getenv('MCP_CONFIG_PATH', 'mcp_config.json')

        if not os.path.exists(config_path):
            logger.warning(f"MCP config not found at {config_path}. Using defaults.")
            return {
                'enabled': False,
                'mcp_server_url': os.getenv('MCP_SERVER_URL', 'http://localhost:3000'),
                'gmail_account': os.getenv('GMAIL_ACCOUNT', ''),
            }

        try:
            with open(config_path, 'r') as f:
                raw = json.load(f)

            # Support both flat structure {"enabled": true, ...}
            # and legacy nested structure {"mcp_servers": {"gmail": {"enabled": true, ...}}}
            if 'mcp_servers' in raw:
                cfg = raw.get('mcp_servers', {}).get('gmail', {})
                cfg.setdefault('dry_run', raw.get('settings', {}).get('dry_run', True))
                return cfg
            return raw
        except Exception as e:
            logger.error(f"Error loading MCP config: {str(e)}")
            return {'enabled': False}

    def send_notifications(self, send_live: bool = False, output_dir: str = 'data/output') -> Dict:
        """
        Send (or draft) notifications for flagged duplicates.

        Args:
            send_live: If True, actually send emails. If False, generate drafts.
            output_dir: Directory for output files

        Returns:
            Summary statistics
        """
        os.makedirs(output_dir, exist_ok=True)

        duplicates = self.db.get_flagged_duplicates()
        stats = {
            'total_duplicates': len(duplicates),
            'notifications_sent': 0,
            'notifications_failed': 0,
            'drafts_generated': 0,
        }

        for duplicate in duplicates:
            result = self._process_duplicate(duplicate, send_live, output_dir)

            if result['status'] == 'sent':
                stats['notifications_sent'] += 1
            elif result['status'] == 'drafted':
                stats['drafts_generated'] += 1
            else:
                stats['notifications_failed'] += 1

            self.sent_log.append(result)

        return stats

    def _process_duplicate(self, duplicate: Dict, send_live: bool, output_dir: str) -> Dict:
        """
        Process a single duplicate: generate email, send or draft.

        Args:
            duplicate: Email record flagged as duplicate
            send_live: Whether to actually send the email
            output_dir: Output directory for draft files

        Returns:
            Status dictionary
        """
        try:
            # duplicate_of stores the original email's message_id (TEXT)
            original_msg_id = duplicate['duplicate_of']
            if not original_msg_id:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'recipient': duplicate['from_address'],
                    'subject': duplicate.get('subject', ''),
                    'status': 'failed',
                    'error': 'No original message ID found',
                }

            original = self.db.get_email(original_msg_id)
            if not original:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'recipient': duplicate['from_address'],
                    'subject': duplicate.get('subject', ''),
                    'status': 'failed',
                    'error': 'Could not retrieve original email',
                }

            # Compose notification email
            email_content = self._compose_notification(duplicate, original)

            if send_live:
                # Send via MCP
                return self._send_via_mcp(email_content, duplicate, original)
            else:
                # Generate draft file
                return self._generate_draft_file(email_content, duplicate, original, output_dir)

        except Exception as e:
            logger.error(f"Error processing duplicate {duplicate['message_id']}: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'recipient': duplicate.get('from_address', ''),
                'subject': duplicate.get('subject', ''),
                'status': 'failed',
                'error': str(e),
            }

    def _compose_notification(self, duplicate: Dict, original: Dict) -> Dict:
        """
        Compose notification email following the assignment template.

        Args:
            duplicate: Duplicate email record
            original: Original email record

        Returns:
            Email dictionary with to, subject, body
        """
        recipient = duplicate['from_address']
        original_subject = original['subject'] or '(no subject)'

        # Remove Re:/Fwd: prefixes for display
        import re
        display_subject = re.sub(r'^(re|fwd):\s*', '', original_subject, flags=re.IGNORECASE).strip()

        # Use actual similarity score stored in the database (defaults to 1.0 if missing)
        similarity_score = duplicate.get('similarity_score') or 1.0

        body = f"""To: {recipient}
Subject: [Duplicate Notice] Re: {display_subject}
Date: {datetime.now().isoformat()}
References: {duplicate['message_id']}

This is an automated notification from the Email Deduplication System.

Your email has been identified as a potential duplicate:

    Your Email (Flagged):
        Message-ID: {duplicate['message_id']}
        Date Sent: {duplicate['date']}
        Subject: {duplicate['subject']}

    Original Email on Record:
        Message-ID: {original['message_id']}
        Date Sent: {original['date']}
        Subject: {original['subject']}

    Similarity Score: {similarity_score:.1%}

If this was NOT a duplicate and you intended to send this email, please reply with CONFIRM to restore it to active status.

No action is required if this is indeed a duplicate.

---
Enron Email Deduplication System
"""

        return {
            'to': recipient,
            'subject': f'[Duplicate Notice] Re: {display_subject}',
            'body': body,
            'duplicate_msg_id': duplicate['message_id'],
            'original_msg_id': original['message_id'],
        }

    def _get_gmail_service(self):
        """Return an authenticated Gmail API service, refreshing tokens as needed."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Gmail API packages not installed. "
                "Run: pip install google-auth-oauthlib google-api-python-client"
            ) from exc

        scopes = ["https://www.googleapis.com/auth/gmail.send"]
        token_path = (
            self.mcp_config.get('token_file')
            or os.getenv('GMAIL_TOKEN_FILE', 'gmail_token.json')
        )
        creds_path = (
            self.mcp_config.get('authentication', {}).get('credentials_file')
            or os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
        )

        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {creds_path}. "
                        "Run setup_gmail_oauth.py first."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as fh:
                fh.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def _send_via_mcp(self, email_content: Dict, duplicate: Dict, original: Dict) -> Dict:
        """Send notification email via Gmail API."""
        if not self.mcp_config.get('enabled'):
            logger.warning("Gmail sending not enabled in mcp_config.json")
            return {
                'timestamp': datetime.now().isoformat(),
                'recipient': email_content['to'],
                'subject': email_content.get('subject', ''),
                'status': 'failed',
                'error': 'MCP not enabled in config',
            }

        try:
            service = self._get_gmail_service()

            msg = MIMEText(email_content['body'])
            msg['to'] = email_content['to']
            msg['subject'] = email_content['subject']
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

            result = service.users().messages().send(
                userId='me', body={'raw': raw}
            ).execute()

            logger.info(
                f"Sent notification to {email_content['to']}, Gmail ID: {result['id']}"
            )

            self.db.record_notification_sent(
                email_content['duplicate_msg_id'],
                email_content['to'],
                'sent',
            )
            self.db.update_notification_sent(email_content['duplicate_msg_id'])

            return {
                'timestamp': datetime.now().isoformat(),
                'recipient': email_content['to'],
                'subject': email_content['subject'],
                'status': 'sent',
                'error': '',
            }

        except Exception as e:
            logger.error(f"Error sending via Gmail API: {str(e)}")
            self.db.record_notification_sent(
                email_content['duplicate_msg_id'],
                email_content['to'],
                'failed',
                str(e),
            )
            return {
                'timestamp': datetime.now().isoformat(),
                'recipient': email_content['to'],
                'subject': email_content.get('subject', ''),
                'status': 'failed',
                'error': str(e),
            }

    def _generate_draft_file(self, email_content: Dict, duplicate: Dict, original: Dict, output_dir: str) -> Dict:
        """
        Generate draft email file (dry-run mode).

        Args:
            email_content: Composed email content
            duplicate: Duplicate record
            original: Original record
            output_dir: Output directory

        Returns:
            Status dictionary
        """
        replies_dir = os.path.join(output_dir, 'replies')
        os.makedirs(replies_dir, exist_ok=True)

        # Generate filename from message ID
        safe_msg_id = email_content['duplicate_msg_id'].replace('<', '').replace('>', '').replace('/', '_')
        filename = os.path.join(replies_dir, f"{safe_msg_id}.eml")

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(email_content['body'])

            logger.info(f"Generated draft email: {filename}")

            # Record draft as pending in notification log
            self.db.record_notification_sent(
                email_content['duplicate_msg_id'],
                email_content['to'],
                'pending'
            )

            return {
                'timestamp': datetime.now().isoformat(),
                'recipient': email_content['to'],
                'subject': email_content['subject'],
                'status': 'drafted',
                'error': '',
                'draft_file': filename,
            }

        except Exception as e:
            logger.error(f"Error generating draft: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'recipient': email_content['to'],
                'subject': email_content.get('subject', ''),
                'status': 'failed',
                'error': str(e),
                'draft_file': '',
            }

    def save_send_log(self, output_dir: str = 'data/output') -> str:
        """
        Save send log to CSV file.

        Args:
            output_dir: Output directory

        Returns:
            Path to log file
        """
        os.makedirs(output_dir, exist_ok=True)
        log_path = os.path.join(output_dir, 'send_log.csv')

        try:
            with open(log_path, 'w', newline='') as f:
                if self.sent_log:
                    fieldnames = self.sent_log[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.sent_log)

            logger.info(f"Send log saved to {log_path}")
            return log_path

        except Exception as e:
            logger.error(f"Error saving send log: {str(e)}")
            return None
