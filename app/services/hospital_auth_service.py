"""
Hospital Authentication Service

Handles hospital registration and user management with role-based access.
Extends existing OTP auth service for hospital-specific flows.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import Request
import logging

from app.models.user import User, UserRole, LoginType
from app.models.hospital import Hospital
from app.models.hospital_user import HospitalUser, HospitalRole
from app.models.login_audit import LoginAudit
from app.services.otp_service import OTPService
from app.services.token_service import TokenService
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class HospitalAuthService:
    """Service for hospital authentication and user management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_hospital(
        self,
        hospital_data: Dict[str, Any],
        admin_data: Dict[str, Any],
        request: Request = None
    ) -> Dict[str, Any]:
        """
        Register new hospital and create admin user
        
        This creates:
        1. Hospital record
        2. Admin user with login_type=HOSPITAL
        3. HospitalUser mapping with role=ADMIN
        """
        # Check if hospital code already exists
        result = await self.db.execute(
            select(Hospital).where(Hospital.hospital_code == hospital_data["hospital_code"])
        )
        existing_hospital = result.scalar_one_or_none()
        if existing_hospital:
            raise ValueError(f"Hospital with code '{hospital_data['hospital_code']}' already exists")
        
        # Normalize mobile number
        admin_mobile = admin_data["mobile_number"].strip()
        
        # Check if admin mobile already exists
        result = await self.db.execute(
            select(User).where(User.mobile_number == admin_mobile)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError(f"User with mobile '{admin_mobile}' already exists")
        
        try:
            # Create hospital
            hospital = Hospital(
                name=hospital_data["hospital_name"],
                hospital_code=hospital_data["hospital_code"],
                hospital_type=hospital_data["hospital_type"],
                address=hospital_data["address"],
                city=hospital_data["city"],
                state=hospital_data["state"],
                pincode=hospital_data["pincode"],
                email=hospital_data.get("email"),
                phone=hospital_data.get("phone")
            )
            self.db.add(hospital)
            await self.db.flush()  # Get hospital ID
            
            # Create admin user
            admin_user = User(
                mobile_number=admin_mobile,
                full_name=admin_data["admin_name"],
                email=admin_data.get("admin_email"),
                role=UserRole.HOSPITAL,  # Backward compatibility
                login_type=LoginType.HOSPITAL,
                consent_given='Y',
                consent_timestamp=datetime.utcnow().isoformat()
            )
            self.db.add(admin_user)
            await self.db.flush()  # Get user ID
            
            # Create hospital-user mapping with ADMIN role
            hospital_user = HospitalUser(
                user_id=admin_user.id,
                hospital_id=hospital.id,
                hospital_role=HospitalRole.ADMIN,
                is_active=True
            )
            self.db.add(hospital_user)
            
            await self.db.commit()
            await self.db.refresh(hospital)
            await self.db.refresh(admin_user)
            await self.db.refresh(hospital_user)
            
            logger.info(
                f"Hospital registered: {hospital.name} (ID: {hospital.id}), "
                f"Admin: {self._mask_mobile(admin_data['mobile_number'])}"
            )
            
            # Get facility info (new RBAC) - admin just created, so get from facility_users
            from app.models.facility_user import FacilityUser
            from app.core.rbac import get_user_facilities, is_super_admin as check_super_admin
            
            facilities = await get_user_facilities(admin_user, self.db)
            facility_ids = [f.facility_id for f in facilities if f.facility_id is not None]
            facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id is not None}
            is_super = await check_super_admin(admin_user, self.db)
            
            # Issue tokens for admin
            tokens = TokenService.create_token_pair(
                user_id=admin_user.id,
                mobile_number=admin_user.mobile_number,
                role=admin_user.role.value,
                login_type=LoginType.HOSPITAL.value,
                hospital_id=hospital.id,  # Legacy
                hospital_role=HospitalRole.ADMIN.value,  # Legacy
                facility_ids=facility_ids,  # New RBAC
                facility_roles=facility_roles,  # New RBAC
                is_super_admin=is_super  # New RBAC
            )
            
            # Log registration
            await self._create_login_audit(
                user=admin_user,
                device_info=admin_data.get("device_info"),
                request=request
            )
            
            return {
                "success": True,
                "message": "Hospital registered successfully",
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "bearer",
                "expires_in": tokens["expires_in"],
                "user_id": admin_user.id,
                "login_type": LoginType.HOSPITAL.value,
                "hospital_id": hospital.id,
                "hospital_role": HospitalRole.ADMIN.value
            }
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error registering hospital: {str(e)}")
            raise ValueError(f"Failed to register hospital: {str(e)}")
    
    def _get_mobile_formats(self, mobile_number: str) -> list[str]:
        """
        Get all possible mobile number formats for lookup
        
        Returns list of formats to try:
        - Original (stripped)
        - With +91 prefix if not present
        - Without +91 prefix if present
        - Without 91 prefix if 12 digits
        """
        # Remove whitespace and special characters
        cleaned = mobile_number.strip().replace(" ", "").replace("-", "")
        
        formats = [cleaned]
        
        # If it starts with +91, also try without it
        if cleaned.startswith("+91"):
            without_prefix = cleaned[3:]
            if without_prefix:
                formats.append(without_prefix)
        
        # If it doesn't start with +91 and is 10 digits, also try with +91
        elif cleaned.isdigit() and len(cleaned) == 10:
            formats.append(f"+91{cleaned}")
        
        # If it starts with 91 (without +) and is 12 digits, try both formats
        elif cleaned.startswith("91") and len(cleaned) == 12:
            formats.append(cleaned[2:])  # Remove 91 prefix
            formats.append(f"+{cleaned}")  # Add + to 91
        
        # Return unique formats while preserving order
        seen = set()
        unique_formats = []
        for fmt in formats:
            if fmt not in seen:
                seen.add(fmt)
                unique_formats.append(fmt)
        
        return unique_formats
    
    async def login_hospital(
        self,
        mobile_number: str,
        otp: str,
        device_info: Optional[str] = None,
        request: Request = None
    ) -> Dict[str, Any]:
        """
        Login hospital user (uses OTP verification)
        
        Returns tokens with hospital context if user is hospital user
        """
        from app.core.redis import get_redis
        from app.services.otp_service import OTPService
        
        # Normalize mobile number and get all possible formats
        mobile_formats = self._get_mobile_formats(mobile_number)
        logger.debug(f"Trying mobile number formats: {mobile_formats}")
        
        # Verify OTP - try all possible formats
        redis = await get_redis()
        otp_service = OTPService(redis)
        
        is_valid = False
        verified_mobile = None
        
        for fmt in mobile_formats:
            try:
                is_valid = await otp_service.verify_otp(fmt, otp, invalidate_on_success=False)
                if is_valid:
                    verified_mobile = fmt
                    logger.debug(f"OTP verified with format: {fmt}")
                    break
            except Exception as e:
                logger.debug(f"OTP verification failed for format {fmt}: {e}")
                continue
        
        if not is_valid:
            raise ValueError("Invalid or expired OTP")
        
        # Get user - try all possible mobile number formats
        from sqlalchemy import or_
        conditions = [User.mobile_number == fmt for fmt in mobile_formats]
        result = await self.db.execute(
            select(User).where(or_(*conditions))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Invalidate OTP if we found the verified format
            if verified_mobile:
                await otp_service.invalidate_otp(verified_mobile)
            logger.warning(f"User not found for mobile formats: {mobile_formats}")
            raise ValueError("User not found. Please register first or check your mobile number.")
        
        # Invalidate OTP after successful user lookup
        if verified_mobile:
            await otp_service.invalidate_otp(verified_mobile)
        
        # Verify user is hospital user
        if user.login_type != LoginType.HOSPITAL:
            raise ValueError("This mobile number is not registered as a hospital user")
        
        # Check if user is SUPER_ADMIN (new RBAC)
        from app.core.rbac import is_super_admin
        is_super = await is_super_admin(user, self.db)
        
        if is_super:
            # SUPER_ADMIN doesn't need HospitalUser assignment - they have FacilityUser with SUPER_ADMIN role
            # Get facility info for token
            from app.core.rbac import get_user_facilities
            facilities = await get_user_facilities(user, self.db)
            facility_ids = [f.facility_id for f in facilities if f.facility_id is not None]
            facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id is not None}
            
            tokens = TokenService.create_token_pair(
                user_id=user.id,
                mobile_number=user.mobile_number,
                role=user.role.value,
                login_type=LoginType.HOSPITAL.value,
                hospital_id=None,  # SUPER_ADMIN doesn't have a single hospital
                hospital_role=None,  # SUPER_ADMIN role is in facility_users
                facility_ids=facility_ids,
                facility_roles=facility_roles,
                is_super_admin=True
            )
            
            await otp_service.invalidate_otp(mobile_number)
            
            return {
                "success": True,
                "message": "Login successful",
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "bearer",
                "expires_in": tokens["expires_in"],
                "user_id": user.id,
                "login_type": LoginType.HOSPITAL.value,
                "is_super_admin": True
            }
        
        # Get active hospital assignment (legacy HospitalUser or new FacilityUser)
        result = await self.db.execute(
            select(HospitalUser).where(
                and_(
                    HospitalUser.user_id == user.id,
                    HospitalUser.is_active == True
                )
            ).limit(1)
        )
        hospital_user = result.scalar_one_or_none()
        
        # Also check for FacilityUser assignment (new RBAC)
        if not hospital_user:
            from app.models.facility_user import FacilityUser, FacilityRole
            result = await self.db.execute(
                select(FacilityUser).where(
                    and_(
                        FacilityUser.user_id == user.id,
                        FacilityUser.is_active == True,
                        FacilityUser.facility_role != FacilityRole.SUPER_ADMIN  # Already handled above
                    )
                ).limit(1)
            )
            facility_user = result.scalar_one_or_none()
            
            if not facility_user:
                await otp_service.invalidate_otp(mobile_number)
            raise ValueError("User is not assigned to any hospital")
        
        # Get facility info (new RBAC)
        from app.models.facility_user import FacilityUser
        from app.core.rbac import get_user_facilities, is_super_admin as check_super_admin
        
        facilities = await get_user_facilities(user, self.db)
        facility_ids = [f.facility_id for f in facilities if f.facility_id is not None]
        facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id is not None}
        is_super = await check_super_admin(user, self.db)
        
        # Handle legacy hospital_id and hospital_role
        # If hospital_user exists, use it; otherwise derive from facility_user or set to None
        legacy_hospital_id = None
        legacy_hospital_role = None
        
        if hospital_user:
            legacy_hospital_id = hospital_user.hospital_id
            legacy_hospital_role = hospital_user.hospital_role.value
        elif facility_user:
            # For new RBAC system, use first facility's id as legacy hospital_id
            # and map facility_role to hospital_role
            if facility_ids:
                legacy_hospital_id = facility_ids[0]  # Use first facility_id
            # Map facility_role to hospital_role
            if facility_user.facility_role == FacilityRole.FACILITY_ADMIN:
                legacy_hospital_role = HospitalRole.ADMIN.value
            elif facility_user.facility_role == FacilityRole.DOCTOR:
                legacy_hospital_role = HospitalRole.DOCTOR.value
            elif facility_user.facility_role == FacilityRole.STAFF:
                legacy_hospital_role = HospitalRole.STAFF.value
            else:
                legacy_hospital_role = HospitalRole.STAFF.value  # Default fallback
        
        # Issue tokens with hospital context
        tokens = TokenService.create_token_pair(
            user_id=user.id,
            mobile_number=user.mobile_number,
            role=user.role.value,
            login_type=LoginType.HOSPITAL.value,
            hospital_id=legacy_hospital_id,  # Legacy (can be None for new RBAC)
            hospital_role=legacy_hospital_role,  # Legacy (can be None for new RBAC)
            facility_ids=facility_ids,  # New RBAC
            facility_roles=facility_roles,  # New RBAC
            is_super_admin=is_super  # New RBAC
        )
        
        # Log login
        await self._create_login_audit(
            user=user,
            device_info=device_info,
            request=request
        )
        
        # Invalidate OTP after successful login
        await otp_service.invalidate_otp(mobile_number)
        
        logger.info(f"Hospital user logged in: {self._mask_mobile(mobile_number)}")
        
        return {
            "success": True,
            "message": "Login successful",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
            "expires_in": tokens["expires_in"],
            "user_id": user.id,
            "login_type": LoginType.HOSPITAL.value,
            "hospital_id": legacy_hospital_id,
            "hospital_role": legacy_hospital_role
        }
    
    async def add_hospital_user(
        self,
        hospital_id: int,
        user_data: Dict[str, Any],
        request: Request = None
    ) -> Dict[str, Any]:
        """
        Add new hospital user (DOCTOR or STAFF) - ADMIN only
        
        This creates:
        1. User with login_type=HOSPITAL
        2. HospitalUser mapping with specified role
        """
        # Normalize mobile number
        user_mobile = user_data["mobile_number"].strip()
        
        # Check if user already exists
        result = await self.db.execute(
            select(User).where(User.mobile_number == user_mobile)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Check if already assigned to this hospital
            result = await self.db.execute(
                select(HospitalUser).where(
                    and_(
                        HospitalUser.user_id == existing_user.id,
                        HospitalUser.hospital_id == hospital_id,
                        HospitalUser.is_active == True
                    )
                )
            )
            existing_assignment = result.scalar_one_or_none()
            if existing_assignment:
                raise ValueError("User is already assigned to this hospital")
            
            # User exists but not assigned - create assignment
            if existing_user.login_type != LoginType.HOSPITAL:
                raise ValueError("User exists but is not a hospital user")
            
            hospital_user = HospitalUser(
                user_id=existing_user.id,
                hospital_id=hospital_id,
                hospital_role=HospitalRole(user_data["hospital_role"]),
                is_active=True
            )
            self.db.add(hospital_user)
            await self.db.commit()
            await self.db.refresh(hospital_user)
            
            return {
                "success": True,
                "message": "User added to hospital successfully",
                "user_id": existing_user.id,
                "hospital_id": hospital_id,
                "hospital_role": hospital_user.hospital_role.value
            }
        
        # Create new user
        try:
            new_user = User(
                mobile_number=user_mobile,
                full_name=user_data["full_name"],
                email=user_data.get("email"),
                role=UserRole.HOSPITAL,  # Backward compatibility
                login_type=LoginType.HOSPITAL,
                consent_given='Y',
                consent_timestamp=datetime.utcnow().isoformat()
            )
            self.db.add(new_user)
            await self.db.flush()
            
            # Create hospital assignment
            hospital_user = HospitalUser(
                user_id=new_user.id,
                hospital_id=hospital_id,
                hospital_role=HospitalRole(user_data["hospital_role"]),
                is_active=True
            )
            self.db.add(hospital_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            await self.db.refresh(hospital_user)
            
            logger.info(
                f"Hospital user added: {self._mask_mobile(user_data['mobile_number'])}, "
                f"Role: {user_data['hospital_role']}, Hospital: {hospital_id}"
            )
            
            return {
                "success": True,
                "message": "Hospital user created successfully",
                "user_id": new_user.id,
                "hospital_id": hospital_id,
                "hospital_role": hospital_user.hospital_role.value
            }
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding hospital user: {str(e)}")
            raise ValueError(f"Failed to add hospital user: {str(e)}")
    
    async def get_hospital_users(
        self,
        hospital_id: int
    ) -> List[Dict[str, Any]]:
        """Get all users for a hospital - checks both hospital_users and facility_users"""
        from app.models.facility import Facility
        from app.models.facility_user import FacilityUser, FacilityRole
        
        # First, try to find facility linked to this hospital
        facility_result = await self.db.execute(
            select(Facility).where(
                Facility.legacy_hospital_id == hospital_id
            ).limit(1)
        )
        facility = facility_result.scalar_one_or_none()
        
        users = []
        user_ids_seen = set()
        
        # Get users from old hospital_users table
        result = await self.db.execute(
            select(HospitalUser, User, Hospital).join(
                User, HospitalUser.user_id == User.id
            ).join(
                Hospital, HospitalUser.hospital_id == Hospital.id
            ).where(
                and_(
                    HospitalUser.hospital_id == hospital_id,
                    HospitalUser.is_active == True
                )
            )
        )
        rows = result.all()
        
        for hospital_user, user, hospital in rows:
            user_ids_seen.add(user.id)
            # Map hospital_role to facility_role for display
            role_mapping = {
                "admin": "facility_admin",
                "doctor": "doctor",
                "staff": "staff"
            }
            facility_role = role_mapping.get(hospital_user.hospital_role.value, "staff")
            
            users.append({
                "id": user.id,
                "mobile_number": user.mobile_number,
                "full_name": user.full_name,
                "email": user.email,
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "hospital_role": hospital_user.hospital_role.value,  # Keep for backward compatibility
                "role": facility_role,  # New RBAC role
                "is_active": hospital_user.is_active,
                "created_at": hospital_user.created_at.isoformat() if hospital_user.created_at else None
            })
        
        # Also get users from new facility_users table if facility exists
        if facility:
            facility_result = await self.db.execute(
                select(FacilityUser, User).join(
                    User, FacilityUser.user_id == User.id
                ).where(
                    and_(
                        FacilityUser.facility_id == facility.id,
                        FacilityUser.is_active == True
                    )
                )
            )
            facility_rows = facility_result.all()
            
            for facility_user, user in facility_rows:
                # Skip if already added from hospital_users
                if user.id not in user_ids_seen:
                    user_ids_seen.add(user.id)
                    # Map facility_role back to hospital_role for backward compatibility
                    role_mapping = {
                        "facility_admin": "admin",
                        "doctor": "doctor",
                        "staff": "staff"
                    }
                    hospital_role = role_mapping.get(facility_user.facility_role.value, "staff")
                    
                    users.append({
                        "id": user.id,
                        "mobile_number": user.mobile_number,
                        "full_name": user.full_name,
                        "email": user.email,
                        "hospital_id": hospital_id,
                        "hospital_name": facility.name,
                        "hospital_role": hospital_role,  # For backward compatibility
                        "role": facility_user.facility_role.value,  # New RBAC role
                        "is_active": facility_user.is_active,
                        "created_at": facility_user.created_at.isoformat() if facility_user.created_at else None
            })
        
        return users
    
    async def _create_login_audit(
        self,
        user: User,
        device_info: Optional[str] = None,
        request: Request = None
    ):
        """Create login audit entry"""
        ip_address = self._get_client_ip(request) if request else None
        
        login_audit = LoginAudit(
            user_id=user.id,
            mobile_number=user.mobile_number,
            ip_address=ip_address,
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
        
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return None
    
    def _mask_mobile(self, mobile_number: str) -> str:
        """Mask mobile number for logging"""
        if len(mobile_number) > 4:
            return f"****{mobile_number[-4:]}"
        return "****"

