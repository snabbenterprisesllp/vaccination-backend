"""OTP-based authentication schemas"""
from pydantic import BaseModel, Field, field_validator
from app.utils.validation import validate_mobile_number, validate_email, normalize_email


class SendOTPRequest(BaseModel):
    """Request to send OTP"""
    mobile_number: str = Field(..., min_length=10, max_length=15, description="Mobile number with country code")
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        """Validate mobile number format using validation utility"""
        is_valid, normalized, error_msg = validate_mobile_number(v, default_country='IN')
        if not is_valid:
            raise ValueError(error_msg or 'Invalid mobile number format')
        return normalized


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
        """Validate and normalize mobile number using validation utility"""
        is_valid, normalized, error_msg = validate_mobile_number(v, default_country='IN')
        if not is_valid:
            raise ValueError(error_msg or 'Invalid mobile number format')
        return normalized
    
    @field_validator('email')
    @classmethod
    def validate_email_field(cls, v: str | None) -> str | None:
        """Validate email if provided"""
        if v is None or not v.strip():
            return None
        
        is_valid, error_msg = validate_email(v.strip(), check_disposable=True)
        if not is_valid:
            raise ValueError(error_msg or 'Invalid email format')
        
        return normalize_email(v)


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
    facility_ids: list[int] | None = None  # List of facility IDs user has access to
    facility_roles: dict[int, str] | None = None  # Mapping facility_id to role
    is_super_admin: bool = False  # Global admin flag
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True

