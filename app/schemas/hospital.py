"""Hospital schemas"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime


class HospitalBase(BaseModel):
    """Base hospital schema"""
    name: str = Field(..., max_length=255)
    hospital_code: str = Field(..., max_length=50)
    hospital_type: str = Field(..., max_length=50)  # government, private
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = None
    address: str
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., max_length=10)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    registration_number: Optional[str] = None
    abha_registered: bool = False
    abha_facility_id: Optional[str] = None
    services_offered: Optional[List[str]] = None
    vaccines_available: Optional[List[int]] = None
    operating_hours: Optional[Dict[str, str]] = None


class HospitalCreate(HospitalBase):
    """Schema for creating a hospital"""
    pass


class HospitalUpdate(BaseModel):
    """Schema for updating a hospital"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    services_offered: Optional[List[str]] = None
    vaccines_available: Optional[List[int]] = None
    operating_hours: Optional[Dict[str, str]] = None


class HospitalResponse(HospitalBase):
    """Schema for hospital response"""
    id: int
    verified: bool
    verified_at: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class HospitalSearchRequest(BaseModel):
    """Schema for searching hospitals"""
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    hospital_type: Optional[str] = None
    vaccine_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = 10.0

