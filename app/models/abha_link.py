"""ABHA integration model"""
from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ABHALink(BaseModel):
    """ABHA (Ayushman Bharat Health Account) linkage"""
    __tablename__ = "abha_links"
    
    # Child reference
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # ABHA details
    abha_number = Column(String(50), nullable=False, index=True)
    abha_address = Column(String(100), nullable=True)
    
    # Consent management
    consent_given = Column(Boolean, default=False)
    consent_date = Column(DateTime, nullable=True)
    consent_expiry = Column(DateTime, nullable=True)
    
    # Token management
    access_token = Column(String(500), nullable=True)
    refresh_token = Column(String(500), nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    
    # Link status
    linked = Column(Boolean, default=False)
    linked_at = Column(DateTime, nullable=True)
    
    # Additional data
    abha_profile_data = Column(JSON, nullable=True)
    
    # Relationships
    child = relationship("ChildProfile", back_populates="abha_links")
    
    def __repr__(self):
        return f"<ABHALink {self.abha_number}>"

