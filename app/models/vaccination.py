"""Vaccination record model"""
from sqlalchemy import Column, String, Integer, ForeignKey, Date, DateTime, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class VaccinationStatus(str, enum.Enum):
    """Vaccination status"""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class Vaccination(BaseModel):
    """Vaccination record"""
    __tablename__ = "vaccinations"
    
    # Beneficiary reference (primary - ADULT or CHILD)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Legacy child reference (for backward compatibility during migration)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Vaccine information
    vaccine_id = Column(Integer, ForeignKey("vaccine_master.id"), nullable=False, index=True)
    vaccine_name = Column(String(255), nullable=False)
    dose_number = Column(Integer, default=1, nullable=False)
    
    # Vaccination details
    vaccination_date = Column(Date, nullable=False, index=True)
    vaccination_time = Column(DateTime, nullable=True)
    status = Column(SQLEnum(VaccinationStatus), default=VaccinationStatus.COMPLETED, nullable=False)
    
    # Hospital/clinic information
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True, index=True)
    administered_by = Column(String(255), nullable=True)  # Doctor/nurse name
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # User who recorded this vaccination
    
    # Vaccine vial details (from barcode/QR scan)
    batch_number = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    expiry_date = Column(Date, nullable=True)
    vial_barcode = Column(String(100), nullable=True)
    
    # Medical details
    site_of_administration = Column(String(100), nullable=True)
    route_of_administration = Column(String(100), nullable=True)
    
    # Reaction/notes
    adverse_reaction = Column(Boolean, default=False)
    reaction_details = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Verification
    verified_by_parent = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Document reference
    certificate_url = Column(String(500), nullable=True)
    
    # Vitals at time of vaccination
    temperature = Column(String(20), nullable=True)  # Store as string to preserve unit
    temperature_unit = Column(String(2), nullable=True)  # 'C' or 'F'
    weight = Column(String(20), nullable=True)  # in kilograms
    height_length = Column(String(20), nullable=True)  # in cm
    pulse_rate = Column(Integer, nullable=True)  # bpm
    oxygen_saturation = Column(String(10), nullable=True)  # SpO2 %
    
    # Relationships
    beneficiary = relationship("Beneficiary", back_populates="vaccinations")
    child = relationship("ChildProfile", back_populates="vaccinations")  # Legacy relationship
    vaccine = relationship("VaccineMaster")
    hospital = relationship("Hospital", back_populates="vaccinations")
    recorded_by = relationship("User", foreign_keys=[recorded_by_user_id])
    
    def __repr__(self):
        return f"<Vaccination {self.vaccine_name} - Dose {self.dose_number} on {self.vaccination_date}>"


class VaccinationSchedule(BaseModel):
    """Upcoming vaccination schedule"""
    __tablename__ = "vaccination_schedules"
    
    # Beneficiary reference (primary - ADULT or CHILD)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Legacy child reference (for backward compatibility during migration)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Vaccine information
    vaccine_id = Column(Integer, ForeignKey("vaccine_master.id"), nullable=False, index=True)
    vaccine_name = Column(String(255), nullable=False)
    dose_number = Column(Integer, default=1, nullable=False)
    
    # Schedule details
    due_date = Column(Date, nullable=False, index=True)
    reminder_sent = Column(Boolean, default=False)
    completed = Column(Boolean, default=False)
    
    # Hospital preference
    preferred_hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    beneficiary = relationship("Beneficiary", back_populates="schedules")
    child = relationship("ChildProfile", back_populates="schedules")  # Legacy relationship
    vaccine = relationship("VaccineMaster")
    hospital = relationship("Hospital")
    
    def __repr__(self):
        return f"<VaccinationSchedule {self.vaccine_name} - Dose {self.dose_number} due on {self.due_date}>"

