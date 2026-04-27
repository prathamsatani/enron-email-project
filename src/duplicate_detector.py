"""
Duplicate Detection Module
Identifies duplicate emails based on sender, subject, and body similarity.
Uses fuzzy matching to find emails with 90%+ body content similarity.
"""

import re
from typing import Dict, List, Set, Tuple
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects and flags duplicate emails in the database.
    """

    SIMILARITY_THRESHOLD = 0.90  # 90% similarity threshold

    def __init__(self, database):
        """
        Initialize detector with database connection.

        Args:
            database: EmailDatabase instance
        """
        self.db = database
        self.duplicate_groups = []
        self.statistics = {
            'total_groups': 0,
            'total_flagged': 0,
            'group_sizes': []
        }

    def detect_duplicates(self) -> List[Dict]:
        """
        Detect duplicate emails in database.

        Returns:
            List of duplicate group information
        """
        emails = self.db.get_all_emails()
        if not emails:
            logger.warning("No emails in database")
            return []

        # Group emails by normalized sender and subject
        groups = self._group_by_signature(emails)

        # Find duplicates within each group
        duplicate_info = []
        processed = set()

        for group_key, group_emails in groups.items():
            if len(group_emails) < 2:
                continue

            # Find similar messages in this group
            for i, email1 in enumerate(group_emails):
                msg_id_1 = email1['message_id']
                if msg_id_1 in processed:
                    continue

                for email2 in group_emails[i+1:]:
                    msg_id_2 = email2['message_id']
                    if msg_id_2 in processed:
                        continue

                    # Check body similarity
                    similarity = self._calculate_similarity(
                        email1['body'],
                        email2['body']
                    )

                    if similarity >= self.SIMILARITY_THRESHOLD:
                        # Determine which is duplicate (latest)
                        if email1['date'] > email2['date']:
                            duplicate = email1
                            original = email2
                        else:
                            duplicate = email2
                            original = email1

                        duplicate_info.append({
                            'duplicate_msg_id': duplicate['message_id'],
                            'original_msg_id': original['message_id'],
                            'subject': duplicate['subject'],
                            'from_address': duplicate['from_address'],
                            'duplicate_date': duplicate['date'],
                            'original_date': original['date'],
                            'similarity_score': similarity,
                        })

                        processed.add(msg_id_2)

        # Group duplicates into clusters
        self._flag_duplicates_in_database(duplicate_info)

        return duplicate_info

    def _group_by_signature(self, emails: List[Dict]) -> Dict:
        """
        Group emails by normalized sender and subject.

        Args:
            emails: List of email dictionaries

        Returns:
            Dictionary mapping (from, subject) -> list of emails
        """
        groups = {}

        for email in emails:
            from_addr = email['from_address'] or ''
            subject = email['subject'] or ''

            # Normalize subject (remove Re:/Fwd: prefixes)
            normalized_subject = self._normalize_subject(subject)

            # Create signature
            signature = (from_addr.lower(), normalized_subject.lower())

            if signature not in groups:
                groups[signature] = []

            groups[signature].append(email)

        return groups

    def _normalize_subject(self, subject: str) -> str:
        """
        Normalize subject line (remove Re:/Fwd: prefixes).

        Args:
            subject: Original subject line

        Returns:
            Normalized subject
        """
        if not subject:
            return ''

        # Remove Re: and Fwd: prefixes (case-insensitive)
        normalized = re.sub(r'^(re|fwd):\s*', '', subject, flags=re.IGNORECASE).strip()

        # Remove multiple consecutive spaces
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate body content similarity using SequenceMatcher.

        Args:
            text1: First email body
            text2: Second email body

        Returns:
            Similarity score (0-1)
        """
        if not text1 or not text2:
            return 0.0

        # Normalize texts
        text1_norm = self._normalize_text(text1)
        text2_norm = self._normalize_text(text2)

        if not text1_norm or not text2_norm:
            return 0.0

        # Calculate similarity
        matcher = SequenceMatcher(None, text1_norm, text2_norm)
        return matcher.ratio()

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison (lowercase, remove extra whitespace).

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ''

        # Convert to lowercase
        text = text.lower()

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove quoted markers and forwarding artifacts
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Skip lines that are just quoted markers
            if re.match(r'^\s*[>]+\s*$', line):
                continue

            # Skip typical email boundaries
            if '-----' in line and 'message' in line.lower():
                continue

            cleaned_lines.append(line.strip())

        return ' '.join(cleaned_lines).strip()

    def _flag_duplicates_in_database(self, duplicate_info: List[Dict]) -> None:
        """
        Flag emails as duplicates in database and create duplicate groups.

        Args:
            duplicate_info: List of duplicate pair information
        """
        # Build groups (clusters of duplicate emails)
        groups = {}
        msg_to_group = {}

        for dup in duplicate_info:
            dup_msg_id = dup['duplicate_msg_id']
            orig_msg_id = dup['original_msg_id']

            # Find or create group
            if orig_msg_id in msg_to_group:
                group_id = msg_to_group[orig_msg_id]
            else:
                group_id = len(groups)
                groups[group_id] = {'original': orig_msg_id, 'duplicates': []}
                msg_to_group[orig_msg_id] = group_id

            # Add duplicate to group
            groups[group_id]['duplicates'].append(dup_msg_id)
            msg_to_group[dup_msg_id] = group_id

        # Flag all duplicates in database
        for group_id, group_info in groups.items():
            original_msg_id = group_info['original']

            for dup_msg_id in group_info['duplicates']:
                self.db.flag_as_duplicate(dup_msg_id, original_msg_id)

        # Update statistics
        self.statistics['total_groups'] = len(groups)
        self.statistics['total_flagged'] = len(duplicate_info)
        self.statistics['group_sizes'] = [len(g['duplicates']) + 1 for g in groups.values()]

        logger.info(f"Duplicate detection complete: {len(groups)} groups, "
                   f"{len(duplicate_info)} emails flagged")

    def get_statistics(self) -> Dict:
        """Get duplicate detection statistics."""
        stats = self.statistics.copy()

        if stats['group_sizes']:
            stats['average_group_size'] = sum(stats['group_sizes']) / len(stats['group_sizes'])
        else:
            stats['average_group_size'] = 0

        return stats

    def generate_report(self, duplicate_info: List[Dict]) -> str:
        """
        Generate CSV report of duplicates.

        Args:
            duplicate_info: List of duplicate pair information

        Returns:
            CSV content as string
        """
        if not duplicate_info:
            return "duplicate_message_id,original_message_id,subject,from_address,duplicate_date,original_date,similarity_score\n"

        lines = ["duplicate_message_id,original_message_id,subject,from_address,duplicate_date,original_date,similarity_score"]

        for dup in duplicate_info:
            line = (
                f"\"{dup['duplicate_msg_id']}\","
                f"\"{dup['original_msg_id']}\","
                f"\"{dup['subject']}\","
                f"\"{dup['from_address']}\","
                f"\"{dup['duplicate_date']}\","
                f"\"{dup['original_date']}\","
                f"{dup['similarity_score']:.4f}"
            )
            lines.append(line)

        return '\n'.join(lines) + '\n'
