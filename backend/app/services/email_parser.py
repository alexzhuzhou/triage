"""
Email parser service to convert email.Message to EmailIngest schema.

Adapts real email format to our application's internal schema.
"""
import email
from email.message import Message
from email.header import decode_header
from typing import List
from datetime import datetime
import logging

from app.schemas.email import EmailIngest, AttachmentData
from app.config import settings

logger = logging.getLogger(__name__)


class EmailParser:
    """Parses email.Message objects to EmailIngest schema."""

    @staticmethod
    def decode_header_value(header_value: str) -> str:
        """
        Decode email header value.

        Args:
            header_value: Raw header value

        Returns:
            Decoded string
        """
        if not header_value:
            return ""

        decoded_parts = decode_header(header_value)
        decoded_string = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_string += part

        return decoded_string

    @staticmethod
    def extract_email_addresses(header_value: str) -> List[str]:
        """
        Extract email addresses from header (To, Cc, From).

        Args:
            header_value: Raw header value

        Returns:
            List of email addresses
        """
        if not header_value:
            return []

        # Decode header
        decoded = EmailParser.decode_header_value(header_value)

        # Extract email addresses (simple parsing)
        # Format: "Name <email@example.com>" or "email@example.com"
        emails = []
        for part in decoded.split(','):
            part = part.strip()
            if '<' in part and '>' in part:
                # Extract from "Name <email>"
                start = part.index('<') + 1
                end = part.index('>')
                emails.append(part[start:end])
            elif '@' in part:
                # Plain email address
                emails.append(part)

        return emails

    @staticmethod
    def extract_body(email_message: Message) -> str:
        """
        Extract email body text.

        Args:
            email_message: Email message object

        Returns:
            Email body as plain text
        """
        body = ""

        try:
            # Check if multipart
            if email_message.is_multipart():
                # Walk through email parts
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))

                    # Skip attachments
                    if 'attachment' in content_disposition:
                        continue

                    # Get text/plain content
                    if content_type == 'text/plain':
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            body += payload.decode(charset, errors='ignore')

                    # Fallback to text/html if no plain text
                    elif content_type == 'text/html' and not body:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            html_body = payload.decode(charset, errors='ignore')
                            # Simple HTML stripping (not perfect, but works for demo)
                            import re
                            body = re.sub('<[^<]+?>', '', html_body)

            else:
                # Not multipart - get payload directly
                payload = email_message.get_payload(decode=True)
                if payload:
                    charset = email_message.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='ignore')

        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            body = "[Error extracting email body]"

        return body.strip()

    @staticmethod
    def extract_attachments(email_message: Message) -> List[AttachmentData]:
        """
        Extract attachment metadata from email.

        Note: Does not extract actual file content or perform OCR.
        For this simplified version, text_content is None.

        Args:
            email_message: Email message object

        Returns:
            List of AttachmentData objects
        """
        attachments = []

        try:
            if not email_message.is_multipart():
                return attachments

            for part in email_message.walk():
                content_disposition = str(part.get('Content-Disposition', ''))

                # Check if this is an attachment
                if 'attachment' in content_disposition:
                    filename = part.get_filename()

                    if filename:
                        # Decode filename if needed
                        filename = EmailParser.decode_header_value(filename)

                        content_type = part.get_content_type()

                        # Get binary payload
                        payload = part.get_payload(decode=True)

                        # Initialize fields
                        text_content = None
                        pdf_images = None

                        # Handle PDF attachments with image conversion
                        if content_type == 'application/pdf' and payload and settings.PDF_CONVERSION_ENABLED:
                            try:
                                from app.services.pdf_converter import convert_pdf_to_images
                                pdf_images = convert_pdf_to_images(payload)
                                logger.info(f"Converted PDF {filename} to {len(pdf_images)} images")
                            except Exception as e:
                                logger.warning(f"PDF conversion failed for {filename}: {e}")
                                # Fallback: Try pypdf text extraction
                                try:
                                    import pypdf
                                    import io
                                    reader = pypdf.PdfReader(io.BytesIO(payload))
                                    text_content = " ".join(
                                        page.extract_text() for page in reader.pages
                                    )[:1000]
                                    logger.debug(f"Fell back to text extraction for {filename}")
                                except Exception as fallback_error:
                                    logger.debug(f"Text extraction also failed for {filename}: {fallback_error}")

                        # Handle text attachments
                        elif content_type.startswith('text/') and payload:
                            try:
                                charset = part.get_content_charset() or 'utf-8'
                                # Limit to first 1000 chars
                                text_content = payload.decode(charset, errors='ignore')[:1000]
                            except Exception as e:
                                logger.debug(f"Could not extract text from {filename}: {e}")

                        attachments.append(AttachmentData(
                            filename=filename,
                            content_type=content_type,
                            text_content=text_content,
                            pdf_images=pdf_images,
                            binary_content=payload  # Store original binary for GCS upload
                        ))

        except Exception as e:
            logger.error(f"Error extracting attachments: {e}")

        return attachments

    @staticmethod
    def parse_to_ingest(email_message: Message) -> EmailIngest:
        """
        Convert email.Message to EmailIngest schema.

        Args:
            email_message: Email message object from IMAP

        Returns:
            EmailIngest object ready for processing
        """
        try:
            # Extract headers
            subject = EmailParser.decode_header_value(email_message.get('Subject', ''))
            from_header = email_message.get('From', '')
            to_header = email_message.get('To', '')
            cc_header = email_message.get('Cc', '')
            date_header = email_message.get('Date', '')

            # Parse sender
            sender_list = EmailParser.extract_email_addresses(from_header)
            sender = sender_list[0] if sender_list else 'unknown@example.com'

            # Parse recipients (To + Cc)
            recipients = EmailParser.extract_email_addresses(to_header)
            recipients.extend(EmailParser.extract_email_addresses(cc_header))

            if not recipients:
                recipients = ['unknown@example.com']

            # Extract body
            body = EmailParser.extract_body(email_message)

            # Extract attachments
            attachments = EmailParser.extract_attachments(email_message)

            # Parse received date (optional - will default to now if not provided)
            received_at = None
            if date_header:
                try:
                    # Parse email date to datetime
                    from email.utils import parsedate_to_datetime
                    received_at = parsedate_to_datetime(date_header)
                except Exception as e:
                    logger.warning(f"Could not parse email date: {e}")

            return EmailIngest(
                subject=subject,
                sender=sender,
                recipients=recipients,
                body=body,
                attachments=attachments,
                received_at=received_at
            )

        except Exception as e:
            logger.error(f"Error parsing email to ingest schema: {e}")
            raise
