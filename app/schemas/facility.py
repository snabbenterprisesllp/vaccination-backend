"""
Facility schemas for request/response models
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class FacilityCreate(BaseModel):
    """Schema for creating a facility"""
    name: str = Field(..., min_length=1, max_length=255)
    facility_code: Optional[str] = Field(None, min_length=1, max_length=50, description="Optional internal code")
    facility_type: str = Field(..., description="hospital, clinic, health_center")
    address: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    pincode: str = Field(..., min_length=6, max_length=10)
    country: Optional[str] = Field(default="India", max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    registration_number: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = Field(None, max_length=500)
    services_offered: Optional[List[str]] = None
    vaccines_available: Optional[List[int]] = None
    operating_hours: Optional[Dict[str, str]] = None
    verified: Optional[bool] = False


class FacilityUpdate(BaseModel):
    """Schema for updating a facility"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    facility_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, min_length=6, max_length=10)
    country: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    registration_number: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = Field(None, max_length=500)
    services_offered: Optional[List[str]] = None
    vaccines_available: Optional[List[int]] = None
    operating_hours: Optional[Dict[str, str]] = None
    verified: Optional[bool] = None
    is_active: Optional[bool] = None


class FacilityResponse(BaseModel):
    """Schema for facility response"""
    id: int
    name: str
    facility_id: str  # Globally unique identifier
    facility_code: Optional[str] = None  # Optional internal code
    facility_type: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    registration_number: Optional[str] = None
    logo_url: Optional[str] = None
    services_offered: Optional[List[str]] = None
    vaccines_available: Optional[List[int]] = None
    operating_hours: Optional[Dict[str, str]] = None
    verified: bool
    verified_at: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FacilityListResponse(BaseModel):
    """Schema for facility list response"""
    facilities: List[FacilityResponse]
    total: int
    skip: int
    limit: int


class FacilityUserCreate(BaseModel):
    """Schema for adding a user to a facility"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    role: str = Field(..., description="facility_admin, doctor, or staff")


class FacilityUserUpdate(BaseModel):
    """Schema for updating a facility user"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, description="facility_admin, doctor, or staff")
    is_active: Optional[bool] = None


class FacilityUserResponse(BaseModel):
    """Schema for facility user response"""
    id: int
    user_id: int
    mobile_number: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    facility_id: int
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class FacilityUserListResponse(BaseModel):
    """Schema for facility user list response"""
    users: List[Dict[str, Any]]

