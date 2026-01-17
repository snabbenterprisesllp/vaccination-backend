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
        
        # Check if admin mobile already exists
        result = await self.db.execute(
            select(User).where(User.mobile_number == admin_data["mobile_number"])
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError(f"User with mobile '{admin_data['mobile_number']}' already exists")
        
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
                mobile_number=admin_data["mobile_number"],
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
            
            # Issue tokens for admin
            tokens = TokenService.create_token_pair(
                user_id=admin_user.id,
                mobile_number=admin_user.mobile_number,
                role=admin_user.role.value,
                login_type=LoginType.HOSPITAL.value,
                hospital_id=hospital.id,
                hospital_role=HospitalRole.ADMIN.value
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
        
        # Verify OTP using OTP service
        redis = await get_redis()
        otp_service = OTPService(redis)
        
        is_valid = await otp_service.verify_otp(mobile_number, otp, invalidate_on_success=False)
        if not is_valid:
            raise ValueError("Invalid or expired OTP")
        
        # Get user
        result = await self.db.execute(
            select(User).where(User.mobile_number == mobile_number)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await otp_service.invalidate_otp(mobile_number)
            raise ValueError("User not found")
        
        # Verify user is hospital user
        if user.login_type != LoginType.HOSPITAL:
            await otp_service.invalidate_otp(mobile_number)
            raise ValueError("This mobile number is not registered as a hospital user")
        
        # Get active hospital assignment
        result = await self.db.execute(
            select(HospitalUser).where(
                and_(
                    HospitalUser.user_id == user.id,
                    HospitalUser.is_active == True
                )
            ).limit(1)
        )
        hospital_user = result.scalar_one_or_none()
        
        if not hospital_user:
            await otp_service.invalidate_otp(mobile_number)
            raise ValueError("User is not assigned to any hospital")
        
        # Issue tokens with hospital context
        tokens = TokenService.create_token_pair(
            user_id=user.id,
            mobile_number=user.mobile_number,
            role=user.role.value,
            login_type=LoginType.HOSPITAL.value,
            hospital_id=hospital_user.hospital_id,
            hospital_role=hospital_user.hospital_role.value
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
            "hospital_id": hospital_user.hospital_id,
            "hospital_role": hospital_user.hospital_role.value
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
        # Check if user already exists
        result = await self.db.execute(
            select(User).where(User.mobile_number == user_data["mobile_number"])
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
                mobile_number=user_data["mobile_number"],
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
        """Get all users for a hospital"""
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
        
        users = []
        for hospital_user, user, hospital in rows:
            users.append({
                "id": user.id,
                "mobile_number": user.mobile_number,
                "full_name": user.full_name,
                "email": user.email,
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "hospital_role": hospital_user.hospital_role.value,
                "is_active": hospital_user.is_active,
                "created_at": hospital_user.created_at.isoformat() if hospital_user.created_at else None
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

