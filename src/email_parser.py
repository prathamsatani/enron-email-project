"""
Email Parser Module
Parses RFC 2822 email files and extracts mandatory and optional fields.
Handles edge cases: malformed headers, encoding issues, multipart messages.
"""

import os
import sys
import email
from email import policy
from email.parser import BytesParser
from datetime import datetime
from datetime import timezone as stdlib_timezone
from dateutil import parser as date_parser
from dateutil import tz as dateutil_tz
import re
from typing import Dict, List, Optional, Tuple


class EmailParsingError(Exception):
    """Custom exception for email parsing errors."""
    pass


class EmailParser:
    """
    Parses RFC 2822 email files and extracts structured fields.
    """

    # Regex patterns
    QUOTED_CONTENT_PATTERN = re.compile(r'^(>|\s*On\s+.*?wrote:|-----Original Message-----)', re.MULTILINE)
    FORWARDED_PATTERN = re.compile(r'(---------- Forwarded message|Begin forwarded message)', re.IGNORECASE)
    HEADING_PATTERN = re.compile(r'^(#+\s+\w+|Subject:|From:|To:|Date:)', re.MULTILINE)

    # Timezone abbreviations to offset mapping
    TIMEZONE_MAP = {
        'PST': '-08:00', 'PDT': '-07:00',
        'MST': '-07:00', 'MDT': '-06:00',
        'CST': '-06:00', 'CDT': '-05:00',
        'EST': '-05:00', 'EDT': '-04:00',
    }

    def __init__(self):
        """Initialize parser statistics."""
        self.stats = {
            'total_files': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'field_completeness': {}
        }
        self.errors = []

    def parse_file(self, file_path: str) -> Optional[Dict]:
        """
        Parse a single email file.

        Args:
            file_path: Full path to email file

        Returns:
            Dictionary with extracted fields, or None if parsing failed
        """
        self.stats['total_files'] += 1

        try:
            # Windows normalizes away trailing periods in file paths; use \\?\ prefix
            # to bypass that, but we must NOT call abspath() on the full path because
            # abspath also strips trailing dots.  Instead, normalize the parent dir
            # (safe, no trailing dot there) and re-append the filename manually.
            open_path = file_path
            if sys.platform == 'win32' and os.path.basename(file_path).endswith('.'):
                parent = os.path.abspath(os.path.dirname(file_path))
                filename = os.path.basename(file_path)
                open_path = '\\\\?\\' + parent + '\\' + filename

            with open(open_path, 'rb') as f:
                content = f.read()

            # Parse email using BytesParser for better encoding handling
            msg = BytesParser(policy=policy.default).parsebytes(content)

            # Extract fields
            extracted = self._extract_fields(msg, file_path)
            self.stats['successful_parses'] += 1
            self._update_field_completeness(extracted)

            return extracted

        except Exception as e:
            self.stats['failed_parses'] += 1
            error_msg = f"Failed to parse {file_path}: {str(e)}"
            self.errors.append(error_msg)
            return None

    def _extract_fields(self, msg: email.message.Message, source_file: str) -> Dict:
        """Extract all mandatory and optional fields from email message."""

        extracted = {
            # Mandatory fields
            'message_id': self._extract_message_id(msg),
            'date': self._extract_date(msg),
            'from_address': self._extract_from(msg),
            'to_addresses': self._extract_to(msg),
            'subject': self._extract_subject(msg),
            'body': self._extract_body(msg),
            'source_file': source_file,

            # Optional fields
            'cc_addresses': self._extract_cc(msg),
            'bcc_addresses': self._extract_bcc(msg),
            'x_from': self._extract_x_header(msg, 'X-From'),
            'x_to': self._extract_x_header(msg, 'X-To'),
            'x_cc': self._extract_x_header(msg, 'X-cc'),
            'x_bcc': self._extract_x_header(msg, 'X-bcc'),
            'x_folder': self._extract_x_header(msg, 'X-Folder'),
            'x_origin': self._extract_x_header(msg, 'X-Origin'),
            'content_type': self._extract_content_type(msg),
            'has_attachment': self._has_attachment(msg),
            'forwarded_content': self._extract_forwarded_content(msg),
            'quoted_content': self._extract_quoted_content(msg),
            'headings': self._extract_headings(msg),
        }

        # Validate mandatory fields
        if not extracted['message_id']:
            raise EmailParsingError("Missing mandatory field: message_id")
        if not extracted['from_address']:
            raise EmailParsingError("Missing mandatory field: from_address")

        return extracted

    def _extract_message_id(self, msg: email.message.Message) -> Optional[str]:
        """Extract and validate Message-ID."""
        msg_id = msg.get('Message-ID', '').strip('<> ')
        return msg_id if msg_id else None

    def _extract_date(self, msg: email.message.Message) -> Optional[str]:
        """Extract and normalize date to UTC ISO format."""
        date_str = msg.get('Date', '')
        if not date_str:
            return None

        try:
            # Replace timezone abbreviations with offsets
            for tz_abbr, offset in self.TIMEZONE_MAP.items():
                date_str = re.sub(rf'\b{tz_abbr}\b', offset, date_str)

            # Parse the date
            dt = date_parser.parse(date_str, fuzzy=False)

            # Convert to UTC and format as ISO string
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dateutil_tz.tzutc())
            dt_utc = dt.astimezone(stdlib_timezone.utc)
            return dt_utc.isoformat()
        except Exception as e:
            # Log error but don't fail parsing
            self.errors.append(f"Date parsing error: {date_str} - {str(e)}")
            return None

    def _extract_from(self, msg: email.message.Message) -> Optional[str]:
        """Extract sender email address (not display name)."""
        from_str = msg.get('From', '')
        if not from_str:
            return None

        # Extract email from format: "Name <email@domain.com>" or just "email@domain.com"
        match = re.search(r'<([^>]+)>', from_str)
        if match:
            return match.group(1).strip()

        # If no angle brackets, try to extract email directly
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_str)
        if email_match:
            return email_match.group(0)

        return from_str.strip() if from_str else None

    def _extract_to(self, msg: email.message.Message) -> List[str]:
        """Extract all To: recipients."""
        return self._parse_recipient_list(msg, 'To')

    def _extract_cc(self, msg: email.message.Message) -> List[str]:
        """Extract all CC: recipients."""
        return self._parse_recipient_list(msg, 'Cc')

    def _extract_bcc(self, msg: email.message.Message) -> List[str]:
        """Extract all BCC: recipients."""
        return self._parse_recipient_list(msg, 'Bcc')

    def _parse_recipient_list(self, msg: email.message.Message, header: str) -> List[str]:
        """Parse comma/line-separated recipient list."""
        recipients_str = msg.get(header, '')
        if not recipients_str:
            return []

        # Split by comma and newline, handle multi-line headers
        recipients = []
        for part in re.split(r'[,\n]', recipients_str):
            part = part.strip()
            if not part:
                continue

            # Extract email from "Name <email>" format
            match = re.search(r'<([^>]+)>', part)
            if match:
                email_addr = match.group(1).strip()
            else:
                # Try to extract email directly
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', part)
                email_addr = email_match.group(0) if email_match else part

            if email_addr and email_addr not in recipients:
                recipients.append(email_addr)

        return recipients

    def _extract_subject(self, msg: email.message.Message) -> Optional[str]:
        """Extract subject line."""
        subject = msg.get('Subject', '')
        return subject.strip() if subject else None

    def _extract_body(self, msg: email.message.Message) -> Optional[str]:
        """Extract email body, handling multipart messages."""
        try:
            if msg.is_multipart():
                # Get first text part
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload.decode(errors='replace').strip()
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    return payload.decode(errors='replace').strip()

            return None
        except Exception as e:
            self.errors.append(f"Body extraction error: {str(e)}")
            return None

    def _extract_subject(self, msg: email.message.Message) -> Optional[str]:
        """Extract subject line."""
        subject = msg.get('Subject', '')
        if not subject:
            return None

        # Handle encoded-word subjects
        try:
            if '=?' in subject:
                from email.header import decode_header
                decoded = decode_header(subject)
                subject = ''.join(
                    part.decode(charset or 'utf-8') if isinstance(part, bytes) else part
                    for part, charset in decoded
                )
        except Exception:
            pass

        return subject.strip() if subject else None

    def _extract_x_header(self, msg: email.message.Message, header_name: str) -> Optional[str]:
        """Extract X-* header value."""
        value = msg.get(header_name, '')
        return value.strip() if value else None

    def _extract_content_type(self, msg: email.message.Message) -> Optional[str]:
        """Extract MIME content type."""
        return msg.get('Content-Type', '').split(';')[0].strip() or None

    def _has_attachment(self, msg: email.message.Message) -> bool:
        """Detect if email has attachments."""
        for part in msg.walk():
            if part.get('Content-Disposition', '').startswith('attachment'):
                return True
            # Check Content-Type for MIME boundary indicators
            if 'multipart' in part.get('Content-Type', '').lower():
                if part.get_payload() and len(part.get_payload()) > 1:
                    return True
        return False

    def _extract_forwarded_content(self, msg: email.message.Message) -> Optional[str]:
        """Extract forwarded message content."""
        body = self._extract_body(msg)
        if not body:
            return None

        # Find forwarded message marker
        match = self.FORWARDED_PATTERN.search(body)
        if match:
            return body[match.start():].strip()

        return None

    def _extract_quoted_content(self, msg: email.message.Message) -> Optional[str]:
        """Extract quoted/replied content."""
        body = self._extract_body(msg)
        if not body:
            return None

        # Find quoted content markers (lines starting with >, or quoted patterns)
        lines = body.split('\n')
        quoted_lines = []

        for line in lines:
            if re.match(r'^\s*>', line) or re.match(r'^\s*On\s+.*?wrote:', line):
                quoted_lines.append(line)

        return '\n'.join(quoted_lines).strip() if quoted_lines else None

    def _extract_headings(self, msg: email.message.Message) -> Optional[str]:
        """Extract headings from email body."""
        body = self._extract_body(msg)
        if not body:
            return None

        # Simple heading extraction (lines with markdown # or looking like headers)
        lines = body.split('\n')
        headings = []

        for line in lines:
            if re.match(r'^#+\s+', line):  # Markdown headings
                headings.append(line.strip())

        return '\n'.join(headings) if headings else None

    def _update_field_completeness(self, extracted: Dict) -> None:
        """Track field completion rates."""
        for field, value in extracted.items():
            if field not in self.stats['field_completeness']:
                self.stats['field_completeness'][field] = {'total': 0, 'present': 0}

            self.stats['field_completeness'][field]['total'] += 1
            if value is not None and (not isinstance(value, list) or len(value) > 0):
                self.stats['field_completeness'][field]['present'] += 1

    def get_statistics(self) -> Dict:
        """Return parsing statistics."""
        stats = {
            'total_files': self.stats['total_files'],
            'successful_parses': self.stats['successful_parses'],
            'failed_parses': self.stats['failed_parses'],
            'success_rate': (self.stats['successful_parses'] / max(self.stats['total_files'], 1)) * 100,
        }

        # Add field completeness rates
        field_completeness = {}
        for field, counts in self.stats['field_completeness'].items():
            rate = (counts['present'] / max(counts['total'], 1)) * 100
            field_completeness[field] = rate

        stats['field_completeness'] = field_completeness
        return stats

    def get_errors(self) -> List[str]:
        """Return list of parsing errors."""
        return self.errors
