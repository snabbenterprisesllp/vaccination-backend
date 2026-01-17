"""Beneficiary schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.models.beneficiary import BeneficiaryType, Gender


class BeneficiaryBase(BaseModel):
    """Base beneficiary schema"""
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: Gender
    abha_id: Optional[str] = Field(None, max_length=50)


class BeneficiaryCreate(BeneficiaryBase):
    """Schema for creating a beneficiary"""
    type: BeneficiaryType


class BeneficiaryUpdate(BaseModel):
    """Schema for updating a beneficiary"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    abha_id: Optional[str] = Field(None, max_length=50)
    abha_address: Optional[str] = Field(None, max_length=100)
    abha_linked: Optional[bool] = None


class BeneficiaryResponse(BeneficiaryBase):
    """Schema for beneficiary response"""
    id: int
    account_id: int
    type: BeneficiaryType
    abha_address: Optional[str] = None
    abha_linked: bool = False
    abha_linked_at: Optional[datetime] = None
    qr_code_url: Optional[str] = None
    qr_code_token: Optional[str] = None
    legacy_child_profile_id: Optional[int] = None  # ID of the child_profile this beneficiary is linked to
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)


class BeneficiaryWithVaccinations(BeneficiaryResponse):
    """Beneficiary with vaccination timeline"""
    vaccinations: List[dict] = Field(default_factory=list)  # Will be populated by service


class ParentProfileResponse(BaseModel):
    """Parent profile response - includes parent beneficiary and vaccinations"""
    beneficiary: BeneficiaryResponse
    vaccinations: List[dict] = Field(default_factory=list)


class QRScanResponse(BaseModel):
    """QR scan response for beneficiary"""
    beneficiary: BeneficiaryResponse
    vaccination_summary: dict = Field(default_factory=dict)
    upcoming_schedules: List[dict] = Field(default_factory=list)

