"""Hospital endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.schemas.hospital import (
    HospitalCreate,
    HospitalUpdate,
    HospitalResponse,
    HospitalSearchRequest
)
from app.models.hospital import Hospital
from app.models.user import User, UserRole

router = APIRouter()


@router.get("", response_model=List[HospitalResponse])
async def get_hospitals(
    city: Optional[str] = None,
    state: Optional[str] = None,
    hospital_type: Optional[str] = None,
    verified_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get list of hospitals"""
    query = select(Hospital).where(Hospital.is_active == True)
    
    if city:
        query = query.where(Hospital.city.ilike(f"%{city}%"))
    
    if state:
        query = query.where(Hospital.state.ilike(f"%{state}%"))
    
    if hospital_type:
        query = query.where(Hospital.hospital_type == hospital_type)
    
    if verified_only:
        query = query.where(Hospital.verified == True)
    
    query = query.offset(skip).limit(limit).order_by(Hospital.name)
    
    result = await db.execute(query)
    hospitals = list(result.scalars().all())
    
    return hospitals


@router.get("/{hospital_id}", response_model=HospitalResponse)
async def get_hospital(
    hospital_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific hospital"""
    result = await db.execute(
        select(Hospital).where(
            and_(
                Hospital.id == hospital_id,
                Hospital.is_active == True
            )
        )
    )
    hospital = result.scalar_one_or_none()
    
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    
    return hospital


@router.post("/search", response_model=List[HospitalResponse])
async def search_hospitals(
    search_params: HospitalSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Search hospitals with advanced filters"""
    query = select(Hospital).where(Hospital.is_active == True)
    
    if search_params.city:
        query = query.where(Hospital.city.ilike(f"%{search_params.city}%"))
    
    if search_params.state:
        query = query.where(Hospital.state.ilike(f"%{search_params.state}%"))
    
    if search_params.pincode:
        query = query.where(Hospital.pincode == search_params.pincode)
    
    if search_params.hospital_type:
        query = query.where(Hospital.hospital_type == search_params.hospital_type)
    
    # TODO: Add geospatial search for nearby hospitals using lat/long and radius
    
    result = await db.execute(query.limit(50))
    hospitals = list(result.scalars().all())
    
    return hospitals


@router.post("", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED)
async def create_hospital(
    hospital_data: HospitalCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HOSPITAL])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new hospital"""
    # Check if hospital code already exists
    result = await db.execute(
        select(Hospital).where(Hospital.hospital_code == hospital_data.hospital_code)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hospital with this code already exists"
        )
    
    hospital = Hospital(**hospital_data.model_dump())
    db.add(hospital)
    await db.commit()
    await db.refresh(hospital)
    
    return hospital


@router.put("/{hospital_id}", response_model=HospitalResponse)
async def update_hospital(
    hospital_id: int,
    update_data: HospitalUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HOSPITAL])),
    db: AsyncSession = Depends(get_db)
):
    """Update a hospital"""
    result = await db.execute(
        select(Hospital).where(Hospital.id == hospital_id)
    )
    hospital = result.scalar_one_or_none()
    
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found"
        )
    
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(hospital, field, value)
    
    await db.commit()
    await db.refresh(hospital)
    
    return hospital

