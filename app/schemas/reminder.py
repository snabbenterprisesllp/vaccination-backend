"""
Reminder schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class ReminderResponse(BaseModel):
    """Reminder response schema"""
    id: int
    beneficiary_id: int
    vaccine_code: str
    vaccine_name: str
    dose_number: Optional[int] = None
    dose_label: Optional[str] = None
    reminder_type: str  # "seven_days_before", "one_day_before", "due_date", "follow_up_missed"
    scheduled_date: str  # ISO date
    scheduled_time: str  # ISO datetime
    status: str  # "pending", "sent", "cancelled", "failed"
    is_enabled: bool
    is_birth_dose: bool
    due_date_start: Optional[str] = None  # ISO date
    due_date_end: Optional[str] = None  # ISO date
    
    class Config:
        from_attributes = True


class ReminderCreate(BaseModel):
    """Create reminder request schema"""
    beneficiary_id: int
    vaccine_code: str
    vaccine_name: str
    dose_number: Optional[int] = None
    reminder_type: str
    scheduled_date: date
    notification_channels: List[str] = ["push", "sms", "email"]


class NotificationPreferenceResponse(BaseModel):
    """Notification preference response schema"""
    id: int
    user_id: int
    beneficiary_id: int
    vaccine_code: str
    is_enabled: bool
    notification_channels: List[str]
    
    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    """Update notification preference request schema"""
    is_enabled: Optional[bool] = None
    notification_channels: Optional[List[str]] = None

