"""Vaccine master schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.vaccine_master import VaccineType, VaccineCategory


class VaccineMasterBase(BaseModel):
    """Base vaccine master schema"""
    vaccine_name: str = Field(..., max_length=255)
    vaccine_code: str = Field(..., max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=255)
    vaccine_type: VaccineType
    category: VaccineCategory
    description: Optional[str] = None
    protects_against: Optional[str] = None
    total_doses: int = Field(1, ge=1)
    dosage_schedule: Optional[Dict[str, Any]] = None
    recommended_age_start: Optional[str] = None
    recommended_age_end: Optional[str] = None
    route_of_administration: Optional[str] = None
    site_of_administration: Optional[str] = None
    available_in_govt: bool = False
    available_in_private: bool = True
    side_effects: Optional[str] = None
    contraindications: Optional[str] = None
    storage_requirements: Optional[str] = None


class VaccineMasterCreate(VaccineMasterBase):
    """Schema for creating a vaccine master entry"""
    pass


class VaccineMasterUpdate(BaseModel):
    """Schema for updating a vaccine master entry"""
    vaccine_name: Optional[str] = None
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    available_in_govt: Optional[bool] = None
    available_in_private: Optional[bool] = None
    side_effects: Optional[str] = None


class VaccineMasterResponse(VaccineMasterBase):
    """Schema for vaccine master response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


from datetime import datetime

