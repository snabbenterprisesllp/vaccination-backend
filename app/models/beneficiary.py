"""Beneficiary model - unified entity for ADULT (parent) and CHILD beneficiaries"""
from sqlalchemy import Column, String, Date, Integer, ForeignKey, Enum as SQLEnum, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class BeneficiaryType(str, enum.Enum):
    """Beneficiary type"""
    ADULT = "ADULT"  # Parent/Guardian
    CHILD = "CHILD"  # Child


class Gender(str, enum.Enum):
    """Gender options"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Beneficiary(BaseModel):
    """
    Beneficiary model - unified entity for both adults and children
    
    This model replaces the direct link between users and child_profiles.
    - ADULT beneficiaries represent parents/guardians
    - CHILD beneficiaries represent children
    - All vaccinations are linked to beneficiaries
    """
    __tablename__ = "beneficiaries"
    
    # Account relationship (parent account)
    account_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Beneficiary type
    type = Column(SQLEnum(BeneficiaryType), nullable=False, index=True)
    
    # Basic information
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False, index=True)
    gender = Column(SQLEnum(Gender), nullable=False)
    
    # ABHA M1 fields (for future ABHA linking)
    abha_id = Column(String(50), nullable=True, index=True)  # ABHA number reference (masked/encrypted)
    abha_address = Column(String(100), nullable=True)  # ABHA address (e.g., xxxxx@abdm)
    abha_linked = Column(Boolean, default=False, nullable=False)  # Link status
    abha_linked_at = Column(DateTime(timezone=True), nullable=True)  # When ABHA was linked
    
    # QR Code for quick access (primarily for children, but can be used for adults too)
    qr_code_url = Column(String(500), nullable=True)
    qr_code_token = Column(String(100), unique=True, index=True, nullable=True)
    
    # Legacy references (for data migration and backward compatibility)
    # These will be populated during migration and can be used for lookups
    legacy_user_id = Column(Integer, nullable=True, index=True)  # Reference to users.id if migrated from user
    legacy_child_profile_id = Column(Integer, nullable=True, index=True)  # Reference to child_profiles.id if migrated
    
    # Relationships
    account = relationship("User", foreign_keys=[account_id])
    vaccinations = relationship("Vaccination", back_populates="beneficiary", cascade="all, delete-orphan")
    schedules = relationship("VaccinationSchedule", back_populates="beneficiary", cascade="all, delete-orphan")
    
    @property
    def full_name(self):
        """Get full name"""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)
    
    def __repr__(self):
        return f"<Beneficiary {self.full_name} ({self.type.value})>"

