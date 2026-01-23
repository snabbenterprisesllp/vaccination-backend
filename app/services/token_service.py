"""Token Service for JWT operations"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenService:
    """Service for JWT token operations"""
    
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=TokenService.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=TokenService.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_token_pair(
        user_id: int, 
        mobile_number: str, 
        role: str,
        login_type: str = "individual",
        hospital_id: Optional[int] = None,
        hospital_role: Optional[str] = None,
        facility_ids: Optional[List[int]] = None,
        facility_roles: Optional[Dict[int, str]] = None,
        is_super_admin: bool = False
    ) -> Dict[str, str]:
        """
        Create both access and refresh tokens
        
        Args:
            user_id: User ID
            mobile_number: Mobile number
            role: User role (for backward compatibility)
            login_type: "individual" or "hospital"
            hospital_id: Hospital ID (for hospital users - legacy)
            hospital_role: "admin", "doctor", or "staff" (for hospital users - legacy)
            facility_ids: List of facility IDs user has access to (new RBAC)
            facility_roles: Dict mapping facility_id to role (new RBAC)
            is_super_admin: Whether user is SUPER_ADMIN (global scope)
        """
        token_data = {
            "user_id": user_id,
            "mobile_number": mobile_number,
            "role": role,  # Backward compatibility
            "login_type": login_type,
            "hospital_id": hospital_id,  # Legacy
            "hospital_role": hospital_role,  # Legacy
            "facility_ids": facility_ids or [],  # New RBAC
            "facility_roles": facility_roles or {},  # New RBAC: {facility_id: role}
            "is_super_admin": is_super_admin  # New RBAC
        }
        
        access_token = TokenService.create_access_token(token_data)
        refresh_token = TokenService.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": TokenService.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
        }
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch. Expected: {token_type}, Got: {payload.get('type')}")
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                logger.warning("Token has expired")
                return None
            
            return payload
        
        except JWTError as e:
            logger.error(f"JWT verification error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return None
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[str]:
        """Generate new access token from refresh token"""
        payload = TokenService.verify_token(refresh_token, token_type="refresh")
        
        if not payload:
            return None
        
        # Create new access token with same user data (preserve all token fields)
        new_access_token = TokenService.create_access_token({
            "user_id": payload.get("user_id"),
            "mobile_number": payload.get("mobile_number"),
            "role": payload.get("role"),  # Backward compatibility
            "login_type": payload.get("login_type", "individual"),
            "hospital_id": payload.get("hospital_id"),  # Legacy
            "hospital_role": payload.get("hospital_role"),  # Legacy
            "facility_ids": payload.get("facility_ids", []),  # New RBAC
            "facility_roles": payload.get("facility_roles", {}),  # New RBAC
            "is_super_admin": payload.get("is_super_admin", False)  # New RBAC
        })
        
        return new_access_token


