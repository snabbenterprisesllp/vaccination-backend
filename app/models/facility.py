"""
Facility model - extends Hospital model for multi-facility support

Facilities represent hospitals/clinics in the system.
This model extends the existing Hospital model to support the new RBAC system.
"""
from sqlalchemy import Column, String, Text, Boolean, Float, JSON, Integer
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Facility(BaseModel):
    """
    Facility model - represents hospitals/clinics
    
    This extends the Hospital model concept to support:
    - Multi-facility management
    - Facility-scoped RBAC
    - Facility analytics
    """
    __tablename__ = "facilities"
    
    # Basic information
    name = Column(String(255), nullable=False, index=True)
    facility_id = Column(String(50), unique=True, nullable=False, index=True)  # Globally unique identifier (UUID-based)
    facility_code = Column(String(50), nullable=True, index=True)  # Optional internal code
    facility_type = Column(String(50), nullable=False)  # hospital, clinic, health_center
    
    # Contact information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Address
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    pincode = Column(String(10), nullable=False, index=True)
    country = Column(String(100), default="India", nullable=False)
    
    # Location coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Registration details
    registration_number = Column(String(100), nullable=True, index=True)
    abha_registered = Column(Boolean, default=False)
    abha_facility_id = Column(String(100), nullable=True, index=True)
    
    # Facility logo/photo URL
    logo_url = Column(String(500), nullable=True)
    
    # Services
    services_offered = Column(JSON, nullable=True)  # List of services
    vaccines_available = Column(JSON, nullable=True)  # List of vaccine IDs
    
    # Operating hours
    operating_hours = Column(JSON, nullable=True)  # {"monday": "9:00-18:00", ...}
    
    # Verification and status
    verified = Column(Boolean, default=False)
    verified_at = Column(String(50), nullable=True)
    verified_by = Column(Integer, nullable=True)  # User ID who verified
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)  # Can be disabled by SUPER_ADMIN
    
    # Legacy hospital_id reference (for backward compatibility)
    legacy_hospital_id = Column(Integer, nullable=True, index=True)
    
    # Relationships
    facility_users = relationship("FacilityUser", back_populates="facility", cascade="all, delete-orphan")
    vaccinations = relationship(
        "Vaccination", 
        back_populates="facility", 
        foreign_keys="Vaccination.facility_id",
        lazy="select"  # Lazy load to avoid validation errors before migration
    )
    
    def __repr__(self):
        return f"<Facility {self.name} ({self.city})>"

