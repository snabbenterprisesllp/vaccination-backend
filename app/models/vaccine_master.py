"""Vaccine master data model"""
from sqlalchemy import Column, String, Integer, Text, Enum as SQLEnum, Boolean, JSON
import enum

from app.models.base import BaseModel


class VaccineType(str, enum.Enum):
    """Vaccine type"""
    UNIVERSAL = "universal"  # Government universal immunization program
    PRIVATE = "private"  # Private/optional vaccines


class VaccineCategory(str, enum.Enum):
    """Vaccine category"""
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class VaccineMaster(BaseModel):
    """Master data for vaccines (India Universal Immunization + Private)"""
    __tablename__ = "vaccine_master"
    
    # Basic information
    vaccine_name = Column(String(255), nullable=False, index=True)
    vaccine_code = Column(String(50), unique=True, nullable=False, index=True)
    manufacturer = Column(String(255), nullable=True)
    
    # Classification
    vaccine_type = Column(SQLEnum(VaccineType), nullable=False)
    category = Column(SQLEnum(VaccineCategory), nullable=False)
    
    # Medical information
    description = Column(Text, nullable=True)
    protects_against = Column(Text, nullable=True)  # Diseases it protects against
    
    # Dosage information
    total_doses = Column(Integer, default=1, nullable=False)
    dosage_schedule = Column(JSON, nullable=True)  # JSON: {"dose_1": "At birth", "dose_2": "6 weeks"}
    
    # Age recommendations
    recommended_age_start = Column(String(50), nullable=True)  # e.g., "At birth", "6 weeks"
    recommended_age_end = Column(String(50), nullable=True)    # e.g., "18 years"
    
    # Administration details
    route_of_administration = Column(String(100), nullable=True)  # Oral, Injection, etc.
    site_of_administration = Column(String(100), nullable=True)   # Left arm, Right thigh, etc.
    
    # Availability
    available_in_govt = Column(Boolean, default=False)
    available_in_private = Column(Boolean, default=True)
    
    # Additional information
    side_effects = Column(Text, nullable=True)
    contraindications = Column(Text, nullable=True)
    storage_requirements = Column(Text, nullable=True)
    
    # Barcode/QR for vial scanning
    barcode_format = Column(String(50), nullable=True)
    
    def __repr__(self):
        return f"<VaccineMaster {self.vaccine_name} ({self.vaccine_code})>"

