"""
Tab-based Authentication Endpoints

Supports:
- Individual (Parent/Guardian) registration and login
- Hospital login (hospital users must be created by SUPER_ADMIN)

EXTENDS existing OTP auth - does not replace it.
Hospital registration is disabled - hospitals and hospital users must be created by SUPER_ADMIN through facility management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.authorization import require_hospital_role, require_hospital_user
from app.schemas.auth import (
    IndividualRegisterRequest,
    IndividualLoginRequest,
    HospitalRegisterRequest,
    HospitalLoginRequest,
    AddHospitalUserRequest,
    HospitalUserResponse,
    AuthResponse
)
from app.schemas.otp import SendOTPRequest, SendOTPResponse
from app.services.otp_auth_service import OTPAuthService
from app.services.hospital_auth_service import HospitalAuthService
from app.models.user import User, LoginType
from app.models.hospital_user import HospitalRole, HospitalUser

router = APIRouter()
logger = logging.getLogger(__name__)


async def require_admin_role(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, HospitalUser]:
    """Dependency to ensure user is hospital ADMIN"""
    # First ensure hospital user
    user, hospital_user = await require_hospital_user(current_user, db)
    
    # Check if admin
    if hospital_user.hospital_role != HospitalRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires ADMIN role"
        )
    
    return (user, hospital_user)


# ============================================================================
# INDIVIDUAL AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/register/individual", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_individual(
    request_data: IndividualRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register individual (Parent/Guardian) user
    
    This endpoint:
    - Uses existing OTP flow (send-otp, verify-otp, complete-registration)
    - Sets login_type=INDIVIDUAL
    - Returns tokens with individual context
    """
    auth_service = OTPAuthService(db)
    
    try:
        # Use existing complete_registration with login_type=INDIVIDUAL
        result = await auth_service.complete_registration(
            mobile_number=request_data.mobile_number,
            full_name=request_data.full_name,
            role="parent",  # Individual users are parents
            email=request_data.email,
            hospital_id=None,
            consent_given=request_data.consent_given,
            request=request
        )
        
        # Get user to extract login_type
        user = await auth_service._get_user_by_mobile(request_data.mobile_number)
        
        return AuthResponse(
            success=True,
            message="Registration successful",
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="bearer",
            expires_in=result["expires_in"],
            user_id=user.id,
            login_type=user.login_type.value,
            hospital_id=None,
            hospital_role=None
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Individual registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login/individual", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login_individual(
    request_data: IndividualLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login individual (Parent/Guardian) user
    
    Uses existing OTP verification flow.
    Ensures user has login_type=INDIVIDUAL.
    """
    auth_service = OTPAuthService(db)
    
    try:
        # Verify OTP using existing flow
        result = await auth_service.verify_otp(
            mobile_number=request_data.mobile_number,
            otp=request_data.otp,
            device_info=request_data.device_info,
            request=request
        )
        
        if result.get("is_new_user"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not registered. Please complete registration first."
            )
        
        # Get user to verify login_type
        user = await auth_service._get_user_by_mobile(request_data.mobile_number)
        
        if user.login_type != LoginType.INDIVIDUAL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This mobile number is registered as a hospital user. Please use hospital login."
            )
        
        return AuthResponse(
            success=True,
            message="Login successful",
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="bearer",
            expires_in=result["expires_in"],
            user_id=user.id,
            login_type=LoginType.INDIVIDUAL.value,
            hospital_id=None,
            hospital_role=None
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Individual login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


# ============================================================================
# HOSPITAL AUTHENTICATION ENDPOINTS
# ============================================================================

# Hospital registration removed - hospitals and users must be created by SUPER_ADMIN
# Use /facilities endpoint to create facilities and /facilities/{id}/users to add users


@router.post("/login/hospital", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login_hospital(
    request_data: HospitalLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login hospital user
    
    Uses OTP verification.
    Ensures user has login_type=HOSPITAL and active hospital assignment.
    Returns tokens with hospital context.
    """
    hospital_service = HospitalAuthService(db)
    
    try:
        result = await hospital_service.login_hospital(
            mobile_number=request_data.mobile_number,
            otp=request_data.otp,
            device_info=request_data.device_info,
            request=request
        )
        
        return AuthResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Hospital login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


# ============================================================================
# HOSPITAL USER MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/hospital/users", response_model=HospitalUserResponse, status_code=status.HTTP_201_CREATED)
async def add_hospital_user(
    request_data: AddHospitalUserRequest,
    request: Request,
    user_hospital: tuple[User, HospitalUser] = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Add new hospital user (DOCTOR or STAFF) - ADMIN only
    
    This endpoint:
    - Creates user with login_type=HOSPITAL
    - Creates HospitalUser mapping with specified role
    - Only accessible by hospital ADMIN
    """
    user, hospital_user = user_hospital
    
    hospital_service = HospitalAuthService(db)
    
    try:
        user_data = {
            "mobile_number": request_data.mobile_number,
            "full_name": request_data.full_name,
            "email": request_data.email,
            "hospital_role": request_data.hospital_role,
            "device_info": request_data.device_info
        }
        
        result = await hospital_service.add_hospital_user(
            hospital_id=hospital_user.hospital_id,
            user_data=user_data,
            request=request
        )
        
        # Get created user for response
        from sqlalchemy import select
        from app.models.hospital import Hospital
        result_user = await db.execute(
            select(User).where(User.id == result["user_id"])
        )
        created_user = result_user.scalar_one_or_none()
        
        result_hospital = await db.execute(
            select(Hospital).where(Hospital.id == hospital_user.hospital_id)
        )
        hospital = result_hospital.scalar_one_or_none()
        
        return HospitalUserResponse(
            id=created_user.id,
            mobile_number=created_user.mobile_number,
            full_name=created_user.full_name,
            email=created_user.email,
            hospital_id=hospital.id,
            hospital_name=hospital.name,
            hospital_role=result["hospital_role"],
            is_active=True,
            created_at=created_user.created_at.isoformat() if created_user.created_at else ""
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add hospital user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add hospital user: {str(e)}"
        )


@router.get("/hospital/users", response_model=list[HospitalUserResponse], status_code=status.HTTP_200_OK)
async def get_hospital_users(
    user_hospital: tuple[User, HospitalUser] = Depends(require_hospital_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users for a hospital
    
    Accessible by all hospital users (ADMIN, DOCTOR, STAFF)
    """
    user, hospital_user = user_hospital
    
    hospital_service = HospitalAuthService(db)
    
    try:
        users = await hospital_service.get_hospital_users(hospital_user.hospital_id)
        return [HospitalUserResponse(**u) for u in users]
    except Exception as e:
        logger.error(f"Failed to get hospital users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hospital users: {str(e)}"
        )


# ============================================================================
# OTP ENDPOINTS (Reuse existing - work for both Individual and Hospital)
# ============================================================================

@router.post("/send-otp", response_model=SendOTPResponse, status_code=status.HTTP_200_OK)
async def send_otp(
    request_data: SendOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Send OTP to mobile number (works for both Individual and Hospital)
    
    This endpoint is shared - the login_type is determined during registration/login
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

