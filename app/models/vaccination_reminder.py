"""Vaccination Reminder model"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Enum as SQLEnum, Boolean, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.models.base import BaseModel


class ReminderStatus(str, enum.Enum):
    """Reminder status"""
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ReminderType(str, enum.Enum):
    """Reminder type based on timing"""
    SEVEN_DAYS_BEFORE = "seven_days_before"
    ONE_DAY_BEFORE = "one_day_before"
    DUE_DATE = "due_date"
    FOLLOW_UP_MISSED = "follow_up_missed"  # 7 days after due date if missed


class NotificationChannel(str, enum.Enum):
    """Notification delivery channel"""
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"


class VaccinationReminder(BaseModel):
    """Vaccination reminder scheduling and tracking"""
    __tablename__ = "vaccination_reminders"
    
    # Beneficiary reference (child)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Vaccination reference (linked vaccine from timeline)
    vaccine_code = Column(String(50), nullable=False, index=True)
    vaccine_name = Column(String(255), nullable=False)
    dose_number = Column(Integer, nullable=True)
    dose_label = Column(String(100), nullable=True)  # e.g., "Birth Dose", "Dose 1"
    
    # Reminder scheduling
    reminder_type = Column(SQLEnum(ReminderType), nullable=False)
    scheduled_date = Column(Date, nullable=False, index=True)
    scheduled_time = Column(DateTime, nullable=False, index=True)  # Exact datetime to send
    
    # Reminder status
    status = Column(SQLEnum(ReminderStatus), nullable=False, default=ReminderStatus.PENDING, index=True)
    sent_at = Column(DateTime, nullable=True)
    
    # Notification channels (JSON array: ["push", "sms", "email"])
    notification_channels = Column(String(255), nullable=False, default='["push"]')  # JSON array as string
    
    # User preference (can disable specific reminders)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    
    # Vaccination status tracking
    vaccination_id = Column(Integer, ForeignKey("vaccinations.id", ondelete="SET NULL"), nullable=True)
    is_birth_dose = Column(Boolean, nullable=False, default=False)
    
    # Due date information (for reference)
    due_date_start = Column(Date, nullable=True)
    due_date_end = Column(Date, nullable=True)
    
    # Failure tracking
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Relationships
    beneficiary = relationship("Beneficiary", backref="vaccination_reminders")
    vaccination = relationship("Vaccination")
    
    def __repr__(self):
        return f"<VaccinationReminder {self.vaccine_name} - {self.reminder_type} ({self.status})>"


class NotificationPreference(BaseModel):
    """User notification preferences per vaccine"""
    __tablename__ = "notification_preferences"
    
    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Beneficiary reference (child)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Vaccine reference
    vaccine_code = Column(String(50), nullable=False, index=True)
    
    # Preference settings
    is_enabled = Column(Boolean, nullable=False, default=True)
    notification_channels = Column(String(255), nullable=False, default='["push", "sms", "email"]')  # JSON array
    
    # Relationships
    user = relationship("User")
    beneficiary = relationship("Beneficiary")
    
    def __repr__(self):
        return f"<NotificationPreference user={self.user_id} vaccine={self.vaccine_code} enabled={self.is_enabled}>"

