"""
Role-Based Access Control (RBAC) System

Provides dependencies for checking:
- SUPER_ADMIN (global scope)
- FACILITY_ADMIN, DOCTOR, STAFF (facility-scoped)
- Multi-facility support
"""
from typing import Optional, List, Tuple
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User, LoginType
from app.models.facility_user import FacilityUser, FacilityRole
from app.models.facility import Facility


class RBACScope:
    """RBAC scope types"""
    GLOBAL = "global"  # SUPER_ADMIN only
    FACILITY = "facility"  # Facility-scoped roles


async def get_user_facilities(
    user: User,
    db: AsyncSession
) -> List[FacilityUser]:
    """
    Get all active facility assignments for a user
    
    Returns list of FacilityUser objects
    """
    result = await db.execute(
        select(FacilityUser).where(
            and_(
                FacilityUser.user_id == user.id,
                FacilityUser.is_active == True
            )
        )
    )
    return result.scalars().all()


async def is_super_admin(
    user: User,
    db: AsyncSession
) -> bool:
    """
    Check if user is SUPER_ADMIN
    
    SUPER_ADMIN has facility_role=SUPER_ADMIN in facility_users table
    """
    result = await db.execute(
        select(FacilityUser).where(
            and_(
                FacilityUser.user_id == user.id,
                FacilityUser.facility_role == FacilityRole.SUPER_ADMIN,
                FacilityUser.is_active == True
            )
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def require_super_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to ensure user is SUPER_ADMIN (global scope)
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user: User = Depends(require_super_admin)):
            ...
    """
    import logging
    logger = logging.getLogger(__name__)
    
    is_super = await is_super_admin(current_user, db)
    logger.debug(
        f"require_super_admin check: user_id={current_user.id}, "
        f"mobile={current_user.mobile_number}, is_super_admin={is_super}"
    )
    
    if not is_super:
        logger.warning(
            f"Access denied to SUPER_ADMIN endpoint: user_id={current_user.id}, "
            f"mobile={current_user.mobile_number}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires SUPER_ADMIN role"
        )
    return current_user


async def require_facility_role(
    required_roles: List[FacilityRole],
    facility_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Tuple[User, FacilityUser]:
    """
    Dependency to ensure user has required facility role
    
    Args:
        required_roles: List of allowed roles (e.g., [FacilityRole.FACILITY_ADMIN, FacilityRole.DOCTOR])
        facility_id: Optional facility ID to check. If None, uses first active facility assignment.
    
    Returns: (user, facility_user)
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            user_facility: Tuple[User, FacilityUser] = Depends(
                require_facility_role([FacilityRole.FACILITY_ADMIN])
            )
        ):
            user, facility_user = user_facility
            ...
    """
    # Check if SUPER_ADMIN (has global access)
    if await is_super_admin(current_user, db):
        # SUPER_ADMIN can access any facility
        if facility_id:
            # Get the facility
            result = await db.execute(
                select(Facility).where(Facility.id == facility_id)
            )
            facility = result.scalar_one_or_none()
            if not facility:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Facility not found"
                )
            # Create a virtual FacilityUser for SUPER_ADMIN
            # This allows SUPER_ADMIN to access facility-scoped endpoints
            virtual_facility_user = FacilityUser(
                user_id=current_user.id,
                facility_id=facility_id,
                facility_role=FacilityRole.SUPER_ADMIN,
                is_active=True
            )
            virtual_facility_user.facility = facility
            return (current_user, virtual_facility_user)
        else:
            # No facility_id specified - get first active facility assignment
            # or create virtual one
            facilities = await get_user_facilities(current_user, db)
            if facilities:
                return (current_user, facilities[0])
            else:
                # SUPER_ADMIN with no facility assignments - still allow access
                virtual_facility_user = FacilityUser(
                    user_id=current_user.id,
                    facility_id=None,
                    facility_role=FacilityRole.SUPER_ADMIN,
                    is_active=True
                )
                return (current_user, virtual_facility_user)
    
    # Get facility assignments
    facilities = await get_user_facilities(current_user, db)
    
    if not facilities:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to any facility"
        )
    
    # Filter by facility_id if provided
    if facility_id:
        facilities = [f for f in facilities if f.facility_id == facility_id]
        if not facilities:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User is not assigned to facility {facility_id}"
            )
    
    # Check if user has required role in any of the facilities
    matching_facility = None
    for facility_user in facilities:
        if facility_user.facility_role in required_roles:
            matching_facility = facility_user
            break
    
    if not matching_facility:
        role_names = ", ".join([r.value for r in required_roles])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This endpoint requires one of these roles: {role_names}"
        )
    
    return (current_user, matching_facility)


async def require_facility_admin(
    facility_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Tuple[User, FacilityUser]:
    """
    Dependency to ensure user is FACILITY_ADMIN or SUPER_ADMIN
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            user_facility: Tuple[User, FacilityUser] = Depends(require_facility_admin)
        ):
            user, facility_user = user_facility
            ...
    """
    return await require_facility_role(
        [FacilityRole.FACILITY_ADMIN, FacilityRole.SUPER_ADMIN],
        facility_id=facility_id,
        current_user=current_user,
        db=db
    )


async def require_doctor_or_above(
    facility_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Tuple[User, FacilityUser]:
    """
    Dependency to ensure user is DOCTOR, FACILITY_ADMIN, or SUPER_ADMIN
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            user_facility: Tuple[User, FacilityUser] = Depends(require_doctor_or_above)
        ):
            user, facility_user = user_facility
            ...
    """
    return await require_facility_role(
        [FacilityRole.DOCTOR, FacilityRole.FACILITY_ADMIN, FacilityRole.SUPER_ADMIN],
        facility_id=facility_id,
        current_user=current_user,
        db=db
    )


async def get_facility_context(
    facility_id: Optional[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Optional[Tuple[User, FacilityUser]]:
    """
    Optional dependency to get facility context if user has access
    
    Returns: (user, facility_user) if user has access, None otherwise
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            facility_context: Optional[Tuple[User, FacilityUser]] = Depends(
                get_facility_context(facility_id=1)
            )
        ):
            if facility_context:
                user, facility_user = facility_context
                # Facility-specific logic
    """
    try:
        return await require_facility_role(
            [
                FacilityRole.STAFF,
                FacilityRole.DOCTOR,
                FacilityRole.FACILITY_ADMIN,
                FacilityRole.SUPER_ADMIN
            ],
            facility_id=facility_id,
            current_user=current_user,
            db=db
        )
    except HTTPException:
        return None


async def get_user_facility_ids(
    user: User,
    db: AsyncSession
) -> List[int]:
    """
    Get list of facility IDs user has access to
    
    Returns list of facility IDs (empty list if SUPER_ADMIN with global access)
    """
    # SUPER_ADMIN has global access - return empty list to indicate all facilities
    if await is_super_admin(user, db):
        return []
    
    facilities = await get_user_facilities(user, db)
    return [f.facility_id for f in facilities if f.facility_id is not None]

