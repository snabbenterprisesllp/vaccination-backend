"""Document model"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class DocumentType(str, enum.Enum):
    """Document types"""
    BIRTH_CERTIFICATE = "birth_certificate"
    DISCHARGE_SUMMARY = "discharge_summary"
    VACCINATION_CARD = "vaccination_card"
    VACCINE_PROOF = "vaccine_proof"
    PRESCRIPTION = "prescription"
    MEDICAL_REPORT = "medical_report"
    ABHA_CARD = "abha_card"
    OTHER = "other"


class Document(BaseModel):
    """Document storage model"""
    __tablename__ = "documents"
    
    # Child reference
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Document information
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # File information
    file_name = Column(String(255), nullable=False)
    file_extension = Column(String(10), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # in bytes
    mime_type = Column(String(100), nullable=False)
    
    # Storage information (Google Cloud Storage)
    gcs_bucket = Column(String(255), nullable=False)
    gcs_path = Column(String(500), nullable=False)
    gcs_url = Column(String(1000), nullable=True)  # Signed URL
    
    # Metadata
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vaccination_id = Column(Integer, ForeignKey("vaccinations.id"), nullable=True)  # Optional link to vaccination
    
    # Relationships
    # Specify primaryjoin to avoid ambiguity with birth_vaccination_proof_document_id
    child = relationship("ChildProfile", back_populates="documents", primaryjoin="Document.child_id == ChildProfile.id")
    uploaded_by = relationship("User")
    vaccination = relationship("Vaccination")
    
    def __repr__(self):
        return f"<Document {self.title} ({self.document_type})>"

