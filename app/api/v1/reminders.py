"""
Vaccination Reminders API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.beneficiary import Beneficiary
from app.services.vaccination_reminder_service import VaccinationReminderService
from app.schemas.reminder import (
    ReminderResponse,
    ReminderCreate,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate
)

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("/beneficiaries/{beneficiary_id}/schedule", response_model=List[ReminderResponse])
async def schedule_reminders(
    beneficiary_id: int,
    force_reschedule: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Schedule reminders for all upcoming vaccinations for a beneficiary"""
    # Verify beneficiary exists and user has access
    from sqlalchemy import select
    result = await db.execute(
        select(Beneficiary).where(
            Beneficiary.id == beneficiary_id,
            Beneficiary.is_active == True
        )
    )
    beneficiary = result.scalar_one_or_none()
    
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiary not found"
        )
    
    # Verify user owns this beneficiary (if needed)
    # This depends on your access control logic
    
    service = VaccinationReminderService(db)
    reminders = await service.schedule_reminders_for_beneficiary(
        beneficiary_id=beneficiary_id,
        force_reschedule=force_reschedule
    )
    
    return [
        ReminderResponse(
            id=r.id,
            beneficiary_id=r.beneficiary_id,
            vaccine_code=r.vaccine_code,
            vaccine_name=r.vaccine_name,
            dose_number=r.dose_number,
            dose_label=r.dose_label,
            reminder_type=r.reminder_type.value,
            scheduled_date=r.scheduled_date.isoformat(),
            scheduled_time=r.scheduled_time.isoformat(),
            status=r.status.value,
            is_enabled=r.is_enabled,
            is_birth_dose=r.is_birth_dose,
            due_date_start=r.due_date_start.isoformat() if r.due_date_start else None,
            due_date_end=r.due_date_end.isoformat() if r.due_date_end else None,
        )
        for r in reminders
    ]


@router.get("/beneficiaries/{beneficiary_id}/upcoming", response_model=List[ReminderResponse])
async def get_upcoming_reminders(
    beneficiary_id: int,
    days_ahead: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming reminders for a beneficiary"""
    service = VaccinationReminderService(db)
    reminders = await service.get_upcoming_reminders(
        beneficiary_id=beneficiary_id,
        days_ahead=days_ahead
    )
    
    # Convert to response format
    return reminders


@router.get("/beneficiaries/{beneficiary_id}/next", response_model=Optional[ReminderResponse])
async def get_next_reminder(
    beneficiary_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the next upcoming reminder for a beneficiary (for Next Vaccination card)"""
    service = VaccinationReminderService(db)
    reminders = await service.get_upcoming_reminders(
        beneficiary_id=beneficiary_id,
        days_ahead=365  # Look ahead 1 year
    )
    
    if not reminders:
        return None
    
    # Return the first (earliest) reminder
    next_reminder = reminders[0]
    
    # Get full reminder details
    from sqlalchemy import select
    from app.models.vaccination_reminder import VaccinationReminder
    result = await db.execute(
        select(VaccinationReminder).where(VaccinationReminder.id == next_reminder['id'])
    )
    reminder = result.scalar_one_or_none()
    
    if not reminder:
        return None
    
    return ReminderResponse(
        id=reminder.id,
        beneficiary_id=reminder.beneficiary_id,
        vaccine_code=reminder.vaccine_code,
        vaccine_name=reminder.vaccine_name,
        dose_number=reminder.dose_number,
        dose_label=reminder.dose_label,
        reminder_type=reminder.reminder_type.value,
        scheduled_date=reminder.scheduled_date.isoformat(),
        scheduled_time=reminder.scheduled_time.isoformat(),
        status=reminder.status.value,
        is_enabled=reminder.is_enabled,
        is_birth_dose=reminder.is_birth_dose,
        due_date_start=reminder.due_date_start.isoformat() if reminder.due_date_start else None,
        due_date_end=reminder.due_date_end.isoformat() if reminder.due_date_end else None,
    )


@router.post("/{reminder_id}/cancel")
async def cancel_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a specific reminder"""
    from sqlalchemy import select
    from app.models.vaccination_reminder import VaccinationReminder, ReminderStatus
    
    result = await db.execute(
        select(VaccinationReminder).where(VaccinationReminder.id == reminder_id)
    )
    reminder = result.scalar_one_or_none()
    
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    reminder.status = ReminderStatus.CANCELLED
    await db.commit()
    
    return {"message": "Reminder cancelled successfully"}


@router.put("/{reminder_id}/enable")
async def toggle_reminder_enabled(
    reminder_id: int,
    enabled: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable or disable a reminder"""
    from sqlalchemy import select
    from app.models.vaccination_reminder import VaccinationReminder
    
    result = await db.execute(
        select(VaccinationReminder).where(VaccinationReminder.id == reminder_id)
    )
    reminder = result.scalar_one_or_none()
    
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    reminder.is_enabled = enabled
    await db.commit()
    
    return {"message": f"Reminder {'enabled' if enabled else 'disabled'} successfully"}

