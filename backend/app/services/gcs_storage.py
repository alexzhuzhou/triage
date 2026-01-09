"""
Google Cloud Storage service for attachment management.

Handles uploading attachments to GCS and generating signed URLs for secure downloads.
"""
import logging
from typing import Optional
from datetime import timedelta
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from app.config import settings

logger = logging.getLogger(__name__)


class GCSStorageService:
    """Service for managing attachments in Google Cloud Storage."""

    def __init__(self):
        """Initialize GCS client."""
        try:
            self.client = storage.Client(project=settings.GCP_PROJECT_ID)
            self.bucket_name = settings.GCS_BUCKET_NAME
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCS client initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            self.client = None
            self.bucket = None

    def upload_attachment(
        self,
        file_data: bytes,
        case_number: str,
        filename: str,
        content_type: str = "application/octet-stream"
    ) -> Optional[dict]:
        """
        Upload an attachment to Google Cloud Storage.

        Args:
            file_data: Binary file content
            case_number: Case number for organizing files (e.g., "NF-39281")
            filename: Original filename
            content_type: MIME type of the file

        Returns:
            dict with:
                - file_path: GCS URI (gs://bucket/path)
                - public_url: HTTPS URL (not publicly accessible without signed URL)
                - file_size: Size in bytes
                - storage_provider: "gcs"
            Returns None if upload fails.
        """
        if not self.client or not self.bucket:
            logger.warning("GCS client not initialized - skipping upload")
            return None

        try:
            # Create organized path: cases/{case_number}/{filename}
            blob_path = f"cases/{case_number}/{filename}"
            blob = self.bucket.blob(blob_path)

            # Upload binary data with explicit content type
            blob.upload_from_string(
                file_data,
                content_type=content_type
            )

            file_size = len(file_data)
            gcs_uri = f"gs://{self.bucket_name}/{blob_path}"

            logger.info(f"Uploaded {filename} to {gcs_uri} ({file_size} bytes)")

            return {
                "file_path": gcs_uri,
                "public_url": blob.public_url,  # Not actually public without bucket policy
                "file_size": file_size,
                "storage_provider": "gcs"
            }

        except GoogleCloudError as e:
            logger.error(f"GCS upload failed for {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading {filename}: {e}")
            return None

    def generate_signed_url(
        self,
        file_path: str,
        expiration_minutes: int = 60
    ) -> Optional[str]:
        """
        Generate a temporary signed URL for secure file download.

        Args:
            file_path: GCS URI (gs://bucket/path) or just the blob path
            expiration_minutes: URL validity duration (default 60 minutes)

        Returns:
            Signed URL string or None if generation fails
        """
        if not self.client or not self.bucket:
            logger.warning("GCS client not initialized - cannot generate signed URL")
            return None

        try:
            # Extract blob path from GCS URI if needed
            if file_path.startswith("gs://"):
                # Format: gs://bucket/path -> extract path
                blob_path = file_path.split(f"gs://{self.bucket_name}/", 1)[1]
            else:
                blob_path = file_path

            blob = self.bucket.blob(blob_path)

            # Generate signed URL with expiration
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )

            logger.info(f"Generated signed URL for {blob_path} (expires in {expiration_minutes}m)")
            return signed_url

        except GoogleCloudError as e:
            logger.error(f"Failed to generate signed URL for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating signed URL: {e}")
            return None

    def delete_attachment(self, file_path: str) -> bool:
        """
        Delete an attachment from GCS.

        Args:
            file_path: GCS URI (gs://bucket/path) or blob path

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.client or not self.bucket:
            logger.warning("GCS client not initialized - cannot delete")
            return False

        try:
            # Extract blob path from GCS URI
            if file_path.startswith("gs://"):
                blob_path = file_path.split(f"gs://{self.bucket_name}/", 1)[1]
            else:
                blob_path = file_path

            blob = self.bucket.blob(blob_path)
            blob.delete()

            logger.info(f"Deleted {blob_path} from GCS")
            return True

        except GoogleCloudError as e:
            logger.error(f"Failed to delete {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting {file_path}: {e}")
            return False


# Singleton instance
_gcs_service: Optional[GCSStorageService] = None


def get_gcs_service() -> GCSStorageService:
    """Get or create the GCS service singleton."""
    global _gcs_service
    if _gcs_service is None:
        _gcs_service = GCSStorageService()
    return _gcs_service
