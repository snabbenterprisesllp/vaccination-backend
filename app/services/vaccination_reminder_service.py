"""
Vaccination Reminder Service
Handles scheduling, processing, and sending vaccination reminders
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
import json
import logging

from app.models.beneficiary import Beneficiary
from app.models.vaccination_reminder import (
    VaccinationReminder, 
    ReminderStatus, 
    ReminderType,
    NotificationChannel
)
from app.models.vaccination import Vaccination, VaccinationStatus
from app.services.vaccination_timeline_service import VaccinationTimelineService

logger = logging.getLogger(__name__)


class VaccinationReminderService:
    """Service for managing vaccination reminders"""
    
    # Reminder timing offsets
    SEVEN_DAYS_BEFORE = timedelta(days=7)
    ONE_DAY_BEFORE = timedelta(days=1)
    FOLLOW_UP_MISSED = timedelta(days=7)
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.timeline_service = VaccinationTimelineService(db)
    
    async def schedule_reminders_for_beneficiary(
        self,
        beneficiary_id: int,
        force_reschedule: bool = False
    ) -> List[VaccinationReminder]:
        """
        Schedule reminders for all upcoming vaccinations for a beneficiary
        
        Args:
            beneficiary_id: ID of the beneficiary (child)
            force_reschedule: If True, reschedule even if reminders already exist
            
        Returns:
            List of created reminders
        """
        # Get vaccination timeline
        timeline_data = await self.timeline_service.get_child_timeline(beneficiary_id)
        
        if not timeline_data or 'timeline' not in timeline_data:
            logger.warning(f"No timeline data found for beneficiary {beneficiary_id}")
            return []
        
        timeline_items = timeline_data['timeline']
        beneficiary = timeline_data.get('beneficiary')
        
        if not beneficiary:
            logger.warning(f"Beneficiary not found: {beneficiary_id}")
            return []
        
        created_reminders = []
        
        for item in timeline_items:
            # Skip completed vaccinations
            if item.get('status') == 'COMPLETED':
                continue
            
            # Get due date (for birth doses, use date of birth)
            due_date_start = None
            due_date_end = None
            is_birth_dose = item.get('is_birth_dose', False)
            
            if is_birth_dose:
                # Birth doses are due on date of birth
                due_date_start = date.fromisoformat(beneficiary.date_of_birth) if beneficiary.date_of_birth else None
            else:
                # Regular vaccines have date ranges
                due_date_start_str = item.get('date_range_start')
                due_date_end_str = item.get('date_range_end')
                
                if due_date_start_str:
                    due_date_start = date.fromisoformat(due_date_start_str)
                if due_date_end_str:
                    due_date_end = date.fromisoformat(due_date_end_str)
            
            # Use start date as primary due date for scheduling
            due_date = due_date_start or due_date_end
            
            if not due_date:
                logger.warning(f"No due date found for vaccine {item.get('vaccine_code')}")
                continue
            
            # Check if reminders already exist
            if not force_reschedule:
                existing = await self.db.execute(
                    select(VaccinationReminder).where(
                        and_(
                            VaccinationReminder.beneficiary_id == beneficiary_id,
                            VaccinationReminder.vaccine_code == item.get('vaccine_code'),
                            VaccinationReminder.dose_number == item.get('dose_number'),
                            VaccinationReminder.status == ReminderStatus.PENDING
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue  # Skip if reminders already scheduled
            
            # Cancel existing reminders for this vaccine if rescheduling
            if force_reschedule:
                await self.db.execute(
                    update(VaccinationReminder).where(
                        and_(
                            VaccinationReminder.beneficiary_id == beneficiary_id,
                            VaccinationReminder.vaccine_code == item.get('vaccine_code'),
                            VaccinationReminder.dose_number == item.get('dose_number'),
                            VaccinationReminder.status == ReminderStatus.PENDING
                        )
                    ).values(status=ReminderStatus.CANCELLED)
                )
            
            # Schedule reminders for each timing
            reminders = await self._schedule_reminders_for_vaccine(
                beneficiary_id=beneficiary_id,
                vaccine_code=item.get('vaccine_code'),
                vaccine_name=item.get('vaccine_name'),
                dose_number=item.get('dose_number'),
                dose_label=item.get('dose_label'),
                due_date=due_date,
                is_birth_dose=is_birth_dose,
                due_date_start=due_date_start,
                due_date_end=due_date_end
            )
            
            created_reminders.extend(reminders)
        
        await self.db.commit()
        return created_reminders
    
    async def _schedule_reminders_for_vaccine(
        self,
        beneficiary_id: int,
        vaccine_code: str,
        vaccine_name: str,
        dose_number: Optional[int],
        dose_label: Optional[str],
        due_date: date,
        is_birth_dose: bool,
        due_date_start: Optional[date],
        due_date_end: Optional[date]
    ) -> List[VaccinationReminder]:
        """Schedule all reminder types for a single vaccine"""
        reminders = []
        
        # Get current date
        today = date.today()
        
        # 7 days before reminder
        reminder_date_7d = due_date - self.SEVEN_DAYS_BEFORE
        if reminder_date_7d >= today:
            reminder = VaccinationReminder(
                beneficiary_id=beneficiary_id,
                vaccine_code=vaccine_code,
                vaccine_name=vaccine_name,
                dose_number=dose_number,
                dose_label=dose_label,
                reminder_type=ReminderType.SEVEN_DAYS_BEFORE,
                scheduled_date=reminder_date_7d,
                scheduled_time=datetime.combine(reminder_date_7d, datetime.min.time().replace(hour=9)),  # 9 AM
                is_birth_dose=is_birth_dose,
                due_date_start=due_date_start,
                due_date_end=due_date_end,
                notification_channels='["push", "sms", "email"]'
            )
            self.db.add(reminder)
            reminders.append(reminder)
        
        # 1 day before reminder
        reminder_date_1d = due_date - self.ONE_DAY_BEFORE
        if reminder_date_1d >= today:
            reminder = VaccinationReminder(
                beneficiary_id=beneficiary_id,
                vaccine_code=vaccine_code,
                vaccine_name=vaccine_name,
                dose_number=dose_number,
                dose_label=dose_label,
                reminder_type=ReminderType.ONE_DAY_BEFORE,
                scheduled_date=reminder_date_1d,
                scheduled_time=datetime.combine(reminder_date_1d, datetime.min.time().replace(hour=9)),  # 9 AM
                is_birth_dose=is_birth_dose,
                due_date_start=due_date_start,
                due_date_end=due_date_end,
                notification_channels='["push", "sms", "email"]'
            )
            self.db.add(reminder)
            reminders.append(reminder)
        
        # Due date reminder
        if due_date >= today:
            reminder = VaccinationReminder(
                beneficiary_id=beneficiary_id,
                vaccine_code=vaccine_code,
                vaccine_name=vaccine_name,
                dose_number=dose_number,
                dose_label=dose_label,
                reminder_type=ReminderType.DUE_DATE,
                scheduled_date=due_date,
                scheduled_time=datetime.combine(due_date, datetime.min.time().replace(hour=9)),  # 9 AM
                is_birth_dose=is_birth_dose,
                due_date_start=due_date_start,
                due_date_end=due_date_end,
                notification_channels='["push", "sms", "email"]'
            )
            self.db.add(reminder)
            reminders.append(reminder)
        
        # Follow-up reminder for missed vaccines (7 days after due date)
        # Only schedule if we're already past due date
        if due_date < today:
            follow_up_date = due_date + self.FOLLOW_UP_MISSED
            reminder = VaccinationReminder(
                beneficiary_id=beneficiary_id,
                vaccine_code=vaccine_code,
                vaccine_name=vaccine_name,
                dose_number=dose_number,
                dose_label=dose_label,
                reminder_type=ReminderType.FOLLOW_UP_MISSED,
                scheduled_date=follow_up_date,
                scheduled_time=datetime.combine(follow_up_date, datetime.min.time().replace(hour=9)),  # 9 AM
                is_birth_dose=is_birth_dose,
                due_date_start=due_date_start,
                due_date_end=due_date_end,
                notification_channels='["push", "sms", "email"]'
            )
            self.db.add(reminder)
            reminders.append(reminder)
        
        return reminders
    
    async def cancel_reminders_for_vaccination(
        self,
        beneficiary_id: int,
        vaccine_code: str,
        dose_number: Optional[int]
    ):
        """Cancel all pending reminders for a vaccination once it's marked as given"""
        await self.db.execute(
            update(VaccinationReminder).where(
                and_(
                    VaccinationReminder.beneficiary_id == beneficiary_id,
                    VaccinationReminder.vaccine_code == vaccine_code,
                    VaccinationReminder.dose_number == dose_number,
                    VaccinationReminder.status == ReminderStatus.PENDING
                )
            ).values(status=ReminderStatus.CANCELLED)
        )
        await self.db.commit()
    
    async def get_pending_reminders(
        self,
        beneficiary_id: Optional[int] = None,
        limit: int = 100
    ) -> List[VaccinationReminder]:
        """Get pending reminders that are due to be sent"""
        query = select(VaccinationReminder).where(
            and_(
                VaccinationReminder.status == ReminderStatus.PENDING,
                VaccinationReminder.is_enabled == True,
                VaccinationReminder.scheduled_time <= datetime.now()
            )
        )
        
        if beneficiary_id:
            query = query.where(VaccinationReminder.beneficiary_id == beneficiary_id)
        
        query = query.order_by(VaccinationReminder.scheduled_time.asc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_upcoming_reminders(
        self,
        beneficiary_id: int,
        days_ahead: int = 30
    ) -> List[Dict]:
        """Get upcoming reminders for a beneficiary"""
        end_date = date.today() + timedelta(days=days_ahead)
        
        result = await self.db.execute(
            select(VaccinationReminder).where(
                and_(
                    VaccinationReminder.beneficiary_id == beneficiary_id,
                    VaccinationReminder.status == ReminderStatus.PENDING,
                    VaccinationReminder.is_enabled == True,
                    VaccinationReminder.scheduled_date <= end_date,
                    VaccinationReminder.scheduled_date >= date.today()
                )
            ).order_by(VaccinationReminder.scheduled_date.asc())
        )
        
        reminders = result.scalars().all()
        
        return [
            {
                'id': r.id,
                'vaccine_code': r.vaccine_code,
                'vaccine_name': r.vaccine_name,
                'dose_label': r.dose_label,
                'reminder_type': r.reminder_type.value,
                'scheduled_date': r.scheduled_date.isoformat(),
                'scheduled_time': r.scheduled_time.isoformat(),
                'due_date_start': r.due_date_start.isoformat() if r.due_date_start else None,
                'due_date_end': r.due_date_end.isoformat() if r.due_date_end else None,
                'is_birth_dose': r.is_birth_dose,
            }
            for r in reminders
        ]
    
    async def mark_reminder_sent(
        self,
        reminder_id: int,
        success: bool = True,
        failure_reason: Optional[str] = None
    ):
        """Mark a reminder as sent or failed"""
        reminder = await self.db.get(VaccinationReminder, reminder_id)
        if not reminder:
            return
        
        if success:
            reminder.status = ReminderStatus.SENT
            reminder.sent_at = datetime.now()
        else:
            reminder.status = ReminderStatus.FAILED
            reminder.failure_reason = failure_reason
            reminder.retry_count += 1
        
        await self.db.commit()


def get_vaccine_importance_message(vaccine_code: str, vaccine_name: str) -> str:
    """Get a one-line importance message for a vaccine"""
    # Simple mapping - can be enhanced with vaccine education utility
    importance_messages = {
        'BCG': 'Protects against tuberculosis, especially important for newborns',
        'OPV': 'Prevents polio, a serious disease that can cause paralysis',
        'DPT': 'Protects against diphtheria, pertussis, and tetanus',
        'HEPB': 'Prevents hepatitis B, which can cause liver disease',
        'MMR': 'Protects against measles, mumps, and rubella',
        'HIB': 'Prevents serious bacterial infections in young children',
        'ROTAVIRUS': 'Protects against severe diarrhea and dehydration',
        'PCV': 'Prevents pneumococcal disease including pneumonia and meningitis',
    }
    
    # Try to match by code or name
    code_upper = vaccine_code.upper()
    if code_upper in importance_messages:
        return importance_messages[code_upper]
    
    name_upper = vaccine_name.upper()
    for key, message in importance_messages.items():
        if key in name_upper:
            return message
    
    return f'Important for protecting against {vaccine_name}'

