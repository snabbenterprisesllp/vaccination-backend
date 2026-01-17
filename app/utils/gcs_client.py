"""Google Cloud Storage client"""
from google.cloud import storage
from typing import Optional
from datetime import timedelta
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class GCSClient:
    """Google Cloud Storage client wrapper"""
    
    def __init__(self):
        try:
            self.client = storage.Client(project=settings.GCP_PROJECT_ID)
            self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
        except Exception as e:
            logger.warning(f"Failed to initialize GCS client: {e}")
            self.client = None
            self.bucket = None
    
    async def upload_file(
        self,
        file_data: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Upload file to GCS"""
        if not self.bucket:
            raise Exception("GCS client not initialized")
        
        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_string(file_data, content_type=content_type)
            
            # Make blob public (or generate signed URL)
            blob.make_public()
            
            return blob.public_url
        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {e}")
            raise
    
    async def generate_signed_url(
        self,
        blob_path: str,
        expiration_minutes: int = 60
    ) -> str:
        """Generate signed URL for private access"""
        if not self.bucket:
            raise Exception("GCS client not initialized")
        
        try:
            blob = self.bucket.blob(blob_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            raise
    
    async def delete_file(self, blob_path: str) -> bool:
        """Delete file from GCS"""
        if not self.bucket:
            raise Exception("GCS client not initialized")
        
        try:
            blob = self.bucket.blob(blob_path)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from GCS: {e}")
            return False
    
    async def file_exists(self, blob_path: str) -> bool:
        """Check if file exists in GCS"""
        if not self.bucket:
            return False
        
        try:
            blob = self.bucket.blob(blob_path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Failed to check file existence: {e}")
            return False

