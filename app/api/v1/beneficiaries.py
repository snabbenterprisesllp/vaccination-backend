"""Beneficiary endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.beneficiary import (
    BeneficiaryCreate,
    BeneficiaryUpdate,
    BeneficiaryResponse,
    BeneficiaryWithVaccinations,
    ParentProfileResponse,
    QRScanResponse
)
from app.services.beneficiary_service import BeneficiaryService
from app.services.vaccination_timeline_service import VaccinationTimelineService
from app.models.user import User
from app.utils.audit_logger import AuditLogger

router = APIRouter()


@router.get("/parent/profile", response_model=ParentProfileResponse)
async def get_parent_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get parent profile with vaccinations
    
    Returns the parent's beneficiary record and their vaccination timeline.
    This endpoint is for individual users (parents) to view their own profile.
    """
    service = BeneficiaryService(db)
    
    try:
        profile = await service.get_parent_profile(current_user)
        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("", response_model=List[BeneficiaryResponse])
async def get_beneficiaries(
    type: str = None,  # Optional filter: "ADULT" or "CHILD"
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all beneficiaries for current user
    
    Returns all beneficiaries (ADULT and CHILD) under the user's account.
    Optionally filter by type.
    """
    from app.models.beneficiary import BeneficiaryType
    
    service = BeneficiaryService(db)
    
    beneficiary_type = None
    if type:
        try:
            beneficiary_type = BeneficiaryType(type.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid type. Must be 'ADULT' or 'CHILD'"
            )
    
    beneficiaries = await service.get_user_beneficiaries(current_user, beneficiary_type)
    return beneficiaries


@router.get("/children", response_model=List[BeneficiaryResponse])
async def get_children(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all child beneficiaries for current user
    
    Convenience endpoint that returns only CHILD beneficiaries.
    """
    from app.models.beneficiary import BeneficiaryType
    
    service = BeneficiaryService(db)
    children = await service.get_user_beneficiaries(current_user, BeneficiaryType.CHILD)
    return children


@router.get("/{beneficiary_id}", response_model=BeneficiaryResponse)
async def get_beneficiary(
    beneficiary_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific beneficiary"""
    service = BeneficiaryService(db)
    beneficiary = await service.get_beneficiary_by_id(beneficiary_id, current_user)
    
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiary not found"
        )
    
    return beneficiary


@router.get("/{beneficiary_id}/vaccinations", response_model=List[dict])
async def get_beneficiary_vaccinations(
    beneficiary_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vaccination timeline for a beneficiary
    
    Returns all vaccinations for the specified beneficiary.
    Parent can only view beneficiaries under their account.
    Hospital users can view any beneficiary (for QR scan workflow).
    """
    service = BeneficiaryService(db)
    
    # For hospital users, allow viewing any beneficiary (for QR scan)
    # For parents, ensure they own the beneficiary
    user = current_user if current_user.login_type.value == "INDIVIDUAL" else None
    
    vaccinations = await service.get_beneficiary_vaccinations(beneficiary_id, user)
    return vaccinations


@router.get("/{beneficiary_id}/vaccination-timeline", response_model=dict)
async def get_beneficiary_vaccination_timeline(
    beneficiary_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get age-based vaccination timeline for a child beneficiary
    
    Returns:
    - Child information (name, DOB, age)
    - Timeline with all scheduled vaccines
    - Status (COMPLETED, UPCOMING, FUTURE) with color codes
    - Reminders for upcoming vaccinations
    """
    from app.models.beneficiary import BeneficiaryType
    
    # Verify beneficiary exists and user has access
    service = BeneficiaryService(db)
    beneficiary = await service.get_beneficiary_by_id(beneficiary_id, current_user)
    
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiary not found"
        )
    
    # Get timeline (works for both ADULT and CHILD beneficiaries)
    timeline_service = VaccinationTimelineService(db)
    timeline_data = await timeline_service.get_child_timeline(beneficiary_id)
    
    return timeline_data


@router.get("/qr/{qr_token}", response_model=QRScanResponse)
async def get_beneficiary_by_qr(
    qr_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get beneficiary by QR code (public endpoint for hospital scanning)
    
    QR contains beneficiary_id only (no PHI).
    Returns:
    - Beneficiary basic information
    - Vaccination summary
    - Upcoming vaccination schedules
    """
    service = BeneficiaryService(db)
    beneficiary = await service.get_beneficiary_by_qr_token(qr_token)
    
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired QR code"
        )
    
    # Get vaccination summary
    vaccinations = await service.get_beneficiary_vaccinations(beneficiary.id)
    
    # Get upcoming schedules
    from sqlalchemy import select, and_
    from app.models.vaccination import VaccinationSchedule
    from datetime import date
    
    schedules_result = await db.execute(
        select(VaccinationSchedule).where(
            and_(
                VaccinationSchedule.beneficiary_id == beneficiary.id,
                VaccinationSchedule.is_active == True,
                VaccinationSchedule.completed == False,
                VaccinationSchedule.due_date >= date.today()
            )
        ).order_by(VaccinationSchedule.due_date)
    )
    schedules = schedules_result.scalars().all()
    
    # Build vaccination summary
    completed_vaccinations = [v for v in vaccinations if v.get('status') == 'completed']
    vaccination_summary = {
        "total_count": len(completed_vaccinations),
        "last_vaccination_date": completed_vaccinations[0].get('vaccination_date') if completed_vaccinations else None,
        "vaccines_received": vaccinations
    }
    
    # Build upcoming schedules
    upcoming_schedules = [
        {
            "vaccine_name": s.vaccine_name,
            "dose_number": s.dose_number,
            "due_date": s.due_date.isoformat() if s.due_date else None,
            "scheduled_date": s.due_date.isoformat() if s.due_date else None
        }
        for s in schedules
    ]
    
    return QRScanResponse(
        beneficiary=BeneficiaryResponse.model_validate(beneficiary),
        vaccination_summary=vaccination_summary,
        upcoming_schedules=upcoming_schedules
    )


@router.post("", response_model=BeneficiaryResponse, status_code=status.HTTP_201_CREATED)
async def create_beneficiary(
    beneficiary_data: BeneficiaryCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new beneficiary (typically a child)"""
    service = BeneficiaryService(db)
    
    try:
        beneficiary = await service.create_beneficiary(current_user, beneficiary_data)
        
        # Audit log
        await AuditLogger.log(
            db=db,
            user=current_user,
            action="CREATE",
            resource_type="beneficiary",
            resource_id=beneficiary.id,
            description=f"Created beneficiary: {beneficiary.full_name} ({beneficiary.type.value})",
            request=request
        )
        
        return beneficiary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{beneficiary_id}", response_model=BeneficiaryResponse)
async def update_beneficiary(
    beneficiary_id: int,
    update_data: BeneficiaryUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a beneficiary"""
    service = BeneficiaryService(db)
    beneficiary = await service.update_beneficiary(beneficiary_id, current_user, update_data)
    
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiary not found"
        )
    
    # Audit log
    await AuditLogger.log(
        db=db,
        user=current_user,
        action="UPDATE",
        resource_type="beneficiary",
        resource_id=beneficiary.id,
        description=f"Updated beneficiary: {beneficiary.full_name}",
        changes=update_data.model_dump(exclude_unset=True),
        request=request
    )
    
    return beneficiary

