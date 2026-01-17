"""
ABHA M1 Integration Schemas

M1 SCOPE ONLY:
- ABHA creation/linking initiation
- OTP verification
- Demographic profile fetch

EXPLICITLY EXCLUDED:
- NO M2 consent schemas (placeholder comments only)
- NO M3 health data schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, Literal
from datetime import datetime


class ABHALinkRequest(BaseModel):
    """Schema for linking ABHA"""
    child_id: int
    abha_number: str = Field(..., max_length=50)
    abha_address: Optional[str] = None
    consent_given: bool = True


class ABHAConsentRequest(BaseModel):
    """Schema for ABHA consent"""
    consent_given: bool
    consent_duration_days: int = 365


class ABHALinkResponse(BaseModel):
    """Schema for ABHA link response"""
    id: int
    child_id: int
    abha_number: str
    abha_address: Optional[str] = None
    consent_given: bool
    consent_date: Optional[datetime] = None
    consent_expiry: Optional[datetime] = None
    linked: bool
    linked_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ABHAProfileResponse(BaseModel):
    """Schema for ABHA profile response"""
    abha_number: str
    abha_address: str
    name: str
    date_of_birth: str
    gender: str
    mobile: Optional[str] = None
    email: Optional[str] = None
    profile_photo: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


# ============================================================================
# ABHA M1 SCHEMAS (M1 ONLY - NO M2/M3)
# ============================================================================

class ABHAInitiateRequest(BaseModel):
    """
    Request to initiate ABHA creation/linking (M1)
    
    person_type: "parent" or "child"
    person_id: User ID (for parent) or ChildProfile ID (for child)
    auth_method: "MOBILE_OTP" or "AADHAAR_OTP"
    mobile_number: Required for MOBILE_OTP
    aadhaar_number: Required for AADHAAR_OTP (will be hashed, never stored)
    """
    person_type: Literal["parent", "child"]
    person_id: int
    auth_method: Literal["MOBILE_OTP", "AADHAAR_OTP"]
    mobile_number: Optional[str] = None
    aadhaar_number: Optional[str] = None  # Will be hashed before sending to ABDM


class ABHAInitiateResponse(BaseModel):
    """
    Response from ABHA initiation (M1)
    """
    transaction_id: str
    message: str = "OTP sent successfully. Please verify to complete ABHA linking."


class ABHAVerifyRequest(BaseModel):
    """
    Request to verify OTP and complete ABHA linking (M1)
    """
    transaction_id: str
    otp: str = Field(..., min_length=6, max_length=6)
    auth_method: Literal["MOBILE_OTP", "AADHAAR_OTP"]
    person_type: Literal["parent", "child"]
    person_id: int


class ABHAVerifyResponse(BaseModel):
    """
    Response from ABHA verification (M1)
    Contains ABHA details and demographic profile
    """
    success: bool
    abha_linked: bool
    abha_number: str  # Masked for security
    abha_address: str
    demographic: Dict[str, Any]  # Name, DOB, gender, mobile, email only
    message: str = "ABHA linked successfully"


# ============================================================================
# PLACEHOLDER FOR FUTURE (DO NOT IMPLEMENT NOW)
# ============================================================================
# M2 Consent Manager schemas would go here (NOT IMPLEMENTED)
# M3 Health Data sync schemas would go here (NOT IMPLEMENTED)

