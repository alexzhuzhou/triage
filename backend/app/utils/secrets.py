"""
Google Cloud Secret Manager utility.

Fetches secrets from Secret Manager using Application Default Credentials (ADC).
Works seamlessly in Cloud Run with the service account's credentials.
"""
import logging
from typing import Optional
from google.auth import default as google_auth_default
from google.cloud.secretmanager_v1 import SecretManagerServiceClient

logger = logging.getLogger(__name__)


def get_secret(secret_name: str, project_id: str = "premium-oven-394418") -> Optional[str]:
    """
    Fetch a secret from Google Cloud Secret Manager using ADC credentials.

    This function uses Application Default Credentials (ADC) which automatically works:
    - In Cloud Run: Uses the service account assigned to the Cloud Run service
    - Locally: Uses credentials from `gcloud auth application-default login`

    Args:
        secret_name: Name of the secret in Secret Manager (e.g., "database-url")
        project_id: GCP project ID (defaults to premium-oven-394418)

    Returns:
        The secret value as a string, or None if retrieval fails

    Raises:
        No exceptions - returns None on any failure and logs warning
    """
    try:
        # Get default credentials (service account in Cloud Run, gcloud credentials locally)
        creds, inferred_project = google_auth_default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        project = project_id or inferred_project

        # Create Secret Manager client
        client = SecretManagerServiceClient(credentials=creds)

        # Build secret path (always use "latest" version)
        secret_path = f"projects/{project}/secrets/{secret_name}/versions/latest"

        # Fetch secret value
        response = client.access_secret_version(request={"name": secret_path})
        secret_value = response.payload.data.decode("UTF-8")

        logger.info(f"✅ Retrieved secret '{secret_name}' from Secret Manager")
        return secret_value

    except Exception as e:
        logger.warning(
            f"⚠️  Could not retrieve secret '{secret_name}' from Secret Manager: {e}. "
            f"Falling back to environment variable if available."
        )
        return None
