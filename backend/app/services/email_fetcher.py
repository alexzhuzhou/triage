"""
Email fetcher service for IMAP email retrieval.

Connects to email providers (Gmail, Outlook) via IMAP to fetch unread emails.
No OAuth required - uses app passwords for simplified authentication.
"""
import imaplib
import email
from email.message import Message
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailFetcher:
    """Fetches emails from IMAP server."""

    def __init__(
        self,
        imap_server: str,
        email_address: str,
        password: str,
        port: int = 993,
        use_ssl: bool = True
    ):
        """
        Initialize email fetcher.

        Args:
            imap_server: IMAP server address (e.g., 'imap.gmail.com')
            email_address: Email account to connect to
            password: App password (not regular password)
            port: IMAP port (default 993 for SSL)
            use_ssl: Use SSL connection (recommended)
        """
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.connection: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> None:
        """Establish IMAP connection."""
        try:
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.imap_server, self.port)
            else:
                self.connection = imaplib.IMAP4(self.imap_server, self.port)

            self.connection.login(self.email_address, self.password)
            logger.info(f"Successfully connected to {self.imap_server} as {self.email_address}")
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            raise

    def disconnect(self) -> None:
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")

    def fetch_unread_emails(self, mark_as_read: bool = True) -> List[Message]:
        """
        Fetch unread emails from inbox.

        Args:
            mark_as_read: Mark fetched emails as read (default True)

        Returns:
            List of email.Message objects
        """
        emails = []

        try:
            if not self.connection:
                self.connect()

            # Select inbox
            self.connection.select('INBOX')

            # Search for unread emails
            status, messages = self.connection.search(None, 'UNSEEN')

            if status != 'OK':
                logger.warning("No unread emails found")
                return emails

            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unread email(s)")

            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = self.connection.fetch(email_id, '(RFC822)')

                    if status != 'OK':
                        logger.warning(f"Failed to fetch email {email_id}")
                        continue

                    # Parse email
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    emails.append(email_message)

                    # Mark as read if requested
                    if mark_as_read:
                        self.connection.store(email_id, '+FLAGS', '\\Seen')
                        logger.debug(f"Marked email {email_id} as read")

                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise
        finally:
            self.disconnect()

        return emails

    def fetch_all_emails(self, limit: Optional[int] = None) -> List[Message]:
        """
        Fetch all emails from inbox (for testing).

        Args:
            limit: Maximum number of emails to fetch

        Returns:
            List of email.Message objects
        """
        emails = []

        try:
            if not self.connection:
                self.connect()

            # Select inbox
            self.connection.select('INBOX')

            # Search for all emails
            status, messages = self.connection.search(None, 'ALL')

            if status != 'OK':
                logger.warning("No emails found")
                return emails

            email_ids = messages[0].split()

            # Apply limit
            if limit:
                email_ids = email_ids[-limit:]

            logger.info(f"Fetching {len(email_ids)} email(s)")

            for email_id in email_ids:
                try:
                    status, msg_data = self.connection.fetch(email_id, '(RFC822)')

                    if status != 'OK':
                        continue

                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    emails.append(email_message)

                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise
        finally:
            self.disconnect()

        return emails
