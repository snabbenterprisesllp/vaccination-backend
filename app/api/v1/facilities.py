"""
Facility Management APIs

Endpoints for:
- Facility CRUD operations (SUPER_ADMIN only)
- Facility user management (FACILITY_ADMIN, SUPER_ADMIN)
- Facility settings
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rbac import (
    require_super_admin,
    require_facility_admin,
    require_facility_role,
    get_user_facilities,
    is_super_admin,
    FacilityRole
)
from app.utils.validation import (
    validate_mobile_number,
    normalize_mobile_number,
    validate_email,
    normalize_email,
    mask_mobile,
    mask_email
)
from app.models.user import User
from app.models.facility import Facility
from app.models.facility_user import FacilityUser
from app.models.beneficiary import Beneficiary
from app.models.vaccination import Vaccination
from app.schemas.facility import (
    FacilityCreate,
    FacilityUpdate,
    FacilityResponse,
    FacilityListResponse,
    FacilityUserCreate,
    FacilityUserUpdate,
    FacilityUserResponse,
    FacilityUserListResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# FACILITY MANAGEMENT (SUPER_ADMIN only)
# ============================================================================

@router.post("/", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
    facility_data: FacilityCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new facility (SUPER_ADMIN only)
    """
    # Generate unique facility_id (UUID-based)
    import uuid
    facility_id = f"FAC-{uuid.uuid4().hex[:12].upper()}"
    
    # Check if facility_id already exists (shouldn't happen, but safety check)
    result = await db.execute(
        select(Facility).where(Facility.facility_id == facility_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Regenerate if collision (extremely rare)
        facility_id = f"FAC-{uuid.uuid4().hex[:12].upper()}"
    
    # Check if facility_code already exists (if provided)
    if facility_data.facility_code:
        result = await db.execute(
            select(Facility).where(Facility.facility_code == facility_data.facility_code)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Facility with code '{facility_data.facility_code}' already exists"
            )
    
    # Create facility
    facility = Facility(
        name=facility_data.name,
        facility_id=facility_id,  # Auto-generated unique ID
        facility_code=facility_data.facility_code,  # Optional internal code
        facility_type=facility_data.facility_type,
        address=facility_data.address,
        city=facility_data.city,
        state=facility_data.state,
        pincode=facility_data.pincode,
        country=facility_data.country or "India",
        email=facility_data.email,
        phone=facility_data.phone,
        website=facility_data.website,
        latitude=facility_data.latitude,
        longitude=facility_data.longitude,
        registration_number=facility_data.registration_number,
        logo_url=facility_data.logo_url,
        services_offered=facility_data.services_offered,
        vaccines_available=facility_data.vaccines_available,
        operating_hours=facility_data.operating_hours,
        verified=facility_data.verified or False
    )
    
    db.add(facility)
    await db.commit()
    await db.refresh(facility)
    
    logger.info(f"Facility created: {facility.name} (ID: {facility.id}) by SUPER_ADMIN {current_user.id}")
    
    return FacilityResponse.model_validate(facility)


@router.get("/", response_model=FacilityListResponse)
async def list_facilities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    city: Optional[str] = None,
    state: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all facilities (SUPER_ADMIN only)
    """
    query = select(Facility)
    
    # Apply filters
    if city:
        query = query.where(Facility.city.ilike(f"%{city}%"))
    if state:
        query = query.where(Facility.state.ilike(f"%{state}%"))
    if is_active is not None:
        query = query.where(Facility.is_active == is_active)
    
    # Get total count
    # Build count query from the same filters
    count_query = select(func.count(Facility.id))
    if city:
        count_query = count_query.where(Facility.city.ilike(f"%{city}%"))
    if state:
        count_query = count_query.where(Facility.state.ilike(f"%{state}%"))
    if is_active is not None:
        count_query = count_query.where(Facility.is_active == is_active)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Get facilities
    query = query.order_by(Facility.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    facilities = result.scalars().all()
    
    # Convert to response models
    facilities_list = [FacilityResponse.model_validate(f) for f in facilities]
    
    logger.info(f"Returning {len(facilities_list)} facilities (total: {total})")
    
    return FacilityListResponse(
        facilities=facilities_list,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get facility details
    
    - SUPER_ADMIN can access any facility
    - Facility users (FACILITY_ADMIN, DOCTOR, STAFF) can only access their own facility
    """
    # Check if user is SUPER_ADMIN
    is_super = await is_super_admin(current_user, db)
    
    # If not SUPER_ADMIN, check if user has access to this facility
    if not is_super:
        user_facilities = await get_user_facilities(current_user, db)
        user_facility_ids = [f.facility_id for f in user_facilities if f.facility_id is not None]
        
        if facility_id not in user_facility_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own facility details"
            )
    
    result = await db.execute(
        select(Facility).where(Facility.id == facility_id)
    )
    facility = result.scalar_one_or_none()
    
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility not found"
        )
    
    return FacilityResponse.model_validate(facility)


