"""
Google Cloud Storage service for attachment management.

Handles uploading attachments to GCS and generating signed URLs for secure downloads.
"""
import logging
import os
import json
import tempfile
from typing import Optional
from datetime import timedelta
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from google.oauth2 import service_account

from app.config import settings

logger = logging.getLogger(__name__)


class GCSStorageService:
    """Service for managing attachments in Google Cloud Storage."""

    def __init__(self):
        """Initialize GCS client."""
        try:
            # Step 1: Create a temporary client with default credentials to download the signing key
            logger.info("Creating temporary GCS client with default credentials to fetch signing key...")
            temp_client = storage.Client(project=settings.GCP_PROJECT_ID)

            # Step 2: Download the service account key from GCS
            credentials_blob_path = "credentials/gcs-key.json"
            logger.info(f"Downloading signing key from gs://{settings.GCS_BUCKET_NAME}/{credentials_blob_path}")

            try:
                bucket = temp_client.bucket(settings.GCS_BUCKET_NAME)
                blob = bucket.blob(credentials_blob_path)
                credentials_json = blob.download_as_text()
                logger.info("Successfully downloaded service account key from GCS")

                # Step 3: Load credentials from the downloaded JSON
                credentials_dict = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                logger.info(f"Loaded service account credentials: {credentials_dict.get('client_email')}")

                # Step 4: Create the real client with signing credentials
                self.client = storage.Client(
                    project=settings.GCP_PROJECT_ID,
                    credentials=credentials
                )
                logger.info("GCS client initialized with signing credentials - signed URLs will work!")

            except Exception as download_error:
                logger.error(f"Failed to download signing key from GCS: {download_error}")
                logger.warning("Falling back to default credentials (signed URLs will NOT work)")
                self.client = temp_client

            self.bucket_name = settings.GCS_BUCKET_NAME
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCS service ready for bucket: {self.bucket_name}")

        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}", exc_info=True)
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
