"""Vaccination endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.vaccination import (
    VaccinationCreate,
    VaccinationUpdate,
    VaccinationResponse,
    VaccinationScheduleCreate,
    VaccinationScheduleUpdate,
    VaccinationScheduleResponse,
    VialScanRequest,
    VialScanResponse
)
from app.services.vaccination_service import VaccinationService
from app.models.user import User
from app.utils.audit_logger import AuditLogger

router = APIRouter()


@router.post("", response_model=VaccinationResponse, status_code=status.HTTP_201_CREATED)
async def create_vaccination(
    vaccination_data: VaccinationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new vaccination record
    
    Requires either beneficiary_id (preferred) or child_id (legacy).
    For hospital users, recorded_by_user_id is automatically set to current_user.id.
    """
    service = VaccinationService(db)
    
    try:
        # For hospital users, record who created this vaccination
        recorded_by_user_id = current_user.id if current_user.login_type.value == "HOSPITAL" else None
        
        vaccination = await service.create_vaccination(
            vaccination_data,
            recorded_by_user_id=recorded_by_user_id
        )
        
        # Audit log
        await AuditLogger.log(
            db=db,
            user=current_user,
            action="CREATE",
            resource_type="vaccination",
            resource_id=vaccination.id,
            description=f"Created vaccination record: {vaccination.vaccine_name}",
            request=request
        )
        
        return vaccination
    except ValueError as e:
        # Handle validation errors (e.g., beneficiary/child/hospital not found)
        error_msg = str(e)
        if "hospital" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg
        )
    except Exception as e:
        # Handle database integrity errors and other errors
        error_str = str(e)
        if "foreign key constraint" in error_str.lower() or "violates foreign key" in error_str.lower():
            if "hospital_id" in error_str.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid hospital ID. The specified hospital does not exist."
                )
            elif "beneficiary_id" in error_str.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid beneficiary ID. The specified beneficiary does not exist."
                )
            elif "child_id" in error_str.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid child ID. The specified child profile does not exist."
                )
            elif "vaccine_id" in error_str.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid vaccine ID. The specified vaccine does not exist."
                )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create vaccination record: {error_str}"
        )


@router.get("", response_model=List[VaccinationResponse])
async def get_all_vaccinations(
    hospital_id: Optional[int] = Query(None, description="Filter by hospital ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all vaccinations (for hospital staff/admin)"""
    from app.models.child_profile import ChildProfile
    from sqlalchemy.orm import selectinload
    
    service = VaccinationService(db)
    
    # If user is hospital staff, filter by their hospital_id
    # Ensure hospital_id is an integer (it might be stored as string in some cases)
    user_hospital_id = None
    if hasattr(current_user, 'hospital_id') and current_user.hospital_id is not None:
        try:
            # Convert to int if it's a string or other type
            user_hospital_id = int(current_user.hospital_id) if current_user.hospital_id else None
        except (ValueError, TypeError):
            # If conversion fails, log and ignore
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid hospital_id for user {current_user.id}: {current_user.hospital_id}")
            user_hospital_id = None
    
    # Use query parameter if provided, otherwise use user's hospital_id
    filter_hospital_id = hospital_id if hospital_id is not None else user_hospital_id
    
    vaccinations = await service.get_all_vaccinations(hospital_id=filter_hospital_id)
    
    # Load child profiles for each vaccination to include child info
    from sqlalchemy import select
    child_ids = [v.child_id for v in vaccinations if v.child_id is not None]
    if child_ids:
        result = await db.execute(
            select(ChildProfile).where(ChildProfile.id.in_(child_ids))
        )
        children = {child.id: child for child in result.scalars().all()}
        
        # Attach child info to each vaccination (we'll return it in the response)
        # Note: The response model doesn't include child info, so we'll need to extend it
        # For now, return vaccinations as-is (child_id is already included)
    
    return vaccinations


@router.get("/child/{child_id}", response_model=List[VaccinationResponse])
async def get_child_vaccinations(
    child_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all vaccinations for a child"""
    service = VaccinationService(db)
    vaccinations = await service.get_child_vaccinations(child_id)
    return vaccinations


@router.get("/{vaccination_id}", response_model=VaccinationResponse)
async def get_vaccination(
    vaccination_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific vaccination record"""
    service = VaccinationService(db)
    vaccination = await service.get_vaccination_by_id(vaccination_id)
    
    if not vaccination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaccination record not found"
        )
    
    return vaccination


@router.put("/{vaccination_id}", response_model=VaccinationResponse)
async def update_vaccination(
    vaccination_id: int,
    update_data: VaccinationUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a vaccination record"""
    service = VaccinationService(db)
    vaccination = await service.update_vaccination(vaccination_id, update_data)
    
    if not vaccination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaccination record not found"
        )
    
    # Audit log
    await AuditLogger.log(
        db=db,
        user=current_user,
        action="UPDATE",
        resource_type="vaccination",
        resource_id=vaccination.id,
        description=f"Updated vaccination record: {vaccination.vaccine_name}",
        changes=update_data.model_dump(exclude_unset=True),
        request=request
    )
    
    return vaccination


@router.delete("/{vaccination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vaccination(
    vaccination_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a vaccination record"""
    service = VaccinationService(db)
    success = await service.delete_vaccination(vaccination_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaccination record not found"
        )
    
    # Audit log
    await AuditLogger.log(
        db=db,
        user=current_user,
        action="DELETE",
        resource_type="vaccination",
        resource_id=vaccination_id,
        description=f"Deleted vaccination record ID: {vaccination_id}",
        request=request
    )
    
    return None


# Schedule endpoints
@router.post("/schedule", response_model=VaccinationScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: VaccinationScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a vaccination schedule"""
    service = VaccinationService(db)
    schedule = await service.create_schedule(schedule_data)
    return schedule


@router.get("/schedule/child/{child_id}", response_model=List[VaccinationScheduleResponse])
async def get_child_schedules(
    child_id: int,
    upcoming_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get vaccination schedules for a child"""
    service = VaccinationService(db)
    schedules = await service.get_child_schedules(child_id, upcoming_only)
    return schedules


@router.put("/schedule/{schedule_id}", response_model=VaccinationScheduleResponse)
async def update_schedule(
    schedule_id: int,
    update_data: VaccinationScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a vaccination schedule"""
    service = VaccinationService(db)
    schedule = await service.update_schedule(schedule_id, update_data)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    return schedule


@router.post("/vial-scan", response_model=VialScanResponse)
async def scan_vial(
    scan_data: VialScanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Scan vaccine vial barcode/QR to fetch details"""
    # This is a placeholder - actual implementation would integrate with
    # vaccine manufacturer databases or a master barcode database
    
    return VialScanResponse(
        vaccine_name="Example Vaccine",
        manufacturer="Example Pharma",
        batch_number=scan_data.barcode,
        expiry_date=None,
        vaccine_id=None
    )

