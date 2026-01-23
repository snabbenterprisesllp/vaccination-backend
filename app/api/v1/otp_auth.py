"""OTP-based Authentication Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
from app.schemas.otp import (
    SendOTPRequest,
    SendOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    CompleteRegistrationRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    LogoutRequest,
    UserOTPResponse
)
from app.services.otp_auth_service import OTPAuthService
from app.models.user import User

router = APIRouter()


@router.post("/send-otp", response_model=SendOTPResponse, status_code=status.HTTP_200_OK)
async def send_otp(
    request_data: SendOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Send OTP to mobile number
    
    - **mobile_number**: Mobile number with country code (e.g., +919876543210)
    
    Rate limiting: Max 3 requests per minute per mobile number
    OTP validity: 3 minutes
    """
    auth_service = OTPAuthService(db)
    
    try:
        result = await auth_service.send_otp(
            mobile_number=request_data.mobile_number,
            request=request
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
            if "Too many" in str(e)
            else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again."
        )


@router.post("/verify-otp", response_model=VerifyOTPResponse, status_code=status.HTTP_200_OK)
async def verify_otp(
    request_data: VerifyOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and login/register
    
    - **mobile_number**: Mobile number used for OTP
    - **otp**: 6-digit OTP received via SMS
    - **device_info**: Optional device information
    
    Returns tokens if existing user, or indicates registration needed for new users
    """
    auth_service = OTPAuthService(db)
    
    try:
        result = await auth_service.verify_otp(
            mobile_number=request_data.mobile_number,
            otp=request_data.otp,
            device_info=request_data.device_info,
            request=request
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        logger.error(f"OTP verification error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )


@router.post("/complete-registration", response_model=VerifyOTPResponse, status_code=status.HTTP_201_CREATED)
async def complete_registration(
    request_data: CompleteRegistrationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete registration for new users after OTP verification
    
    - **mobile_number**: Verified mobile number
    - **full_name**: User's full name
    - **role**: User role (parent or hospital)
    - **email**: Optional email address
    - **hospital_id**: Required if role is hospital
    - **consent_given**: GDPR/ABHA consent (default: true)
    
    Returns access and refresh tokens
    """
    auth_service = OTPAuthService(db)
    
    try:
        result = await auth_service.complete_registration(
            mobile_number=request_data.mobile_number,
            full_name=request_data.full_name,
            role=request_data.role,
            email=request_data.email,
            hospital_id=request_data.hospital_id,
            consent_given=request_data.consent_given,
            request=request
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/refresh-token", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token
    """
    auth_service = OTPAuthService(db)
    
    try:
        result = await auth_service.refresh_token(request_data.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed."
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request_data: LogoutRequest = None,
    current_user: User = Depends(get_current_user)
):
    """
    Logout user
    
    Client should discard access and refresh tokens.
    Optional session_id can be provided for audit logging.
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.get("/me", response_model=UserOTPResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user information
    
    Requires valid access token in Authorization header
    """
    # Get hospital_role if user is a hospital user
    hospital_role = None
    hospital_id = None
    
    # Check if user is SUPER_ADMIN
    from app.core.rbac import is_super_admin, get_user_facilities
    is_super = await is_super_admin(current_user, db)
    
    # Get facility assignments (new RBAC)
    facilities = await get_user_facilities(current_user, db)
    facility_ids = [f.facility_id for f in facilities if f.facility_id is not None]
    facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id is not None}
    
    # Determine display role
    # Priority: SUPER_ADMIN > facility_role > hospital_role > user.role
    if is_super:
        display_role = "super_admin"
    elif facility_roles:
        # Use the first facility role (typically there's only one primary facility)
        # Prefer facility_admin if available
        primary_role = None
        if any(role == "facility_admin" for role in facility_roles.values()):
            primary_role = "facility_admin"
        elif any(role == "doctor" for role in facility_roles.values()):
            primary_role = "doctor"
        elif any(role == "staff" for role in facility_roles.values()):
            primary_role = "staff"
        else:
            primary_role = list(facility_roles.values())[0]
        display_role = primary_role
    else:
        display_role = current_user.role.value
    
    # Get hospital_role for backward compatibility (only if no facility_role exists)
    if not facility_roles and current_user.login_type and current_user.login_type.value == "HOSPITAL":
        from app.models.hospital_user import HospitalUser
        from sqlalchemy import select, and_
        
        result = await db.execute(
            select(HospitalUser).where(
                and_(
                    HospitalUser.user_id == current_user.id,
                    HospitalUser.is_active == True
                )
            ).limit(1)
        )
        hospital_user = result.scalar_one_or_none()
        
        if hospital_user:
            hospital_role = hospital_user.hospital_role.value
            hospital_id = str(hospital_user.hospital_id)
            # Map hospital_role to facility_role for display if no facility_role exists
            role_mapping = {
                "admin": "facility_admin",
                "doctor": "doctor",
                "staff": "staff"
            }
            if display_role == current_user.role.value:  # Only update if still using default
                display_role = role_mapping.get(hospital_role, current_user.role.value)
    
    return UserOTPResponse(
        id=current_user.id,
        mobile_number=current_user.mobile_number,
        email=current_user.email,
        full_name=current_user.full_name,
        role=display_role,  # Show "super_admin" if user is SUPER_ADMIN
        login_type=current_user.login_type.value.lower() if current_user.login_type else None,
        hospital_id=hospital_id or current_user.hospital_id,
        hospital_role=hospital_role,
        facility_ids=facility_ids if facility_ids else None,
        facility_roles=facility_roles if facility_roles else None,
        is_super_admin=is_super,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None
    )


@router.get("/health", status_code=status.HTTP_200_OK)
async def auth_health_check():
    """Health check endpoint for auth service"""
    return {
        "status": "healthy",
        "service": "otp-auth",
        "version": "1.0.0"
    }


