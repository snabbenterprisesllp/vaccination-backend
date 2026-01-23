"""
Analytics schemas for response models
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class FacilityPerformanceResponse(BaseModel):
    """Schema for facility performance in global analytics"""
    facility_id: int
    facility_name: str
    facility_code: Optional[str] = None
    city: str
    state: str
    vaccinations_completed: int
    vaccinations_today: int = 0
    vaccinations_this_month: int = 0
    missed_vaccinations: int = 0
    active_doctors: int = 0
    active_staff: int = 0
    users_count: int
    is_active: bool


class GlobalAnalyticsResponse(BaseModel):
    """Schema for global analytics response"""
    total_facilities: int
    active_facilities: int
    total_children: int
    total_beneficiaries: int
    vaccinations_completed: int
    vaccinations_pending: int
    vaccinations_today: int = 0
    vaccinations_this_month: int = 0
    total_doctors: int = 0
    total_staff: int = 0
    total_facility_admins: int = 0
    missed_vaccinations_today: int = 0
    missed_vaccinations_this_month: int = 0
    facility_performance: List[FacilityPerformanceResponse]


class FacilityAnalyticsResponse(BaseModel):
    """Schema for facility analytics response"""
    facility_id: int
    facility_name: str
    total_users: int
    doctors_count: int
    staff_count: int
    vaccinations_completed: int
    vaccinations_pending: int
    vaccinations_last_30_days: int
    vaccinations_today: int = 0
    upcoming_due_vaccinations: int = 0
    missed_vaccinations: int = 0


class DailyTrendItem(BaseModel):
    """Schema for daily trend item"""
    date: str
    count: int


class DailyTrendResponse(BaseModel):
    """Schema for daily trend response"""
    facility_id: int
    start_date: str
    end_date: str
    trends: List[DailyTrendItem]


class WeeklyTrendItem(BaseModel):
    """Schema for weekly trend item"""
    week_start: str
    count: int


class WeeklyTrendResponse(BaseModel):
    """Schema for weekly trend response"""
    facility_id: int
    weeks: int
    trends: List[WeeklyTrendItem]


class MonthlyTrendItem(BaseModel):
    """Schema for monthly trend item"""
    month_start: str
    count: int


class MonthlyTrendResponse(BaseModel):
    """Schema for monthly trend response"""
    facility_id: int
    months: int
    trends: List[MonthlyTrendItem]


class VaccineDistributionItem(BaseModel):
    """Schema for vaccine distribution item"""
    vaccine_name: str
    count: int
    percentage: float


class VaccineDistributionResponse(BaseModel):
    """Schema for vaccine distribution response"""
    facility_id: int
    start_date: str
    end_date: str
    total_vaccinations: int
    distribution: List[VaccineDistributionItem]


class TodayActivityItem(BaseModel):
    """Schema for today's activity item"""
    child_name: str
    age: str
    vaccine_name: str
    doctor: Optional[str]
    status: str
    time: Optional[str]


class TodayActivityResponse(BaseModel):
    """Schema for today's activity response"""
    facility_id: int
    date: str
    activities: List[TodayActivityItem]


class AlertItem(BaseModel):
    """Schema for alert item"""
    type: str
    message: str
    severity: str
    count: Optional[int] = None


class AlertsResponse(BaseModel):
    """Schema for alerts response"""
    facility_id: int
    alerts: List[AlertItem]


class DoctorPerformanceItem(BaseModel):
    """Schema for doctor performance item"""
    doctor_name: str
    doctor_id: Optional[int]
    vaccinations_today: int
    vaccinations_this_month: int


class DoctorPerformanceResponse(BaseModel):
    """Schema for doctor performance response"""
    facility_id: int
    doctors: List[DoctorPerformanceItem]


class AgeGroupItem(BaseModel):
    """Schema for age group item"""
    age_group: str
    count: int


class AgeGroupResponse(BaseModel):
    """Schema for age group analytics response"""
    facility_id: int
    age_groups: List[AgeGroupItem]


class MissedVaccinationAnalytics(BaseModel):
    """Schema for missed vaccination analytics"""
    facility_id: int
    total_missed: int
    delayed_percentage: float
    missed_trend: List[DailyTrendItem]
    completed_trend: List[DailyTrendItem]


class GlobalAlertItem(BaseModel):
    """Schema for global alert item"""
    type: str
    message: str
    severity: str
    facility_id: Optional[int] = None
    facility_name: Optional[str] = None
    count: Optional[int] = None


class GlobalAlertsResponse(BaseModel):
    """Schema for global alerts response"""
    alerts: List[GlobalAlertItem]


class GlobalVaccinationTrendResponse(BaseModel):
    """Schema for global vaccination trend response"""
    start_date: str
    end_date: str
    trends: List[DailyTrendItem]
    by_facility: Optional[List[Dict[str, Any]]] = None


class GlobalVaccineDistributionResponse(BaseModel):
    """Schema for global vaccine distribution response"""
    start_date: str
    end_date: str
    total_vaccinations: int
    distribution: List[VaccineDistributionItem]


class GlobalDoctorPerformanceItem(BaseModel):
    """Schema for global doctor performance item"""
    doctor_name: str
    doctor_id: Optional[int]
    facility_id: int
    facility_name: str
    vaccinations_today: int
    vaccinations_this_month: int
    missed_followups: int = 0


class GlobalDoctorPerformanceResponse(BaseModel):
    """Schema for global doctor performance response"""
    doctors: List[GlobalDoctorPerformanceItem]


class GlobalAgeGroupResponse(BaseModel):
    """Schema for global age group analytics response"""
    start_date: str
    end_date: str
    age_groups: List[AgeGroupItem]


class GlobalMissedVaccinationAnalytics(BaseModel):
    """Schema for global missed vaccination analytics"""
    start_date: str
    end_date: str
    total_missed: int
    delayed_percentage: float
    missed_trend: List[DailyTrendItem]
    completed_trend: List[DailyTrendItem]
    by_facility: Optional[List[Dict[str, Any]]] = None