@router.put("/{facility_id}", response_model=FacilityResponse)
async def update_facility(
    facility_id: int,
    facility_data: FacilityUpdate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update facility (SUPER_ADMIN only)
    """
    result = await db.execute(
        select(Facility).where(Facility.id == facility_id)
    )
    facility = result.scalar_one_or_none()
    
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility not found"
        )
    
    # Update fields
    update_data = facility_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(facility, field, value)
    
    await db.commit()
    await db.refresh(facility)
    
    logger.info(f"Facility updated: {facility.name} (ID: {facility.id}) by SUPER_ADMIN {current_user.id}")
    
    return FacilityResponse.model_validate(facility)


@router.delete("/{facility_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_facility(
    facility_id: int,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable facility (soft delete - sets is_active=False) (SUPER_ADMIN only)
    """
    result = await db.execute(
        select(Facility).where(Facility.id == facility_id)
    )
    facility = result.scalar_one_or_none()
    
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility not found"
        )
    
    facility.is_active = False
    await db.commit()
    
    logger.info(f"Facility disabled: {facility.name} (ID: {facility.id}) by SUPER_ADMIN {current_user.id}")


# ============================================================================
# FACILITY USER MANAGEMENT (FACILITY_ADMIN, SUPER_ADMIN)
# ============================================================================

@router.post("/{facility_id}/users", response_model=FacilityUserResponse, status_code=status.HTTP_201_CREATED)
async def add_facility_user(
    facility_id: int,
    user_data: FacilityUserCreate,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Add user to facility (FACILITY_ADMIN for their facility, SUPER_ADMIN for any)
    """
    current_user, facility_user = user_facility
    
    # Check if user has permission for this facility
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage users for your own facility"
            )
    
    # Verify facility exists
    result = await db.execute(
        select(Facility).where(Facility.id == facility_id)
    )
    facility = result.scalar_one_or_none()
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility not found"
        )
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.mobile_number == user_data.mobile_number)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Check if already assigned to this facility
        result = await db.execute(
            select(FacilityUser).where(
                and_(
                    FacilityUser.user_id == existing_user.id,
                    FacilityUser.facility_id == facility_id,
                    FacilityUser.is_active == True
                )
            )
        )
        existing_assignment = result.scalar_one_or_none()
        if existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already assigned to this facility"
            )
        
        # Create assignment
        facility_user = FacilityUser(
            user_id=existing_user.id,
            facility_id=facility_id,
            facility_role=FacilityRole(user_data.role),
            is_active=True,
            assigned_by=current_user.id
        )
        db.add(facility_user)
        await db.commit()
        await db.refresh(facility_user)
        await db.refresh(existing_user)
        
        # Construct response with user details
        return FacilityUserResponse(
            id=facility_user.id,
            user_id=facility_user.user_id,
            mobile_number=existing_user.mobile_number,
            full_name=existing_user.full_name,
            email=existing_user.email,
            facility_id=facility_user.facility_id,
            role=facility_user.facility_role.value,
            is_active=facility_user.is_active,
            created_at=facility_user.created_at
        )
    
    # Create new user and assignment
    from app.models.user import LoginType
    from datetime import datetime
    
    new_user = User(
        mobile_number=user_data.mobile_number,
        full_name=user_data.full_name,
        email=user_data.email,
        login_type=LoginType.HOSPITAL,
        consent_given='Y',
        consent_timestamp=datetime.utcnow().isoformat()
    )
    db.add(new_user)
    await db.flush()
    
    facility_user = FacilityUser(
        user_id=new_user.id,
        facility_id=facility_id,
        facility_role=FacilityRole(user_data.role),
        is_active=True,
        assigned_by=current_user.id
    )
    db.add(facility_user)
    await db.commit()
    await db.refresh(facility_user)
    await db.refresh(new_user)
    
    logger.info(
        f"Facility user added: {user_data.mobile_number} to facility {facility_id} "
        f"with role {user_data.role} by user {current_user.id}"
    )
    
    # Construct response with user details
    return FacilityUserResponse(
        id=facility_user.id,
        user_id=facility_user.user_id,
        mobile_number=new_user.mobile_number,
        full_name=new_user.full_name,
        email=new_user.email,
        facility_id=facility_user.facility_id,
        role=facility_user.facility_role.value,
        is_active=facility_user.is_active,
        created_at=facility_user.created_at
    )


@router.get("/{facility_id}/users", response_model=FacilityUserListResponse)
async def list_facility_users(
    facility_id: int,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users for a facility (FACILITY_ADMIN for their facility, SUPER_ADMIN for any)
    """
    current_user, facility_user = user_facility
    
    # Check if user has permission for this facility
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view users for your own facility"
            )
    
    # Get facility users
    result = await db.execute(
        select(FacilityUser, User).join(
            User, FacilityUser.user_id == User.id
        ).where(
            and_(
                FacilityUser.facility_id == facility_id,
                FacilityUser.is_active == True
            )
        )
    )
    rows = result.all()
    
    users = []
    for facility_user_obj, user in rows:
        users.append({
            "id": facility_user_obj.id,  # Assignment ID
            "user_id": user.id,  # User ID
            "mobile_number": user.mobile_number,
            "full_name": user.full_name,
            "email": user.email,
            "facility_id": facility_id,
            "role": facility_user_obj.facility_role.value,
            "is_active": facility_user_obj.is_active,
            "created_at": facility_user_obj.created_at.isoformat() if facility_user_obj.created_at else None
        })
    
    return FacilityUserListResponse(users=users)


