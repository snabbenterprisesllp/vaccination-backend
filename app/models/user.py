"""User model"""
from sqlalchemy import Column, String, Enum as SQLEnum, Integer, Boolean, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    """User roles (for backward compatibility)"""
    PARENT = "parent"
    HOSPITAL = "hospital"
    ADMIN = "admin"


class LoginType(str, enum.Enum):
    """Login type - determines authentication context"""
    INDIVIDUAL = "INDIVIDUAL"  # Parent/Guardian
    HOSPITAL = "HOSPITAL"      # Hospital/Clinic staff


class User(BaseModel):
    """User model for OTP-based authentication"""
    __tablename__ = "users"
    
    # Primary identifier - mobile number
    mobile_number = Column(String(15), unique=True, index=True, nullable=False)
    
    # Optional email (not required for auth)
    email = Column(String(255), unique=True, index=True, nullable=True)
    
    # User details
    full_name = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.PARENT, nullable=False)  # Backward compatibility
    
    # Login type - INDIVIDUAL or HOSPITAL
    login_type = Column(SQLEnum(LoginType), default=LoginType.INDIVIDUAL, nullable=False, index=True)
    
    # Optional hospital reference (for backward compatibility - legacy field)
    hospital_id = Column(String(50), nullable=True)
    
    # Device & consent tracking
    device_info = Column(String(500), nullable=True)
    consent_given = Column(String(1), default='N', nullable=False)  # Y/N for GDPR/ABHA
    consent_timestamp = Column(String(50), nullable=True)
    
    # ABHA M1 fields (minimal storage - no Aadhaar, no full ABDM responses)
    abha_number = Column(String(50), nullable=True, index=True)  # Masked/encrypted ABHA number
    abha_address = Column(String(100), nullable=True)  # ABHA address (e.g., xxxxx@abdm)
    abha_linked = Column(Boolean, default=False, nullable=False)  # Link status
    abha_linked_at = Column(DateTime(timezone=True), nullable=True)  # When ABHA was linked
    guardian_person_id = Column(Integer, nullable=True)  # For children: parent's user_id who linked
    
    # Relationships
    # Specify foreign_keys to avoid ambiguity with guardian_person_id
    children = relationship(
        "ChildProfile", 
        back_populates="parent", 
        foreign_keys="ChildProfile.parent_id",
        cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    login_audits = relationship("LoginAudit", back_populates="user", cascade="all, delete-orphan")
    # Hospital assignments (for hospital users) - legacy
    hospital_assignments = relationship("HospitalUser", back_populates="user", cascade="all, delete-orphan")
    # Facility assignments (for facility users) - new RBAC system
    facility_assignments = relationship("FacilityUser", back_populates="user", foreign_keys="FacilityUser.user_id", cascade="all, delete-orphan")
    # Beneficiaries (ADULT and CHILD)
    beneficiaries = relationship("Beneficiary", foreign_keys="Beneficiary.account_id", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.mobile_number} ({self.role})>"

