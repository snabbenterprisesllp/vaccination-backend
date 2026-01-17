"""Vaccination schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime
from app.models.vaccination import VaccinationStatus


class VaccinationBase(BaseModel):
    """Base vaccination schema"""
    vaccine_id: int
    vaccine_name: str = Field(..., max_length=255)
    dose_number: int = Field(1, ge=1)
    vaccination_date: date
    status: VaccinationStatus = VaccinationStatus.COMPLETED
    hospital_id: Optional[int] = None
    administered_by: Optional[str] = Field(None, max_length=255)
    batch_number: Optional[str] = Field(None, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=255)
    expiry_date: Optional[date] = None
    vial_barcode: Optional[str] = Field(None, max_length=100)
    site_of_administration: Optional[str] = None
    route_of_administration: Optional[str] = None
    adverse_reaction: bool = False
    reaction_details: Optional[str] = None
    notes: Optional[str] = None
    # Vitals at time of vaccination
    temperature: Optional[str] = Field(None, max_length=20)
    temperature_unit: Optional[str] = Field(None, max_length=2)  # 'C' or 'F'
    weight: Optional[str] = Field(None, max_length=20)
    height_length: Optional[str] = Field(None, max_length=20)
    pulse_rate: Optional[int] = Field(None, ge=0, le=300)
    oxygen_saturation: Optional[str] = Field(None, max_length=10)


class VaccinationCreate(VaccinationBase):
    """Schema for creating a vaccination record"""
    beneficiary_id: Optional[int] = None  # Primary - for ADULT or CHILD beneficiaries
    child_id: Optional[int] = None  # Legacy - for backward compatibility
    
    def model_post_init(self, __context):
        """Validate that either beneficiary_id or child_id is provided"""
        if not self.beneficiary_id and not self.child_id:
            raise ValueError("Either beneficiary_id or child_id must be provided")


class VaccinationUpdate(BaseModel):
    """Schema for updating a vaccination record"""
    vaccination_date: Optional[date] = None
    status: Optional[VaccinationStatus] = None
    administered_by: Optional[str] = None
    batch_number: Optional[str] = None
    adverse_reaction: Optional[bool] = None
    reaction_details: Optional[str] = None
    notes: Optional[str] = None
    # Vitals at time of vaccination
    temperature: Optional[str] = Field(None, max_length=20)
    temperature_unit: Optional[str] = Field(None, max_length=2)  # 'C' or 'F'
    weight: Optional[str] = Field(None, max_length=20)
    height_length: Optional[str] = Field(None, max_length=20)
    pulse_rate: Optional[int] = Field(None, ge=0, le=300)
    oxygen_saturation: Optional[str] = Field(None, max_length=10)


class VaccinationResponse(VaccinationBase):
    """Schema for vaccination response"""
    id: int
    beneficiary_id: Optional[int] = None
    child_id: Optional[int] = None  # Legacy
    vaccination_time: Optional[datetime] = None
    verified_by_parent: bool
    verified_at: Optional[datetime] = None
    certificate_url: Optional[str] = None
    recorded_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class VaccinationScheduleBase(BaseModel):
    """Base vaccination schedule schema"""
    vaccine_id: int
    vaccine_name: str = Field(..., max_length=255)
    dose_number: int = Field(1, ge=1)
    due_date: date
    preferred_hospital_id: Optional[int] = None
    notes: Optional[str] = None


class VaccinationScheduleCreate(VaccinationScheduleBase):
    """Schema for creating a vaccination schedule"""
    beneficiary_id: Optional[int] = None  # Primary - for ADULT or CHILD beneficiaries
    child_id: Optional[int] = None  # Legacy - for backward compatibility
    
    def model_post_init(self, __context):
        """Validate that either beneficiary_id or child_id is provided"""
        if not self.beneficiary_id and not self.child_id:
            raise ValueError("Either beneficiary_id or child_id must be provided")


class VaccinationScheduleUpdate(BaseModel):
    """Schema for updating a vaccination schedule"""
    due_date: Optional[date] = None
    preferred_hospital_id: Optional[int] = None
    notes: Optional[str] = None
    completed: Optional[bool] = None


class VaccinationScheduleResponse(VaccinationScheduleBase):
    """Schema for vaccination schedule response"""
    id: int
    beneficiary_id: Optional[int] = None
    child_id: Optional[int] = None  # Legacy
    reminder_sent: bool
    completed: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class VialScanRequest(BaseModel):
    """Schema for scanning vaccine vial barcode"""
    barcode: str = Field(..., max_length=100)


class VialScanResponse(BaseModel):
    """Schema for vial scan response"""
    vaccine_name: str
    manufacturer: str
    batch_number: str
    expiry_date: Optional[date] = None
    vaccine_id: Optional[int] = None

