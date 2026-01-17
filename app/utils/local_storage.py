"""Local file storage utility (fallback when GCS is not available)"""
import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base directory for local file storage
STORAGE_DIR = Path("uploads")
STORAGE_DIR.mkdir(exist_ok=True)


class LocalStorage:
    """Local file storage for development"""
    
    def __init__(self):
        self.base_dir = STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_file(
        self,
        file_data: bytes,
        file_path: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Save file to local storage and return relative URL"""
        try:
            # Create full path
            full_path = self.base_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(full_path, 'wb') as f:
                f.write(file_data)
            
            # Return URL path (will be served via API endpoint)
            return f"/api/v1/documents/files/{file_path}"
        except Exception as e:
            logger.error(f"Failed to save file locally: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
    
    def get_file_path(self, file_path: str) -> Optional[Path]:
        """Get full file path if exists"""
        full_path = self.base_dir / file_path
        if full_path.exists():
            return full_path
        return None
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from local storage"""
        try:
            full_path = self.base_dir / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False


