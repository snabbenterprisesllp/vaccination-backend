"""
Super Admin schemas
"""
from pydantic import BaseModel, EmailStr, Field, model_validator


class SuperAdminSignupRequest(BaseModel):
    """Schema for SUPER_ADMIN signup (bootstrap)"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(None)
    bootstrap_token: str = Field(..., description="Bootstrap token from environment")


class SuperAdminCreateRequest(BaseModel):
    """Schema for creating additional SUPER_ADMIN"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(None)


class AuthResponse(BaseModel):
    """Schema for authentication response"""
    success: bool
    message: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_id: int
    login_type: str
    role: str = "hospital"  # Display role - will be "super_admin" if is_super_admin is True
    is_super_admin: bool = False
    
    @model_validator(mode='after')
    def set_role(self):
        """Set role to 'super_admin' if is_super_admin is True"""
        if self.is_super_admin:
            self.role = 'super_admin'
        return self

