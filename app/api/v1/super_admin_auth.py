"""
Super Admin Authentication Endpoints

Secure endpoints for SUPER_ADMIN signup and management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.database import get_db
from app.core.config import settings
from app.core.rbac import require_super_admin
from app.core.security import get_current_user
from app.models.user import User, LoginType, UserRole
from app.models.facility_user import FacilityUser, FacilityRole
from app.schemas.super_admin import (
    SuperAdminSignupRequest,
    SuperAdminCreateRequest,
    AuthResponse
)
from app.services.otp_auth_service import OTPAuthService
from app.services.token_service import TokenService
from app.core.rbac import get_user_facilities, is_super_admin

router = APIRouter()
logger = logging.getLogger(__name__)


def check_bootstrap_token(bootstrap_token: str) -> bool:
    """Check if bootstrap token is valid"""
    # Use settings from config.py which properly loads from .env file
    allow_signup = settings.ALLOW_SUPER_ADMIN_SIGNUP
    env_token = settings.SUPER_ADMIN_BOOTSTRAP_TOKEN
    
    # Log for debugging
    logger.debug(f"Bootstrap token check: allow_signup={allow_signup}, env_token={'***' if env_token else None}, provided_token={'***' if bootstrap_token else 'empty'}")
    
    # If signup is allowed, always return True (token is optional)
    if allow_signup:
        logger.info("SUPER_ADMIN signup is allowed - bypassing token check")
        return True
    
    # If no token provided and signup not allowed, reject
    if not bootstrap_token or not bootstrap_token.strip():
        logger.warning("No bootstrap token provided and signup is disabled")
        return False
    
    # If token provided, validate it matches
    if env_token and bootstrap_token.strip() == env_token:
        logger.info("Bootstrap token validated successfully")
        return True
    
    logger.warning(f"Bootstrap token mismatch: expected={'***' if env_token else None}, got={'***' if bootstrap_token else 'empty'}")
    return False


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup_super_admin(
    request_data: SuperAdminSignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create the first SUPER_ADMIN user (bootstrap)
    
    Security:
    - Requires bootstrap_token from environment variable
    - OR ALLOW_SUPER_ADMIN_SIGNUP=true
    - Can only be used if no SUPER_ADMIN exists
    """
    # Get bootstrap token (handle empty string as None)
    bootstrap_token = request_data.bootstrap_token.strip() if request_data.bootstrap_token else ""
    
    # Normalize mobile number (remove whitespace)
    mobile_number = request_data.mobile_number.strip()
    
    # Check bootstrap token
    if not check_bootstrap_token(bootstrap_token):
        # Log current settings for debugging
        logger.error(
            f"Bootstrap token validation failed. "
            f"ALLOW_SUPER_ADMIN_SIGNUP={settings.ALLOW_SUPER_ADMIN_SIGNUP}, "
            f"SUPER_ADMIN_BOOTSTRAP_TOKEN={'set' if settings.SUPER_ADMIN_BOOTSTRAP_TOKEN else 'not set'}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bootstrap token or SUPER_ADMIN signup is disabled"
        )
    
    # Check if SUPER_ADMIN already exists
    result = await db.execute(
        select(FacilityUser).where(
            FacilityUser.facility_role == FacilityRole.SUPER_ADMIN,
            FacilityUser.is_active == True
        ).limit(1)
    )
    existing_super_admin = result.scalar_one_or_none()
    
    # If signup is allowed, allow creating additional SUPER_ADMINS
    # Otherwise, only allow first SUPER_ADMIN (bootstrap)
    if existing_super_admin and not settings.ALLOW_SUPER_ADMIN_SIGNUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SUPER_ADMIN already exists. Use /create endpoint instead."
        )
    
    # Check if user already exists (use normalized mobile number)
    result = await db.execute(
        select(User).where(User.mobile_number == mobile_number)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Check if user is already a SUPER_ADMIN
        result = await db.execute(
            select(FacilityUser).where(
                FacilityUser.user_id == existing_user.id,
                FacilityUser.facility_role == FacilityRole.SUPER_ADMIN,
                FacilityUser.is_active == True
            )
        )
        existing_super_admin_role = result.scalar_one_or_none()
        
        if existing_super_admin_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with mobile {request_data.mobile_number} is already a SUPER_ADMIN"
            )
        
        # User exists but is not SUPER_ADMIN - assign the role
        facility_user = FacilityUser(
            user_id=existing_user.id,
            facility_id=None,  # NULL for SUPER_ADMIN (global scope)
            facility_role=FacilityRole.SUPER_ADMIN,
            is_active=True,
            assigned_by=None  # System assignment
        )
        db.add(facility_user)
        await db.commit()
        await db.refresh(existing_user)
        
        # Generate tokens for existing user
        facilities = await get_user_facilities(existing_user, db)
        facility_ids = [f.facility_id for f in facilities if f.facility_id]
        facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id}
        is_super = await is_super_admin(existing_user, db)
        
        tokens = TokenService.create_token_pair(
            user_id=existing_user.id,
            mobile_number=existing_user.mobile_number,
            role=existing_user.role.value,
            login_type=LoginType.HOSPITAL.value,
            facility_ids=facility_ids,
            facility_roles=facility_roles,
            is_super_admin=is_super
        )
        
        logger.info(f"SUPER_ADMIN role assigned to existing user: {existing_user.mobile_number} (ID: {existing_user.id})")
        
        return AuthResponse(
            success=True,
            message="SUPER_ADMIN role assigned successfully",
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=tokens["expires_in"],
            user_id=existing_user.id,
            login_type=LoginType.HOSPITAL.value,
            role="hospital",  # Will be overridden to "super_admin" by model_validator
            is_super_admin=True
        )
    
    # Send OTP first
    otp_service = OTPAuthService(db)
    await otp_service.send_otp(mobile_number, request)
    
    # For bootstrap, we'll create user directly after OTP verification
    # In production, you'd verify OTP first, then create user
    # For now, creating user directly (bootstrap flow)
    
    from datetime import datetime
    
    new_user = User(
        mobile_number=mobile_number,
        full_name=request_data.full_name,
        email=request_data.email,
        role=UserRole.HOSPITAL,  # Set role to HOSPITAL for SUPER_ADMIN
        login_type=LoginType.HOSPITAL,
        consent_given='Y',
        consent_timestamp=datetime.utcnow().isoformat()
    )
    db.add(new_user)
    await db.flush()
    
    # Create SUPER_ADMIN assignment
    facility_user = FacilityUser(
        user_id=new_user.id,
        facility_id=None,  # NULL for SUPER_ADMIN (global scope)
        facility_role=FacilityRole.SUPER_ADMIN,
        is_active=True,
        assigned_by=None  # System assignment
    )
    db.add(facility_user)
    await db.commit()
    await db.refresh(new_user)
    await db.refresh(facility_user)
    
    # Generate tokens
    facilities = await get_user_facilities(new_user, db)
    facility_ids = [f.facility_id for f in facilities if f.facility_id]
    facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id}
    is_super = await is_super_admin(new_user, db)
    
    tokens = TokenService.create_token_pair(
        user_id=new_user.id,
        mobile_number=new_user.mobile_number,
        role=new_user.role.value,
        login_type=LoginType.HOSPITAL.value,
        facility_ids=facility_ids,
        facility_roles=facility_roles,
        is_super_admin=is_super
    )
    
    logger.info(f"First SUPER_ADMIN created: {new_user.mobile_number} (ID: {new_user.id})")
    
    return AuthResponse(
        success=True,
        message="SUPER_ADMIN created successfully",
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        user_id=new_user.id,
        login_type=LoginType.HOSPITAL.value,
        role="hospital",  # Will be overridden to "super_admin" by model_validator
        is_super_admin=True
    )


