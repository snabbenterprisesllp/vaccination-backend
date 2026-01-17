"""
Authentication schemas for tab-based login system

Supports:
- Individual (Parent/Guardian) registration and login
- Hospital registration and login with role-based access
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


# ============================================================================
# INDIVIDUAL AUTHENTICATION SCHEMAS
# ============================================================================

class IndividualRegisterRequest(BaseModel):
    """Individual (Parent/Guardian) registration request"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    full_name: str = Field(..., min_length=2, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    consent_given: bool = Field(True)
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Invalid mobile number format')
        if not cleaned.startswith('+'):
            cleaned = '+91' + cleaned
        return cleaned


class IndividualLoginRequest(BaseModel):
    """Individual login request (uses existing OTP flow)"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')
    device_info: Optional[str] = Field(None, max_length=500)
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Invalid mobile number format')
        if not cleaned.startswith('+'):
            cleaned = '+91' + cleaned
        return cleaned


# ============================================================================
# HOSPITAL AUTHENTICATION SCHEMAS
# ============================================================================

class HospitalRegisterRequest(BaseModel):
    """Hospital registration request - creates hospital and admin user"""
    # Hospital information
    hospital_name: str = Field(..., min_length=2, max_length=255)
    hospital_code: str = Field(..., min_length=3, max_length=50)
    hospital_type: str = Field(..., pattern=r'^(government|private)$')
    address: str = Field(..., min_length=5)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., min_length=6, max_length=10)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    
    # Admin user information
    admin_mobile: str = Field(..., min_length=10, max_length=15)
    admin_name: str = Field(..., min_length=2, max_length=255)
    admin_email: Optional[str] = Field(None, max_length=255)
    
    @field_validator('admin_mobile')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Invalid mobile number format')
        if not cleaned.startswith('+'):
            cleaned = '+91' + cleaned
        return cleaned


class HospitalLoginRequest(BaseModel):
    """Hospital login request (uses existing OTP flow)"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')
    device_info: Optional[str] = Field(None, max_length=500)
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Invalid mobile number format')
        if not cleaned.startswith('+'):
            cleaned = '+91' + cleaned
        return cleaned


# ============================================================================
# HOSPITAL USER MANAGEMENT SCHEMAS
# ============================================================================

class AddHospitalUserRequest(BaseModel):
    """Add new hospital user (DOCTOR or STAFF) - ADMIN only"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    full_name: str = Field(..., min_length=2, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    hospital_role: str = Field(..., pattern=r'^(doctor|staff)$')  # ADMIN cannot be added via API
    device_info: Optional[str] = Field(None, max_length=500)
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Invalid mobile number format')
        if not cleaned.startswith('+'):
            cleaned = '+91' + cleaned
        return cleaned


class HospitalUserResponse(BaseModel):
    """Hospital user information response"""
    id: int
    mobile_number: str
    full_name: Optional[str]
    email: Optional[str]
    hospital_id: int
    hospital_name: str
    hospital_role: str
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


# ============================================================================
# AUTH RESPONSE SCHEMAS
# ============================================================================

class AuthResponse(BaseModel):
    """Authentication response with tokens"""
    success: bool
    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    user_id: int
    login_type: str  # "individual" or "hospital"
    hospital_id: Optional[int] = None
    hospital_role: Optional[str] = None  # "admin", "doctor", "staff"

