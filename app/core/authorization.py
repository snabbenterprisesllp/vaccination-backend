"""
Authorization utilities for role-based access control

Provides dependencies for checking:
- Login type (INDIVIDUAL vs HOSPITAL)
- Hospital roles (ADMIN, DOCTOR, STAFF)
- Hospital access
"""
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User, LoginType
from app.models.hospital_user import HospitalUser, HospitalRole


async def require_login_type(
    required_type: LoginType,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user has required login type
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user: User = Depends(require_login_type(LoginType.INDIVIDUAL))):
            ...
    """
    if current_user.login_type != required_type:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This endpoint requires {required_type.value} login type"
        )
    return current_user


async def require_hospital_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, HospitalUser]:
    """
    Dependency to ensure user is a hospital user with active assignment
    
    Returns: (user, hospital_user)
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            user_hospital: tuple[User, HospitalUser] = Depends(require_hospital_user)
        ):
            user, hospital_user = user_hospital
            ...
    """
    if current_user.login_type != LoginType.HOSPITAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires hospital login"
        )
    
    # Get active hospital assignment
    result = await db.execute(
        select(HospitalUser).where(
            and_(
                HospitalUser.user_id == current_user.id,
                HospitalUser.is_active == True
            )
        ).limit(1)
    )
    hospital_user = result.scalar_one_or_none()
    
    if not hospital_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to any hospital"
        )
    
    return (current_user, hospital_user)


async def require_hospital_role(
    required_roles: List[HospitalRole],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, HospitalUser]:
    """
    Dependency to ensure user has required hospital role
    
    Args:
        required_roles: List of allowed roles (e.g., [HospitalRole.ADMIN, HospitalRole.DOCTOR])
    
    Returns: (user, hospital_user)
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            user_hospital: tuple[User, HospitalUser] = Depends(
                require_hospital_role([HospitalRole.ADMIN])
            )
        ):
            user, hospital_user = user_hospital
            ...
    """
    # First ensure hospital user
    user, hospital_user = await require_hospital_user(current_user, db)
    
    # Check role
    if hospital_user.hospital_role not in required_roles:
        role_names = ", ".join([r.value for r in required_roles])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This endpoint requires one of these roles: {role_names}"
        )
    
    return (user, hospital_user)


async def get_hospital_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Optional[tuple[User, HospitalUser]]:
    """
    Optional dependency to get hospital context if user is hospital user
    
    Returns: (user, hospital_user) if hospital user, None otherwise
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            hospital_context: Optional[tuple[User, HospitalUser]] = Depends(get_hospital_context)
        ):
            if hospital_context:
                user, hospital_user = hospital_context
                # Hospital-specific logic
            else:
                # Individual user logic
    """
    if current_user.login_type != LoginType.HOSPITAL:
        return None
    
    result = await db.execute(
        select(HospitalUser).where(
            and_(
                HospitalUser.user_id == current_user.id,
                HospitalUser.is_active == True
            )
        ).limit(1)
    )
    hospital_user = result.scalar_one_or_none()
    
    if not hospital_user:
        return None
    
    return (current_user, hospital_user)