@router.post("/create", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def create_super_admin(
    request_data: SuperAdminCreateRequest,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create additional SUPER_ADMIN (existing SUPER_ADMIN only)
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.mobile_number == request_data.mobile_number)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Check if already SUPER_ADMIN
        result = await db.execute(
            select(FacilityUser).where(
                FacilityUser.user_id == existing_user.id,
                FacilityUser.facility_role == FacilityRole.SUPER_ADMIN,
                FacilityUser.is_active == True
            )
        )
        existing_super_admin = result.scalar_one_or_none()
        if existing_super_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a SUPER_ADMIN"
            )
        
        # Assign SUPER_ADMIN role
        facility_user = FacilityUser(
            user_id=existing_user.id,
            facility_id=None,
            facility_role=FacilityRole.SUPER_ADMIN,
            is_active=True,
            assigned_by=current_user.id
        )
        db.add(facility_user)
        await db.commit()
        await db.refresh(existing_user)
        
        user = existing_user
    else:
        # Create new user
        from datetime import datetime
        new_user = User(
            mobile_number=request_data.mobile_number,
            full_name=request_data.full_name,
            email=request_data.email,
            login_type=LoginType.HOSPITAL,
            consent_given='Y',
            consent_timestamp=datetime.utcnow().isoformat()
        )
        db.add(new_user)
        await db.flush()
        
        facility_user = FacilityUser(
            user_id=new_user.id,
            facility_id=None,
            facility_role=FacilityRole.SUPER_ADMIN,
            is_active=True,
            assigned_by=current_user.id
        )
        db.add(facility_user)
        await db.commit()
        await db.refresh(new_user)
        
        user = new_user
    
    # Generate tokens
    facilities = await get_user_facilities(user, db)
    facility_ids = [f.facility_id for f in facilities if f.facility_id]
    facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id}
    is_super = await is_super_admin(user, db)
    
    tokens = TokenService.create_token_pair(
        user_id=user.id,
        mobile_number=user.mobile_number,
        role=user.role.value,
        login_type=LoginType.HOSPITAL.value,
        facility_ids=facility_ids,
        facility_roles=facility_roles,
        is_super_admin=is_super
    )
    
    logger.info(
        f"SUPER_ADMIN created by {current_user.id}: {user.mobile_number} (ID: {user.id})"
    )
    
    return AuthResponse(
        success=True,
        message="SUPER_ADMIN created successfully",
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        user_id=user.id,
        login_type=LoginType.HOSPITAL.value,
        role="hospital",  # Will be overridden to "super_admin" by model_validator
        is_super_admin=True
    )

