"""OTP-based authentication schemas"""
from pydantic import BaseModel, Field, field_validator
import re


class SendOTPRequest(BaseModel):
    """Request to send OTP"""
    mobile_number: str = Field(..., min_length=10, max_length=15, description="Mobile number with country code")
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        """Validate mobile number format"""
        # Remove any spaces, dashes, or parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        
        # Check if it contains only digits and optional leading +
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Invalid mobile number format. Use format: +919876543210 or 9876543210')
        
        # Ensure it starts with + for consistency
        if not cleaned.startswith('+'):
            # Assume Indian number if no country code
            cleaned = '+91' + cleaned
        
        return cleaned


class SendOTPResponse(BaseModel):
    """Response after sending OTP"""
    success: bool
    message: str
    mobile_number: str = Field(..., description="Masked mobile number")
    expires_in_seconds: int = 180  # 3 minutes


class VerifyOTPRequest(BaseModel):
    """Request to verify OTP"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')
    device_info: str | None = Field(None, max_length=500, description="Device information")
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        """Validate and normalize mobile number"""
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Invalid mobile number format')
        if not cleaned.startswith('+'):
            cleaned = '+91' + cleaned
        return cleaned


class VerifyOTPResponse(BaseModel):
    """Response after OTP verification"""
    success: bool
    message: str
    is_new_user: bool | None = None  # Optional for complete-registration response
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes
    user_id: int | None = None  # Optional, included in registration response


class CompleteRegistrationRequest(BaseModel):
    """Complete user registration after OTP verification (for new users)"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(..., pattern=r'^(parent|hospital)$')
    email: str | None = Field(None, max_length=255)
    hospital_id: str | None = Field(None, max_length=50)
    consent_given: bool = Field(True, description="GDPR/ABHA consent")
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        """Validate and normalize mobile number"""
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError('Invalid mobile number format')
        if not cleaned.startswith('+'):
            cleaned = '+91' + cleaned
        return cleaned


class TokenRefreshRequest(BaseModel):
    """Request to refresh access token"""
    refresh_token: str = Field(..., min_length=1)


class TokenRefreshResponse(BaseModel):
    """Response after token refresh"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class LogoutRequest(BaseModel):
    """Logout request"""
    session_id: str | None = None


class UserOTPResponse(BaseModel):
    """User information response"""
    id: int
    mobile_number: str
    email: str | None
    full_name: str | None
    role: str
    login_type: str | None = None  # "individual" or "hospital"
    hospital_id: str | None = None
    hospital_role: str | None = None  # "admin", "doctor", or "staff" (for hospital users)
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True

