"""Hospital model"""
from sqlalchemy import Column, String, Text, Boolean, Float, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Hospital(BaseModel):
    """Hospital/clinic model"""
    __tablename__ = "hospitals"
    
    # Basic information
    name = Column(String(255), nullable=False, index=True)
    hospital_code = Column(String(50), unique=True, nullable=False, index=True)
    hospital_type = Column(String(50), nullable=False)  # government, private
    
    # Contact information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Address
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    pincode = Column(String(10), nullable=False, index=True)
    
    # Location coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Registration details
    registration_number = Column(String(100), nullable=True)
    abha_registered = Column(Boolean, default=False)
    abha_facility_id = Column(String(100), nullable=True, index=True)
    
    # Services
    services_offered = Column(JSON, nullable=True)  # List of services
    vaccines_available = Column(JSON, nullable=True)  # List of vaccine IDs
    
    # Operating hours
    operating_hours = Column(JSON, nullable=True)  # {"monday": "9:00-18:00", ...}
    
    # Verification
    verified = Column(Boolean, default=False)
    verified_at = Column(String(50), nullable=True)
    
    # Relationships
    vaccinations = relationship("Vaccination", back_populates="hospital")
    hospital_users = relationship("HospitalUser", back_populates="hospital")
    
    def __repr__(self):
        return f"<Hospital {self.name} ({self.city})>"

