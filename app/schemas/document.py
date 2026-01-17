"""Document schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.document import DocumentType


class DocumentBase(BaseModel):
    """Base document schema"""
    document_type: DocumentType
    title: str = Field(..., max_length=255)
    description: Optional[str] = None


class DocumentCreate(DocumentBase):
    """Schema for creating a document"""
    child_id: int
    vaccination_id: Optional[int] = None


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response"""
    document_id: int
    file_name: str
    file_size: int
    upload_url: Optional[str] = None
    message: str


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: int
    child_id: int
    vaccination_id: Optional[int] = None
    file_name: str
    file_extension: str
    file_size: int
    mime_type: str
    gcs_url: Optional[str] = None
    uploaded_by_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DocumentDownloadResponse(BaseModel):
    """Schema for document download response"""
    download_url: str
    expires_in: int  # seconds

