"""Document endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import uuid
import mimetypes

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUploadResponse,
    DocumentDownloadResponse
)
from app.models.document import Document, DocumentType
from app.models.user import User
from app.utils.gcs_client import GCSClient
from app.utils.local_storage import LocalStorage
from app.core.config import settings
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    child_id: int = Form(...),
    document_type: DocumentType = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    vaccination_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document"""
    # Validate file size
    file_data = await file.read()
    file_size = len(file_data)
    
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit"
        )
    
    # Validate file extension
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Upload to storage (GCS or local fallback)
    gcs_client = GCSClient()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    storage_path = f"documents/child-{child_id}/{unique_filename}"
    
    # Try GCS first, fallback to local storage
    file_url = None
    storage_bucket = None
    use_local_storage = False
    
    if gcs_client.bucket:
        try:
            file_url = await gcs_client.upload_file(
                file_data=file_data,
                destination_path=storage_path,
                content_type=file.content_type
            )
            storage_bucket = settings.GCS_BUCKET_NAME
            logger.info(f"File uploaded to GCS: {storage_path}")
        except Exception as e:
            logger.warning(f"GCS upload failed, falling back to local storage: {e}")
            use_local_storage = True
    else:
        use_local_storage = True
    
    # Fallback to local storage if GCS is not available
    if use_local_storage:
        try:
            local_storage = LocalStorage()
            file_url = await local_storage.save_file(
                file_data=file_data,
                file_path=storage_path,
                content_type=file.content_type
            )
            storage_bucket = "local"
            logger.info(f"File saved to local storage: {storage_path}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
    
    # Create document record
    document = Document(
        child_id=child_id,
        document_type=document_type,
        title=title,
        description=description,
        vaccination_id=vaccination_id,
        file_name=file.filename,
        file_extension=file_extension,
        file_size=file_size,
        mime_type=file.content_type,
        gcs_bucket=storage_bucket or "local",
        gcs_path=storage_path,
        gcs_url=file_url,
        uploaded_by_id=current_user.id
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    return DocumentUploadResponse(
        document_id=document.id,
        file_name=document.file_name,
        file_size=document.file_size,
        upload_url=file_url,
        message="Document uploaded successfully"
    )


@router.get("/child/{child_id}", response_model=List[DocumentResponse])
async def get_child_documents(
    child_id: int,
    document_type: Optional[DocumentType] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all documents for a child"""
    query = select(Document).where(
        and_(
            Document.child_id == child_id,
            Document.is_active == True
        )
    )
    
    if document_type:
        query = query.where(Document.document_type == document_type)
    
    query = query.order_by(Document.created_at.desc())
    
    result = await db.execute(query)
    documents = list(result.scalars().all())
    
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document"""
    result = await db.execute(
        select(Document).where(
            and_(
                Document.id == document_id,
                Document.is_active == True
            )
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.get("/{document_id}/download", response_model=DocumentDownloadResponse)
async def get_document_download_url(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get signed URL for document download"""
    result = await db.execute(
        select(Document).where(
            and_(
                Document.id == document_id,
                Document.is_active == True
            )
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Generate download URL (GCS or local)
    if document.gcs_bucket == "local":
        # Local storage - return API endpoint URL (without /api/v1 prefix, client adds it)
        download_url = f"/documents/files/{document.gcs_path}"
    else:
        # GCS - generate signed URL
        gcs_client = GCSClient()
        try:
            download_url = await gcs_client.generate_signed_url(
                document.gcs_path,
                expiration_minutes=60
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate download URL: {str(e)}"
            )
    
    return DocumentDownloadResponse(
        download_url=download_url,
        expires_in=3600
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Soft delete
    document.is_active = False
    await db.commit()
    
    # Optionally delete from GCS
    # gcs_client = GCSClient()
    # Delete file from storage
    if document.gcs_bucket == "local":
        local_storage = LocalStorage()
        local_storage.delete_file(document.gcs_path)
    # else:
    #     gcs_client = GCSClient()
    #     await gcs_client.delete_file(document.gcs_path)
    
    return None


@router.get("/files/{file_path:path}")
async def serve_file(file_path: str, current_user: User = Depends(get_current_user)):
    """Serve file from local storage"""
    local_storage = LocalStorage()
    file_path_obj = local_storage.get_file_path(file_path)
    
    if not file_path_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Determine media type from file extension
    media_type, _ = mimetypes.guess_type(str(file_path_obj))
    if not media_type:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=str(file_path_obj),
        media_type=media_type,
        filename=file_path_obj.name
    )