@router.put("/{facility_id}/users/{user_id}", response_model=FacilityUserResponse)
async def update_facility_user(
    facility_id: int,
    user_id: int,
    user_data: FacilityUserUpdate,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update facility user details (FACILITY_ADMIN, SUPER_ADMIN)
    """
    current_user, facility_user = user_facility
    
    # Check if user has permission for this facility
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage users for your own facility"
            )
    
    # Find assignment
    result = await db.execute(
        select(FacilityUser, User).join(
            User, FacilityUser.user_id == User.id
        ).where(
            and_(
                FacilityUser.user_id == user_id,
                FacilityUser.facility_id == facility_id
            )
        )
    )
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User assignment not found"
        )
    
    assignment, user = row
    
    # Update user details if provided
    update_data = user_data.dict(exclude_unset=True)
    
    if 'full_name' in update_data and update_data['full_name']:
        user.full_name = update_data['full_name']
    
    if 'email' in update_data:
        user.email = update_data['email']
    
    # Update facility assignment if provided
    if 'role' in update_data and update_data['role']:
        assignment.facility_role = FacilityRole(update_data['role'])
    
    if 'is_active' in update_data:
        assignment.is_active = update_data['is_active']
    
    await db.commit()
    await db.refresh(assignment)
    await db.refresh(user)
    
    logger.info(
        f"Facility user updated: user {user_id} in facility {facility_id} by user {current_user.id}"
    )
    
    # Return updated facility user response
    return FacilityUserResponse(
        id=assignment.id,
        user_id=assignment.user_id,
        mobile_number=user.mobile_number,
        full_name=user.full_name,
        email=user.email,
        facility_id=assignment.facility_id,
        role=assignment.facility_role.value,
        is_active=assignment.is_active,
        created_at=assignment.created_at
    )


@router.delete("/{facility_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_facility_user(
    facility_id: int,
    user_id: int,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove user from facility (deactivate assignment) (FACILITY_ADMIN, SUPER_ADMIN)
    """
    current_user, facility_user = user_facility
    
    # Check if user has permission for this facility
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage users for your own facility"
            )
    
    # Find assignment
    result = await db.execute(
        select(FacilityUser).where(
            and_(
                FacilityUser.user_id == user_id,
                FacilityUser.facility_id == facility_id,
                FacilityUser.is_active == True
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User assignment not found"
        )
    
    # Prevent removing yourself
    if assignment.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from facility"
        )
    
    # Deactivate assignment
    assignment.is_active = False
    await db.commit()
    
    logger.info(
        f"Facility user removed: user {user_id} from facility {facility_id} by user {current_user.id}"
    )

