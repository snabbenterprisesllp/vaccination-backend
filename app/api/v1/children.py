"""Child profile endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.schemas.child_profile import (
    ChildProfileCreate,
    ChildProfileUpdate,
    ChildProfileResponse,
    QRCodeResponse,
    QRScanResponse
)
from app.services.child_profile_service import ChildProfileService
from app.services.vaccination_timeline_service import VaccinationTimelineService
from app.models.user import User
from app.utils.audit_logger import AuditLogger

router = APIRouter()


@router.post("", response_model=ChildProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_child_profile(
    profile_data: ChildProfileCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new child profile"""
    service = ChildProfileService(db)
    
    try:
        profile = await service.create_profile(current_user, profile_data)
        
        # Audit log
        await AuditLogger.log(
            db=db,
            user=current_user,
            action="CREATE",
            resource_type="child_profile",
            resource_id=profile.id,
            description=f"Created child profile: {profile.full_name}",
            request=request
        )
        
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[ChildProfileResponse])
async def get_my_children(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all child profiles for current user"""
    service = ChildProfileService(db)
    profiles = await service.get_user_profiles(current_user)
    return profiles


@router.get("/{child_id}", response_model=ChildProfileResponse)
async def get_child_profile(
    child_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific child profile"""
    service = ChildProfileService(db)
    profile = await service.get_profile_by_id(child_id, current_user)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    return profile


@router.put("/{child_id}", response_model=ChildProfileResponse)
async def update_child_profile(
    child_id: int,
    update_data: ChildProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a child profile"""
    service = ChildProfileService(db)
    profile = await service.update_profile(child_id, current_user, update_data)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    # Audit log
    await AuditLogger.log(
        db=db,
        user=current_user,
        action="UPDATE",
        resource_type="child_profile",
        resource_id=profile.id,
        description=f"Updated child profile: {profile.full_name}",
        changes=update_data.model_dump(exclude_unset=True),
        request=request
    )
    
    return profile


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child_profile(
    child_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a child profile"""
    service = ChildProfileService(db)
    success = await service.delete_profile(child_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    # Audit log
    await AuditLogger.log(
        db=db,
        user=current_user,
        action="DELETE",
        resource_type="child_profile",
        resource_id=child_id,
        description=f"Deleted child profile ID: {child_id}",
        request=request
    )
    
    return None


@router.post("/{child_id}/qr-code/regenerate", response_model=QRCodeResponse)
async def regenerate_qr_code(
    child_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate QR code for child profile"""
    service = ChildProfileService(db)
    profile = await service.regenerate_qr_code(child_id, current_user)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    from datetime import datetime, timedelta
    from app.core.config import settings
    
    return QRCodeResponse(
        qr_code_url=profile.qr_code_url,
        qr_code_token=profile.qr_code_token,
        expires_at=datetime.now() + timedelta(hours=settings.QR_CODE_EXPIRY_HOURS)
    )


@router.get("/{child_id}/qr-code/image")
async def get_qr_code_image(
    child_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get QR code image (generates base64 if URL not stored)"""
    from fastapi.responses import Response
    from app.services.qr_service import QRCodeService
    
    service = ChildProfileService(db)
    profile = await service.get_profile_by_id(child_id, current_user)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    # If URL exists and is a real URL, redirect to it
    if profile.qr_code_url and not profile.qr_code_url.startswith('data:'):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=profile.qr_code_url)
    
    # Otherwise, generate base64 QR code on-the-fly
    if profile.qr_code_token:
        qr_service = QRCodeService()
        qr_data = f"{settings.API_VERSION}/children/qr/{profile.qr_code_token}"
        base64_qr = qr_service.generate_qr_base64(qr_data)
        
        # Return as image
        import base64
        image_data = base64.b64decode(base64_qr.split(',')[1])
        return Response(content=image_data, media_type="image/png")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="QR code not available"
    )


@router.get("/qr/{qr_token}", response_model=QRScanResponse)
async def get_profile_by_qr(
    qr_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get child profile with vaccination summary by QR code (public endpoint for hospital scanning)
    
    Returns:
    - Child profile basic information
    - Vaccination summary (public-safe data only)
    - Upcoming vaccination schedules
    """
    service = ChildProfileService(db)
    profile = await service.get_profile_by_qr_token(qr_token)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired QR code"
        )
    
    # Get vaccination summary (public-safe data only)
    vaccination_summary = await service.get_vaccination_summary(profile.id)
    
    # Get upcoming schedules
    upcoming_schedules = await service.get_upcoming_schedules(profile.id)
    
    # Build enhanced response using model_dump for child profile
    profile_dict = {
        "id": profile.id,
        "parent_id": profile.parent_id,
        "first_name": profile.first_name,
        "middle_name": profile.middle_name,
        "last_name": profile.last_name,
        "date_of_birth": profile.date_of_birth,
        "gender": profile.gender,
        "blood_group": profile.blood_group,
        "birth_weight": profile.birth_weight,
        "birth_height": profile.birth_height,
        "place_of_birth": profile.place_of_birth,
        "address": profile.address,
        "city": profile.city,
        "state": profile.state,
        "pincode": profile.pincode,
        "allergies": profile.allergies,
        "medical_conditions": profile.medical_conditions,
        "abha_number": profile.abha_number,
        "qr_code_url": profile.qr_code_url,
        "qr_code_token": profile.qr_code_token,
        "is_active": profile.is_active,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "vaccination_summary": vaccination_summary,
        "upcoming_schedules": upcoming_schedules
    }
    
    return QRScanResponse(**profile_dict)


@router.get("/{child_id}/vaccination-timeline", response_model=dict)
async def get_child_vaccination_timeline(
    child_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get age-based vaccination timeline for a child (legacy endpoint)
    
    This endpoint uses child_id for backward compatibility.
    It finds the corresponding beneficiary and returns the timeline.
    """
    # Get child profile
    child_service = ChildProfileService(db)
    child_profile = await child_service.get_profile_by_id(child_id, current_user)
    
    if not child_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child profile not found"
        )
    
    # Find corresponding beneficiary
    from app.models.beneficiary import Beneficiary
    from sqlalchemy import select, and_
    
    result = await db.execute(
        select(Beneficiary).where(
            and_(
                Beneficiary.legacy_child_profile_id == child_id,
                Beneficiary.is_active == True
            )
        )
    )
    beneficiary = result.scalar_one_or_none()
    
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiary not found for this child"
        )
    
    # Get timeline using beneficiary
    timeline_service = VaccinationTimelineService(db)
    timeline_data = await timeline_service.get_child_timeline(beneficiary.id)
    
    return timeline_data

