"""Child profile schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.models.child_profile import Gender, BloodGroup, GestationalAgeType, BirthVaccinationStatus


class ChildProfileBase(BaseModel):
    """Base child profile schema"""
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: Gender
    blood_group: BloodGroup = BloodGroup.UNKNOWN
    birth_weight: Optional[str] = None
    birth_height: Optional[str] = None
    head_circumference: Optional[str] = None
    place_of_birth: Optional[str] = None
    gestational_age_type: Optional[GestationalAgeType] = None
    gestational_age_weeks: Optional[int] = Field(None, ge=20, le=45)  # Typically 20-45 weeks
    # Birth vaccinations
    bcg_status: Optional[BirthVaccinationStatus] = None
    bcg_date: Optional[date] = None
    bcg_batch_number: Optional[str] = Field(None, max_length=50)
    opv0_status: Optional[BirthVaccinationStatus] = None
    opv0_date: Optional[date] = None
    opv0_batch_number: Optional[str] = Field(None, max_length=50)
    hepatitis_b_birth_status: Optional[BirthVaccinationStatus] = None
    hepatitis_b_birth_date: Optional[date] = None
    hepatitis_b_birth_batch_number: Optional[str] = Field(None, max_length=50)
    birth_vaccination_proof_document_id: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    abha_number: Optional[str] = None


class ChildProfileCreate(ChildProfileBase):
    """Schema for creating a child profile"""
    pass


class ChildProfileUpdate(BaseModel):
    """Schema for updating a child profile"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    blood_group: Optional[BloodGroup] = None
    birth_weight: Optional[str] = None
    birth_height: Optional[str] = None
    head_circumference: Optional[str] = None
    place_of_birth: Optional[str] = None
    gestational_age_type: Optional[GestationalAgeType] = None
    gestational_age_weeks: Optional[int] = Field(None, ge=20, le=45)
    # Birth vaccinations
    bcg_status: Optional[BirthVaccinationStatus] = None
    bcg_date: Optional[date] = None
    bcg_batch_number: Optional[str] = Field(None, max_length=50)
    opv0_status: Optional[BirthVaccinationStatus] = None
    opv0_date: Optional[date] = None
    opv0_batch_number: Optional[str] = Field(None, max_length=50)
    hepatitis_b_birth_status: Optional[BirthVaccinationStatus] = None
    hepatitis_b_birth_date: Optional[date] = None
    hepatitis_b_birth_batch_number: Optional[str] = Field(None, max_length=50)
    birth_vaccination_proof_document_id: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None


class ChildProfileResponse(ChildProfileBase):
    """Schema for child profile response"""
    id: int
    parent_id: int
    qr_code_url: Optional[str] = None
    qr_code_token: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class QRCodeResponse(BaseModel):
    """Schema for QR code response"""
    qr_code_url: str
    qr_code_token: str
    expires_at: datetime


# Vaccination summary schemas for QR scan (public-safe data only)
class VaccineSummary(BaseModel):
    """Summary of a single vaccination (public-safe fields only)"""
    vaccine_name: str
    dose_number: int
    vaccination_date: date
    status: str  # completed, scheduled, missed, cancelled


class VaccinationSummary(BaseModel):
    """Summary of all vaccinations for a child (public-safe)"""
    total_count: int
    last_vaccination_date: Optional[date] = None
    vaccines_received: List[VaccineSummary] = []


class ScheduleSummary(BaseModel):
    """Summary of upcoming vaccination schedule"""
    vaccine_name: str
    dose_number: int
    due_date: date
    scheduled_date: Optional[date] = None


class QRScanResponse(ChildProfileResponse):
    """Enhanced response for QR code scan with vaccination summary"""
    vaccination_summary: VaccinationSummary
    upcoming_schedules: List[ScheduleSummary] = []
