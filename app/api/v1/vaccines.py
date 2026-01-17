"""Vaccine master endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.schemas.vaccine_master import (
    VaccineMasterCreate,
    VaccineMasterUpdate,
    VaccineMasterResponse
)
from app.models.vaccine_master import VaccineMaster, VaccineType, VaccineCategory
from app.models.user import User, UserRole

router = APIRouter()


@router.get("", response_model=List[VaccineMasterResponse])
async def get_vaccines(
    vaccine_type: Optional[VaccineType] = None,
    category: Optional[VaccineCategory] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get list of vaccines from master data"""
    query = select(VaccineMaster).where(VaccineMaster.is_active == True)
    
    if vaccine_type:
        query = query.where(VaccineMaster.vaccine_type == vaccine_type)
    
    if category:
        query = query.where(VaccineMaster.category == category)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                VaccineMaster.vaccine_name.ilike(search_pattern),
                VaccineMaster.vaccine_code.ilike(search_pattern),
                VaccineMaster.protects_against.ilike(search_pattern)
            )
        )
    
    query = query.offset(skip).limit(limit).order_by(VaccineMaster.vaccine_name)
    
    result = await db.execute(query)
    vaccines = list(result.scalars().all())
    
    return vaccines


@router.get("/{vaccine_id}", response_model=VaccineMasterResponse)
async def get_vaccine(
    vaccine_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific vaccine"""
    result = await db.execute(
        select(VaccineMaster).where(
            and_(
                VaccineMaster.id == vaccine_id,
                VaccineMaster.is_active == True
            )
        )
    )
    vaccine = result.scalar_one_or_none()
    
    if not vaccine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaccine not found"
        )
    
    return vaccine


@router.post("", response_model=VaccineMasterResponse, status_code=status.HTTP_201_CREATED)
async def create_vaccine(
    vaccine_data: VaccineMasterCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vaccine (Admin only)"""
    # Check if vaccine code already exists
    result = await db.execute(
        select(VaccineMaster).where(VaccineMaster.vaccine_code == vaccine_data.vaccine_code)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vaccine with this code already exists"
        )
    
    vaccine = VaccineMaster(**vaccine_data.model_dump())
    db.add(vaccine)
    await db.commit()
    await db.refresh(vaccine)
    
    return vaccine


@router.put("/{vaccine_id}", response_model=VaccineMasterResponse)
async def update_vaccine(
    vaccine_id: int,
    update_data: VaccineMasterUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Update a vaccine (Admin only)"""
    result = await db.execute(
        select(VaccineMaster).where(VaccineMaster.id == vaccine_id)
    )
    vaccine = result.scalar_one_or_none()
    
    if not vaccine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaccine not found"
        )
    
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(vaccine, field, value)
    
    await db.commit()
    await db.refresh(vaccine)
    
    return vaccine

