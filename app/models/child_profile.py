"""Child profile model"""
from sqlalchemy import Column, String, Date, Integer, ForeignKey, Enum as SQLEnum, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class Gender(str, enum.Enum):
    """Gender options"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodGroup(str, enum.Enum):
    """Blood group options"""
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "Unknown"


class GestationalAgeType(str, enum.Enum):
    """Gestational age type options"""
    FULL_TERM = "Full term"
    PRETERM = "Preterm"
    POST_TERM = "Post-term"


class BirthVaccinationStatus(str, enum.Enum):
    """Birth vaccination status options"""
    GIVEN = "Given"
    NOT_GIVEN = "Not Given"


class ChildProfile(BaseModel):
    """Child profile model"""
    __tablename__ = "child_profiles"
    
    # Parent relationship
    parent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Basic information
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False, index=True)
    gender = Column(SQLEnum(Gender), nullable=False)
    blood_group = Column(SQLEnum(BloodGroup), default=BloodGroup.UNKNOWN, nullable=False)
    
    # Birth details
    birth_weight = Column(String(20), nullable=True)  # in kg
    birth_height = Column(String(20), nullable=True)  # in cm
    head_circumference = Column(String(20), nullable=True)  # in cm
    place_of_birth = Column(String(255), nullable=True)
    gestational_age_type = Column(SQLEnum(GestationalAgeType), nullable=True)
    gestational_age_weeks = Column(Integer, nullable=True)  # e.g., 38 weeks
    
    # Birth vaccinations
    bcg_status = Column(SQLEnum(BirthVaccinationStatus), nullable=True)
    bcg_date = Column(Date, nullable=True)
    bcg_batch_number = Column(String(50), nullable=True)
    
    opv0_status = Column(SQLEnum(BirthVaccinationStatus), nullable=True)
    opv0_date = Column(Date, nullable=True)
    opv0_batch_number = Column(String(50), nullable=True)
    
    hepatitis_b_birth_status = Column(SQLEnum(BirthVaccinationStatus), nullable=True)
    hepatitis_b_birth_date = Column(Date, nullable=True)
    hepatitis_b_birth_batch_number = Column(String(50), nullable=True)
    
    birth_vaccination_proof_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # Hospital stamp/proof
    
    # Contact information
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    
    # Medical information
    allergies = Column(Text, nullable=True)
    medical_conditions = Column(Text, nullable=True)
    
    # QR Code for quick access
    qr_code_url = Column(String(500), nullable=True)
    qr_code_token = Column(String(100), unique=True, index=True, nullable=True)
    
    # ABHA M1 fields (minimal storage - no Aadhaar, no full ABDM responses)
    abha_number = Column(String(50), nullable=True, index=True)  # Masked/encrypted ABHA number
    abha_address = Column(String(100), nullable=True)  # ABHA address (e.g., xxxxx@abdm)
    abha_linked = Column(Boolean, default=False, nullable=False)  # Link status
    abha_linked_at = Column(DateTime(timezone=True), nullable=True)  # When ABHA was linked
    guardian_person_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Parent who linked ABHA
    
    # Relationships
    # Specify foreign_keys to avoid ambiguity with guardian_person_id
    parent = relationship("User", back_populates="children", foreign_keys=[parent_id])
    vaccinations = relationship("Vaccination", back_populates="child", cascade="all, delete-orphan")
    # Specify primaryjoin to avoid ambiguity with birth_vaccination_proof_document_id
    documents = relationship("Document", back_populates="child", primaryjoin="ChildProfile.id == Document.child_id", cascade="all, delete-orphan")
    birth_vaccination_proof_document = relationship("Document", foreign_keys=[birth_vaccination_proof_document_id], post_update=True)
    schedules = relationship("VaccinationSchedule", back_populates="child", cascade="all, delete-orphan")
    abha_links = relationship("ABHALink", back_populates="child", cascade="all, delete-orphan")
    
    @property
    def full_name(self):
        """Get full name"""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)
    
    def __repr__(self):
        return f"<ChildProfile {self.full_name} (DOB: {self.date_of_birth})>"

