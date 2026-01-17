"""Audit logging utility"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from typing import Optional, Dict, Any
from datetime import date, datetime
import json

from app.models.audit_log import AuditLog
from app.models.user import User


class AuditLogger:
    """Audit logging utility"""
    
    @staticmethod
    def _serialize_for_json(obj: Any) -> Any:
        """Convert non-JSON-serializable objects to serializable format"""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: AuditLogger._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [AuditLogger._serialize_for_json(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Handle Pydantic models and other objects
            return AuditLogger._serialize_for_json(obj.__dict__)
        else:
            return obj
    
    @staticmethod
    async def log(
        db: AsyncSession,
        user: Optional[User],
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        description: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log an audit event"""
        # Serialize changes and metadata to ensure JSON compatibility
        serialized_changes = None
        if changes is not None:
            serialized_changes = AuditLogger._serialize_for_json(changes)
        
        serialized_metadata = None
        if metadata is not None:
            serialized_metadata = AuditLogger._serialize_for_json(metadata)
        
        log_entry = AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            user_role=user.role.value if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            changes=serialized_changes,
            extra_metadata=serialized_metadata
        )
        
        if request:
            log_entry.endpoint = str(request.url.path)
            log_entry.method = request.method
            log_entry.ip_address = request.client.host if request.client else None
            log_entry.user_agent = request.headers.get("user-agent")
        
        db.add(log_entry)
        await db.commit()

