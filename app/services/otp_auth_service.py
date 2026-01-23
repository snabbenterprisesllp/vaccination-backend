"""OTP-based Authentication Service"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Request
import logging

from app.models.user import User, UserRole, LoginType
from app.models.login_audit import LoginAudit
from app.services.otp_service import OTPService
from app.services.token_service import TokenService
from app.core.redis import get_redis
from app.utils.validation import (
    validate_mobile_number,
    normalize_mobile_number,
    validate_email,
    normalize_email,
    mask_mobile,
    mask_email
)

logger = logging.getLogger(__name__)


class OTPAuthService:
    """Service for OTP-based authentication"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_otp(self, mobile_number: str, request: Request = None) -> Dict[str, Any]:
        """Send OTP to mobile number"""
        # Validate and normalize mobile number
        is_valid, normalized_mobile, error_msg = validate_mobile_number(mobile_number, default_country='IN')
        if not is_valid:
            logger.warning(f"Invalid mobile number attempt: {self._mask_mobile(mobile_number)} - {error_msg}")
            raise ValueError(error_msg or "Invalid mobile number")
        
        mobile_number = normalized_mobile
        
        redis = await get_redis()
        otp_service = OTPService(redis)
        
        # Check rate limit
        can_proceed = await otp_service.check_rate_limit(mobile_number)
        if not can_proceed:
            raise ValueError("Too many OTP requests. Please try again later.")
        
        # Generate OTP
        otp = await otp_service.generate_otp(mobile_number)
        
        # Store OTP in Redis
        await otp_service.store_otp(mobile_number, otp)
        
        # Increment rate limit counter
        await otp_service.increment_rate_limit(mobile_number)
        
        # Send OTP via SMS
        sent = await otp_service.send_otp(mobile_number, otp)
        
        if not sent:
            raise ValueError("Failed to send OTP. Please try again.")
        
        # Get client IP for logging
        ip_address = self._get_client_ip(request) if request else None
        logger.info(f"OTP sent to {self._mask_mobile(mobile_number)} from IP: {ip_address}")
        
        return {
            "success": True,
            "message": "OTP sent successfully",
            "mobile_number": self._mask_mobile(mobile_number),
            "expires_in_seconds": OTPService.OTP_EXPIRY_MINUTES * 60
        }
    
    async def verify_otp(
        self,
        mobile_number: str,
        otp: str,
        device_info: Optional[str] = None,
        request: Request = None
    ) -> Dict[str, Any]:
        """Verify OTP and login/register user"""
        # Validate and normalize mobile number
        is_valid, normalized_mobile, error_msg = validate_mobile_number(mobile_number, default_country='IN')
        if not is_valid:
            logger.warning(f"Invalid mobile number in OTP verification: {self._mask_mobile(mobile_number)} - {error_msg}")
            raise ValueError(error_msg or "Invalid mobile number")
        
        mobile_number = normalized_mobile
        
        redis = await get_redis()
        otp_service = OTPService(redis)
        
        # Verify OTP but don't invalidate yet - wait until full flow completes
        # This prevents OTP from being deleted if there's an error after verification
        is_valid = await otp_service.verify_otp(mobile_number, otp, invalidate_on_success=False)
        
        if not is_valid:
            logger.warning(f"Invalid OTP attempt for {self._mask_mobile(mobile_number)}")
            raise ValueError("Invalid or expired OTP")
        
        try:
            # Check if user exists
            user = await self._get_user_by_mobile(mobile_number)
            is_new_user = user is None
            
            if is_new_user:
                # For new users, invalidate OTP now since we're returning success
                await otp_service.invalidate_otp(mobile_number)
                # Return success but indicate registration needed
                return {
                    "success": True,
                    "message": "OTP verified. Please complete registration.",
                    "is_new_user": True,
                    "mobile_number": mobile_number
                }
            
            # Get hospital info if hospital user (legacy)
            hospital_id = None
            hospital_role = None
            if user.login_type == LoginType.HOSPITAL:
                from app.models.hospital_user import HospitalUser
                from sqlalchemy import select
                result = await self.db.execute(
                    select(HospitalUser).where(
                        HospitalUser.user_id == user.id,
                        HospitalUser.is_active == True
                    ).limit(1)
                )
                hospital_user = result.scalar_one_or_none()
                if hospital_user:
                    hospital_id = hospital_user.hospital_id
                    hospital_role = hospital_user.hospital_role.value
            
            # Get facility info (new RBAC)
            facility_ids = []
            facility_roles = {}
            is_super_admin = False
            if user.login_type == LoginType.HOSPITAL:
                from app.models.facility_user import FacilityUser, FacilityRole
                from app.core.rbac import get_user_facilities, is_super_admin as check_super_admin
                
                facilities = await get_user_facilities(user, self.db)
                facility_ids = [f.facility_id for f in facilities if f.facility_id is not None]
                facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id is not None}
                is_super_admin = await check_super_admin(user, self.db)
            
            # Existing user - issue tokens with login context
            tokens = TokenService.create_token_pair(
                user_id=user.id,
                mobile_number=user.mobile_number,
                role=user.role.value,
                login_type=user.login_type.value,
                hospital_id=hospital_id,  # Legacy
                hospital_role=hospital_role,  # Legacy
                facility_ids=facility_ids,  # New RBAC
                facility_roles=facility_roles,  # New RBAC
                is_super_admin=is_super_admin  # New RBAC
            )
            
            # Log the login
            await self._create_login_audit(
                user=user,
                device_info=device_info,
                request=request
            )
            
            # Only invalidate OTP after everything succeeds
            await otp_service.invalidate_otp(mobile_number)
            
            logger.info(f"User logged in: {self._mask_mobile(mobile_number)}")
            
            return {
                "success": True,
                "message": "Login successful",
                "is_new_user": False,
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "bearer",
                "expires_in": tokens["expires_in"]
            }
        except Exception as e:
            # If there's an error after OTP verification, don't invalidate the OTP
            # so user can try again
            logger.error(f"Error after OTP verification: {str(e)}")
            raise
    
    async def complete_registration(
        self,
        mobile_number: str,
        full_name: str,
        role: str,
        email: Optional[str] = None,
        hospital_id: Optional[str] = None,
        consent_given: bool = True,
        device_info: Optional[str] = None,
        request: Request = None
    ) -> Dict[str, Any]:
        """Complete user registration after OTP verification"""
        
        # Validate and normalize mobile number
        is_valid, normalized_mobile, error_msg = validate_mobile_number(mobile_number, default_country='IN')
        if not is_valid:
            logger.warning(f"Invalid mobile number in registration: {self._mask_mobile(mobile_number)} - {error_msg}")
            raise ValueError(error_msg or "Invalid mobile number")
        
        mobile_number = normalized_mobile
        
        # Check if user already exists by mobile (case-insensitive)
        existing_user = await self._get_user_by_mobile(mobile_number)
        if existing_user:
            logger.warning(f"Registration attempt with existing mobile: {self._mask_mobile(mobile_number)}")
            raise ValueError("User already registered. Please login.")
        
        # Validate and normalize email if provided
        normalized_email = None
        if email:
            email = email.strip()
            if email:  # Only validate if not empty
                is_email_valid, email_error = validate_email(email, check_disposable=True)
                if not is_email_valid:
                    logger.warning(f"Invalid email in registration: {mask_email(email)} - {email_error}")
                    raise ValueError(email_error or "Invalid email format")
                
                normalized_email = normalize_email(email)
                
                # Check if email already exists (case-insensitive)
                from sqlalchemy import select, func
                result = await self.db.execute(
                    select(User).where(func.lower(User.email) == normalized_email)
                )
                email_user = result.scalar_one_or_none()
                if email_user:
                    logger.warning(f"Registration attempt with existing email: {mask_email(normalized_email)}")
                    raise ValueError("Email already registered")
        
        # Create new user
        # Convert role to uppercase to match enum
        role_upper = role.upper() if role else 'PARENT'
        logger.info(f"Registration - Role received: {role}, converted to: {role_upper}")
        try:
            user_role = UserRole(role_upper)
            logger.info(f"Registration - UserRole enum created: {user_role}, value: {user_role.value}")
        except ValueError:
            # Default to PARENT if invalid role
            logger.warning(f"Registration - Invalid role '{role_upper}', defaulting to PARENT")
            user_role = UserRole.PARENT
        
        # Hospital users cannot be created via this endpoint
        # They must be created by SUPER_ADMIN through facility management
        if role_upper == 'HOSPITAL':
            raise ValueError("Hospital users cannot be registered through this endpoint. They must be created by a SUPER_ADMIN through facility management.")
        
        # Only INDIVIDUAL (parent) users can register through this endpoint
        login_type = LoginType.INDIVIDUAL
        
        user = User(
            mobile_number=mobile_number,
            full_name=full_name,
            role=user_role,
            login_type=login_type,  # Set login type
            email=normalized_email,  # Use normalized email
            hospital_id=hospital_id,
            device_info=device_info,
            consent_given='Y' if consent_given else 'N',
            consent_timestamp=datetime.utcnow().isoformat() if consent_given else None
        )
        
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise ValueError(f"Failed to create user: {str(e)}")
        
        # Get hospital info if hospital user
        hospital_id = None
        hospital_role = None
        if login_type == LoginType.HOSPITAL:
            from app.models.hospital_user import HospitalUser
            from sqlalchemy import select
            result = await self.db.execute(
                select(HospitalUser).where(
                    HospitalUser.user_id == user.id,
                    HospitalUser.is_active == True
                ).limit(1)
            )
            hospital_user = result.scalar_one_or_none()
            if hospital_user:
                hospital_id = hospital_user.hospital_id
                hospital_role = hospital_user.hospital_role.value
        
        # Issue tokens with login context
        tokens = TokenService.create_token_pair(
            user_id=user.id,
            mobile_number=user.mobile_number,
            role=user.role.value,
            login_type=login_type.value,
            hospital_id=hospital_id,
            hospital_role=hospital_role
        )
        
        # Log the registration/login
        await self._create_login_audit(
            user=user,
            device_info=device_info,
            request=request
        )
        
        logger.info(f"New user registered: {self._mask_mobile(mobile_number)} as {role}")
        
        return {
            "success": True,
            "message": "Registration successful",
            "is_new_user": False,  # Not a new user anymore, registration complete
            "user_id": user.id,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
            "expires_in": tokens["expires_in"]
        }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        new_access_token = TokenService.refresh_access_token(refresh_token)
        
        if not new_access_token:
            raise ValueError("Invalid or expired refresh token")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": TokenService.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    async def _get_user_by_mobile(self, mobile_number: str) -> Optional[User]:
        """Get user by mobile number"""
        # Normalize mobile number for lookup
        mobile_number = mobile_number.strip()
        result = await self.db.execute(
            select(User).where(User.mobile_number == mobile_number)
        )
        return result.scalar_one_or_none()
    
    async def _create_login_audit(
        self,
        user: User,
        device_info: Optional[str] = None,
        request: Request = None
    ):
        """Create login audit entry"""
        login_audit = LoginAudit(
            user_id=user.id,
            mobile_number=user.mobile_number,
            ip_address=self._get_client_ip(request) if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            device_info=device_info,
            login_method="otp"
        )
        
        self.db.add(login_audit)
        await self.db.commit()
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request"""
        if not request:
            return None
        
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return None
    
    def _mask_mobile(self, mobile_number: str) -> str:
        """Mask mobile number for logging"""
        if len(mobile_number) > 4:
            return f"****{mobile_number[-4:]}"
        return "****"

