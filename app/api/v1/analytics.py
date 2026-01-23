"""
Analytics APIs

Endpoints for:
- Global analytics (SUPER_ADMIN only)
- Facility analytics (FACILITY_ADMIN for their facility, SUPER_ADMIN for any)
- Daily, weekly, monthly trends
- Vaccine distribution analytics
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case, distinct
from sqlalchemy.sql import func as sql_func
from typing import Optional, List, Dict
from datetime import datetime, timedelta, date
import logging

from app.core.database import get_db
from app.core.rbac import (
    require_super_admin,
    require_facility_admin,
    is_super_admin,
    get_user_facilities
)
from app.models.user import User
from app.models.facility import Facility
from app.models.facility_user import FacilityUser
from app.models.beneficiary import Beneficiary
from app.models.vaccination import Vaccination, VaccinationStatus, VaccinationSchedule
from app.models.child_profile import ChildProfile
from app.models.vaccine_master import VaccineMaster
from app.schemas.analytics import (
    GlobalAnalyticsResponse,
    FacilityAnalyticsResponse,
    FacilityPerformanceResponse,
    DailyTrendResponse,
    WeeklyTrendResponse,
    MonthlyTrendResponse,
    VaccineDistributionResponse,
    TodayActivityResponse,
    TodayActivityItem,
    AlertsResponse,
    AlertItem,
    DoctorPerformanceResponse,
    DoctorPerformanceItem,
    AgeGroupResponse,
    AgeGroupItem,
    MissedVaccinationAnalytics,
    GlobalAlertItem,
    GlobalAlertsResponse,
    GlobalVaccinationTrendResponse,
    GlobalVaccineDistributionResponse,
    GlobalDoctorPerformanceItem,
    GlobalDoctorPerformanceResponse,
    GlobalAgeGroupResponse,
    GlobalMissedVaccinationAnalytics
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# GLOBAL ANALYTICS (SUPER_ADMIN only)
# ============================================================================

@router.get("/global", response_model=GlobalAnalyticsResponse)
async def get_global_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get enhanced global analytics across all facilities (SUPER_ADMIN only)
    Supports date range filtering for time-based metrics
    """
    logger.info(f"Global analytics requested by user {current_user.id} ({current_user.mobile_number})")
    
    today = date.today()
    start_of_month = today.replace(day=1)
    
    # Use provided dates or default to today/month
    filter_start = start_date or today
    filter_end = end_date or today
    
    # Total facilities
    total_facilities_result = await db.execute(
        select(func.count(Facility.id))
    )
    total_facilities = total_facilities_result.scalar() or 0
    
    # Active facilities
    active_facilities_result = await db.execute(
        select(func.count(Facility.id)).where(Facility.is_active == True)
    )
    active_facilities = active_facilities_result.scalar() or 0
    
    # Total children registered
    children_result = await db.execute(
        select(func.count(ChildProfile.id))
    )
    total_children = children_result.scalar() or 0
    
    # Total beneficiaries (ADULT + CHILD)
    beneficiaries_result = await db.execute(
        select(func.count(Beneficiary.id))
    )
    total_beneficiaries = beneficiaries_result.scalar() or 0
    
    # Vaccinations completed (all time)
    completed_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            Vaccination.status == VaccinationStatus.COMPLETED
        )
    )
    vaccinations_completed = completed_result.scalar() or 0
    
    # Vaccinations pending (scheduled)
    pending_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            Vaccination.status == VaccinationStatus.SCHEDULED
        )
    )
    vaccinations_pending = pending_result.scalar() or 0
    
    # Vaccinations today
    vaccinations_today_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date == today
            )
        )
    )
    vaccinations_today = vaccinations_today_result.scalar() or 0
    
    # Vaccinations this month
    vaccinations_month_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date >= start_of_month,
                Vaccination.vaccination_date <= today
            )
        )
    )
    vaccinations_this_month = vaccinations_month_result.scalar() or 0
    
    # Total doctors (across all facilities)
    doctors_result = await db.execute(
        select(func.count(FacilityUser.id)).where(
            and_(
                FacilityUser.facility_role == "doctor",
                FacilityUser.is_active == True
            )
        )
    )
    total_doctors = doctors_result.scalar() or 0
    
    # Total staff (across all facilities)
    staff_result = await db.execute(
        select(func.count(FacilityUser.id)).where(
            and_(
                FacilityUser.facility_role == "staff",
                FacilityUser.is_active == True
            )
        )
    )
    total_staff = staff_result.scalar() or 0
    
    # Total facility admins (across all facilities)
    facility_admins_result = await db.execute(
        select(func.count(FacilityUser.id)).where(
            and_(
                FacilityUser.facility_role == "facility_admin",
                FacilityUser.is_active == True
            )
        )
    )
    total_facility_admins = facility_admins_result.scalar() or 0
    
    # Missed vaccinations today
    missed_today_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.status == VaccinationStatus.MISSED,
                Vaccination.vaccination_date == today
            )
        )
    )
    missed_vaccinations_today = missed_today_result.scalar() or 0
    
    # Missed vaccinations this month
    missed_month_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.status == VaccinationStatus.MISSED,
                Vaccination.vaccination_date >= start_of_month,
                Vaccination.vaccination_date <= today
            )
        )
    )
    missed_vaccinations_this_month = missed_month_result.scalar() or 0
    
    # Facility-wise performance with detailed metrics
    facility_performance = []
    facilities_result = await db.execute(
        select(Facility).where(Facility.is_active == True)
    )
    facilities = facilities_result.scalars().all()
    
    for facility in facilities:
        # Total vaccinations completed for this facility
        facility_vaccinations_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                and_(
                    Vaccination.facility_id == facility.id,
                    Vaccination.status == VaccinationStatus.COMPLETED
                )
            )
        )
        facility_vaccinations = facility_vaccinations_result.scalar() or 0
        
        # Vaccinations today
        facility_vaccinations_today_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                and_(
                    Vaccination.facility_id == facility.id,
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date == today
                )
            )
        )
        facility_vaccinations_today = facility_vaccinations_today_result.scalar() or 0
        
        # Vaccinations this month
        facility_vaccinations_month_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                and_(
                    Vaccination.facility_id == facility.id,
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date >= start_of_month,
                    Vaccination.vaccination_date <= today
                )
            )
        )
        facility_vaccinations_month = facility_vaccinations_month_result.scalar() or 0
        
        # Missed vaccinations
        facility_missed_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                and_(
                    Vaccination.facility_id == facility.id,
                    Vaccination.status == VaccinationStatus.MISSED
                )
            )
        )
        facility_missed = facility_missed_result.scalar() or 0
        
        # Active doctors
        facility_doctors_result = await db.execute(
            select(func.count(FacilityUser.id)).where(
                and_(
                    FacilityUser.facility_id == facility.id,
                    FacilityUser.facility_role == "doctor",
                    FacilityUser.is_active == True
                )
            )
        )
        facility_doctors = facility_doctors_result.scalar() or 0
        
        # Active staff
        facility_staff_result = await db.execute(
            select(func.count(FacilityUser.id)).where(
                and_(
                    FacilityUser.facility_id == facility.id,
                    FacilityUser.facility_role == "staff",
                    FacilityUser.is_active == True
                )
            )
        )
        facility_staff = facility_staff_result.scalar() or 0
        
        # Total users
        facility_users_result = await db.execute(
            select(func.count(FacilityUser.id)).where(
                and_(
                    FacilityUser.facility_id == facility.id,
                    FacilityUser.is_active == True
                )
            )
        )
        facility_users_count = facility_users_result.scalar() or 0
        
        facility_performance.append({
            "facility_id": facility.id,
            "facility_name": facility.name,
            "facility_code": facility.facility_code,
            "city": facility.city,
            "state": facility.state,
            "vaccinations_completed": facility_vaccinations,
            "vaccinations_today": facility_vaccinations_today,
            "vaccinations_this_month": facility_vaccinations_month,
            "missed_vaccinations": facility_missed,
            "active_doctors": facility_doctors,
            "active_staff": facility_staff,
            "users_count": facility_users_count,
            "is_active": facility.is_active
        })
    
    return GlobalAnalyticsResponse(
        total_facilities=total_facilities,
        active_facilities=active_facilities,
        total_children=total_children,
        total_beneficiaries=total_beneficiaries,
        vaccinations_completed=vaccinations_completed,
        vaccinations_pending=vaccinations_pending,
        vaccinations_today=vaccinations_today,
        vaccinations_this_month=vaccinations_this_month,
        total_doctors=total_doctors,
        total_staff=total_staff,
        total_facility_admins=total_facility_admins,
        missed_vaccinations_today=missed_vaccinations_today,
        missed_vaccinations_this_month=missed_vaccinations_this_month,
        facility_performance=facility_performance
    )


# ============================================================================
# ENHANCED SUPER ADMIN ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/global/alerts", response_model=GlobalAlertsResponse)
async def get_global_alerts(
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system-wide alerts for Super Admin (SUPER_ADMIN only)
    """
    logger.info(f"Global alerts requested by user {current_user.id}")
    alerts = []
    today = date.today()
    
    # Get all active facilities
    facilities_result = await db.execute(
        select(Facility).where(Facility.is_active == True)
    )
    facilities = facilities_result.scalars().all()
    
    for facility in facilities:
        # Check for zero vaccinations today
        today_vaccinations_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                and_(
                    Vaccination.facility_id == facility.id,
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date == today
                )
            )
        )
        today_vaccinations = today_vaccinations_result.scalar() or 0
        
        if today_vaccinations == 0:
            alerts.append(GlobalAlertItem(
                type="zero_vaccinations_today",
                message=f"{facility.name} has zero vaccinations today",
                severity="warning",
                facility_id=facility.id,
                facility_name=facility.name,
                count=0
            ))
        
        # Check for high missed vaccination rate
        total_vaccinations_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                Vaccination.facility_id == facility.id
            )
        )
        total_vaccinations = total_vaccinations_result.scalar() or 0
        
        if total_vaccinations > 0:
            missed_result = await db.execute(
                select(func.count(Vaccination.id)).where(
                    and_(
                        Vaccination.facility_id == facility.id,
                        Vaccination.status == VaccinationStatus.MISSED
                    )
                )
            )
            missed_count = missed_result.scalar() or 0
            missed_percentage = (missed_count / total_vaccinations) * 100
            
            if missed_percentage > 20:  # Threshold: 20%
                alerts.append(GlobalAlertItem(
                    type="high_missed_rate",
                    message=f"{facility.name} has {missed_percentage:.1f}% missed vaccination rate",
                    severity="error",
                    facility_id=facility.id,
                    facility_name=facility.name,
                    count=missed_count
                ))
        
        # Check for inactive doctors/staff
        active_doctors_result = await db.execute(
            select(func.count(FacilityUser.id)).where(
                and_(
                    FacilityUser.facility_id == facility.id,
                    FacilityUser.facility_role == "doctor",
                    FacilityUser.is_active == True
                )
            )
        )
        active_doctors = active_doctors_result.scalar() or 0
        
        if active_doctors == 0:
            alerts.append(GlobalAlertItem(
                type="no_active_doctors",
                message=f"{facility.name} has no active doctors",
                severity="warning",
                facility_id=facility.id,
                facility_name=facility.name,
                count=0
            ))
    
    return GlobalAlertsResponse(alerts=alerts)


@router.get("/global/trends", response_model=GlobalVaccinationTrendResponse)
async def get_global_vaccination_trends(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    facility_id: Optional[int] = Query(None),
    vaccine_type: Optional[str] = Query(None),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get global vaccination trends across all facilities (SUPER_ADMIN only)
    Supports filtering by date range, facility, and vaccine type
    """
    logger.info(f"Global trends requested by user {current_user.id}")
    
    # Default to last 30 days if not specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Build query
    query = select(
        Vaccination.vaccination_date,
        func.count(Vaccination.id).label('count')
    ).where(
        and_(
            Vaccination.status == VaccinationStatus.COMPLETED,
            Vaccination.vaccination_date >= start_date,
            Vaccination.vaccination_date <= end_date
        )
    )
    
    if facility_id:
        query = query.where(Vaccination.facility_id == facility_id)
    
    if vaccine_type:
        query = query.join(VaccineMaster).where(VaccineMaster.name.ilike(f"%{vaccine_type}%"))
    
    query = query.group_by(Vaccination.vaccination_date).order_by(Vaccination.vaccination_date)
    
    result = await db.execute(query)
    trend_data = result.all()
    
    trends = [
        DailyTrendItem(date=str(row.vaccination_date), count=row.count)
        for row in trend_data
    ]
    
    # Get facility-wise breakdown if no facility filter
    by_facility = None
    if not facility_id:
        facility_query = select(
            Facility.id,
            Facility.name,
            func.count(Vaccination.id).label('count')
        ).join(
            Vaccination, Vaccination.facility_id == Facility.id
        ).where(
            and_(
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date >= start_date,
                Vaccination.vaccination_date <= end_date,
                Facility.is_active == True
            )
        ).group_by(Facility.id, Facility.name).order_by(func.count(Vaccination.id).desc())
        
        facility_result = await db.execute(facility_query)
        by_facility = [
            {
                "facility_id": row.id,
                "facility_name": row.name,
                "vaccinations": row.count
            }
            for row in facility_result.all()
        ]
    
    return GlobalVaccinationTrendResponse(
        start_date=str(start_date),
        end_date=str(end_date),
        trends=trends,
        by_facility=by_facility
    )


@router.get("/global/vaccine-distribution", response_model=GlobalVaccineDistributionResponse)
async def get_global_vaccine_distribution(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get global vaccine distribution across all facilities (SUPER_ADMIN only)
    """
    logger.info(f"Global vaccine distribution requested by user {current_user.id}")
    
    # Default to last 30 days if not specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get vaccine distribution
    try:
        result = await db.execute(
            select(
                VaccineMaster.vaccine_name,
                func.count(Vaccination.id).label('count')
            ).join(
                Vaccination, Vaccination.vaccine_id == VaccineMaster.id
            ).where(
                and_(
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date >= start_date,
                    Vaccination.vaccination_date <= end_date
                )
            ).group_by(VaccineMaster.id, VaccineMaster.vaccine_name)
            .order_by(func.count(Vaccination.id).desc())
        )
        
        vaccine_data = result.all()
        total_vaccinations = sum(row.count for row in vaccine_data) if vaccine_data else 0
        
        distribution = []
        for row in vaccine_data:
            percentage = (row.count / total_vaccinations * 100) if total_vaccinations > 0 else 0
            distribution.append(VaccineDistributionItem(
                vaccine_name=row.vaccine_name,
                count=row.count,
                percentage=round(percentage, 2)
            ))
        
        return GlobalVaccineDistributionResponse(
            start_date=str(start_date),
            end_date=str(end_date),
            total_vaccinations=total_vaccinations,
            distribution=distribution
        )
    except Exception as e:
        logger.error(f"Error getting global vaccine distribution: {e}")
        import traceback
        traceback.print_exc()
        # Return empty distribution instead of failing
        return GlobalVaccineDistributionResponse(
            start_date=str(start_date),
            end_date=str(end_date),
            total_vaccinations=0,
            distribution=[]
        )


@router.get("/global/doctor-performance", response_model=GlobalDoctorPerformanceResponse)
async def get_global_doctor_performance(
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get global doctor performance across all facilities (SUPER_ADMIN only)
    """
    logger.info(f"Global doctor performance requested by user {current_user.id}")
    
    today = date.today()
    start_of_month = today.replace(day=1)
    
    # Get doctor performance with facility info
    result = await db.execute(
        select(
            User.id.label('doctor_id'),
            User.full_name.label('doctor_name'),
            Facility.id.label('facility_id'),
            Facility.name.label('facility_name'),
            func.sum(
                case(
                    (Vaccination.vaccination_date == today, 1),
                    else_=0
                )
            ).label('today_count'),
            func.sum(
                case(
                    (
                        and_(
                            Vaccination.vaccination_date >= start_of_month,
                            Vaccination.vaccination_date <= today
                        ),
                        1
                    ),
                    else_=0
                )
            ).label('month_count')
        ).join(
            FacilityUser, FacilityUser.user_id == User.id
        ).join(
            Facility, Facility.id == FacilityUser.facility_id
        ).outerjoin(
            Vaccination, and_(
                Vaccination.recorded_by_user_id == User.id,
                Vaccination.status == VaccinationStatus.COMPLETED
            )
        ).where(
            and_(
                FacilityUser.facility_role == "doctor",
                FacilityUser.is_active == True,
                Facility.is_active == True
            )
        ).group_by(
            User.id, User.full_name, Facility.id, Facility.name
        ).order_by(func.sum(
            case(
                (
                    and_(
                        Vaccination.vaccination_date >= start_of_month,
                        Vaccination.vaccination_date <= today
                    ),
                    1
                ),
                else_=0
            )
        ).desc())
    )
    
    doctors = []
    for row in result.all():
        # Calculate missed follow-ups (schedules past due and not completed)
        # Note: VaccinationSchedule doesn't have facility_id, so we'll use a simplified approach
        # Count overdue schedules for children/beneficiaries associated with this facility
        today = date.today()
        missed_result = await db.execute(
            select(func.count(VaccinationSchedule.id))
            .join(
                ChildProfile, VaccinationSchedule.child_id == ChildProfile.id
            ).join(
                Vaccination, and_(
                    Vaccination.child_id == ChildProfile.id,
                    Vaccination.facility_id == row.facility_id
                )
            ).where(
                and_(
                    VaccinationSchedule.due_date < today,
                    VaccinationSchedule.completed == False
                )
            )
        )
        missed_followups = missed_result.scalar() or 0
        
        doctors.append(GlobalDoctorPerformanceItem(
            doctor_name=row.doctor_name or "Unknown",
            doctor_id=row.doctor_id,
            facility_id=row.facility_id,
            facility_name=row.facility_name,
            vaccinations_today=row.today_count or 0,
            vaccinations_this_month=row.month_count or 0,
            missed_followups=missed_followups
        ))
    
    return GlobalDoctorPerformanceResponse(doctors=doctors)


@router.get("/global/age-groups", response_model=GlobalAgeGroupResponse)
async def get_global_age_group_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get global age group coverage analytics (SUPER_ADMIN only)
    """
    logger.info(f"Global age group analytics requested by user {current_user.id}")
    
    # Default to last 30 days if not specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Age groups based on vaccination schedules
    age_groups = [
        ("Birth - 6 weeks", 0, 42),
        ("6 - 14 weeks", 42, 98),
        ("6 - 9 months", 180, 270),
        ("9 - 12 months", 270, 365),
        ("1 - 5 years", 365, 1825),
    ]
    
    age_group_data = []
    
    for age_group_name, min_days, max_days in age_groups:
        # Calculate age at vaccination date
        min_birth_date = end_date - timedelta(days=max_days)
        max_birth_date = end_date - timedelta(days=min_days)
        
        result = await db.execute(
            select(func.count(Vaccination.id)).join(
                ChildProfile, Vaccination.child_id == ChildProfile.id
            ).where(
                and_(
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date >= start_date,
                    Vaccination.vaccination_date <= end_date,
                    ChildProfile.date_of_birth >= min_birth_date,
                    ChildProfile.date_of_birth <= max_birth_date
                )
            )
        )
        count = result.scalar() or 0
        
        age_group_data.append(AgeGroupItem(
            age_group=age_group_name,
            count=count
        ))
    
    return GlobalAgeGroupResponse(
        start_date=str(start_date),
        end_date=str(end_date),
        age_groups=age_group_data
    )


@router.get("/global/missed-analytics", response_model=GlobalMissedVaccinationAnalytics)
async def get_global_missed_vaccination_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get global missed vaccination analytics (SUPER_ADMIN only)
    """
    logger.info(f"Global missed vaccination analytics requested by user {current_user.id}")
    
    # Default to last 30 days if not specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get missed vaccinations trend
    missed_result = await db.execute(
        select(
            Vaccination.vaccination_date,
            func.count(Vaccination.id).label('count')
        ).where(
            and_(
                Vaccination.status == VaccinationStatus.MISSED,
                Vaccination.vaccination_date >= start_date,
                Vaccination.vaccination_date <= end_date
            )
        ).group_by(Vaccination.vaccination_date)
        .order_by(Vaccination.vaccination_date)
    )
    
    missed_trend_data = missed_result.all()
    missed_trend = [
        DailyTrendItem(date=str(row.vaccination_date), count=row.count)
        for row in missed_trend_data
    ]
    
    # Get completed vaccinations trend
    completed_result = await db.execute(
        select(
            Vaccination.vaccination_date,
            func.count(Vaccination.id).label('count')
        ).where(
            and_(
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date >= start_date,
                Vaccination.vaccination_date <= end_date
            )
        ).group_by(Vaccination.vaccination_date)
        .order_by(Vaccination.vaccination_date)
    )
    
    completed_trend_data = completed_result.all()
    completed_trend = [
        DailyTrendItem(date=str(row.vaccination_date), count=row.count)
        for row in completed_trend_data
    ]
    
    # Calculate totals and percentage
    total_missed = sum(item.count for item in missed_trend)
    total_completed = sum(item.count for item in completed_trend)
    total_all = total_missed + total_completed
    delayed_percentage = (total_missed / total_all * 100) if total_all > 0 else 0
    
    # Get facility-wise breakdown
    facility_result = await db.execute(
        select(
            Facility.id,
            Facility.name,
            func.count(Vaccination.id).label('missed_count')
        ).join(
            Vaccination, Vaccination.facility_id == Facility.id
        ).where(
            and_(
                Vaccination.status == VaccinationStatus.MISSED,
                Vaccination.vaccination_date >= start_date,
                Vaccination.vaccination_date <= end_date,
                Facility.is_active == True
            )
        ).group_by(Facility.id, Facility.name)
        .order_by(func.count(Vaccination.id).desc())
    )
    
    by_facility = [
        {
            "facility_id": row.id,
            "facility_name": row.name,
            "missed_count": row.missed_count
        }
        for row in facility_result.all()
    ]
    
    return GlobalMissedVaccinationAnalytics(
        start_date=str(start_date),
        end_date=str(end_date),
        total_missed=total_missed,
        delayed_percentage=round(delayed_percentage, 2),
        missed_trend=missed_trend,
        completed_trend=completed_trend,
        by_facility=by_facility
    )


# ============================================================================
# FACILITY ANALYTICS (FACILITY_ADMIN, SUPER_ADMIN)
# ============================================================================

@router.get("/facility/{facility_id}", response_model=FacilityAnalyticsResponse)
async def get_facility_analytics(
    facility_id: int,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get facility analytics (FACILITY_ADMIN for their facility, SUPER_ADMIN for any)
    """
    current_user, facility_user = user_facility
    
    # Check if user is super admin or has access to this facility
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    # Get facility
    facility_result = await db.execute(
        select(Facility).where(Facility.id == facility_id)
    )
    facility = facility_result.scalar_one_or_none()
    
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility not found"
        )
    
    today = date.today()
    start_of_month = today.replace(day=1)
    start_of_30_days = today - timedelta(days=30)
    
    # Total users
    users_result = await db.execute(
        select(func.count(FacilityUser.id)).where(
            and_(
                FacilityUser.facility_id == facility_id,
                FacilityUser.is_active == True
            )
        )
    )
    total_users = users_result.scalar() or 0
    
    # Doctors count
    doctors_result = await db.execute(
        select(func.count(FacilityUser.id)).where(
            and_(
                FacilityUser.facility_id == facility_id,
                FacilityUser.facility_role == "doctor",
                FacilityUser.is_active == True
            )
        )
    )
    doctors_count = doctors_result.scalar() or 0
    
    # Staff count
    staff_result = await db.execute(
        select(func.count(FacilityUser.id)).where(
            and_(
                FacilityUser.facility_id == facility_id,
                FacilityUser.facility_role == "staff",
                FacilityUser.is_active == True
            )
        )
    )
    staff_count = staff_result.scalar() or 0
    
    # Vaccinations completed
    completed_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.COMPLETED
            )
        )
    )
    vaccinations_completed = completed_result.scalar() or 0
    
    # Vaccinations pending
    pending_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.SCHEDULED
            )
        )
    )
    vaccinations_pending = pending_result.scalar() or 0
    
    # Vaccinations last 30 days
    last_30_days_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date >= start_of_30_days,
                Vaccination.vaccination_date <= today
            )
        )
    )
    vaccinations_last_30_days = last_30_days_result.scalar() or 0
    
    # Vaccinations today
    today_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date == today
            )
        )
    )
    vaccinations_today = today_result.scalar() or 0
    
    # Upcoming due vaccinations (scheduled for future)
    upcoming_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.SCHEDULED,
                Vaccination.vaccination_date >= today
            )
        )
    )
    upcoming_due_vaccinations = upcoming_result.scalar() or 0
    
    # Missed vaccinations
    missed_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.MISSED
            )
        )
    )
    missed_vaccinations = missed_result.scalar() or 0
    
    return FacilityAnalyticsResponse(
        facility_id=facility_id,
        facility_name=facility.name,
        total_users=total_users,
        doctors_count=doctors_count,
        staff_count=staff_count,
        vaccinations_completed=vaccinations_completed,
        vaccinations_pending=vaccinations_pending,
        vaccinations_last_30_days=vaccinations_last_30_days,
        vaccinations_today=vaccinations_today,
        upcoming_due_vaccinations=upcoming_due_vaccinations,
        missed_vaccinations=missed_vaccinations
    )


@router.get("/facility/{facility_id}/daily", response_model=DailyTrendResponse)
async def get_facility_daily_trends(
    facility_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily vaccination trends for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    result = await db.execute(
        select(
            Vaccination.vaccination_date,
            func.count(Vaccination.id).label('count')
        ).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date >= start_date,
                Vaccination.vaccination_date <= end_date
            )
        ).group_by(Vaccination.vaccination_date)
        .order_by(Vaccination.vaccination_date)
    )
    
    trends = [
        DailyTrendItem(date=str(row.vaccination_date), count=row.count)
        for row in result.all()
    ]
    
    return DailyTrendResponse(
        facility_id=facility_id,
        start_date=str(start_date),
        end_date=str(end_date),
        trends=trends
    )


@router.get("/facility/{facility_id}/weekly", response_model=WeeklyTrendResponse)
async def get_facility_weekly_trends(
    facility_id: int,
    weeks: int = Query(4, ge=1, le=52),
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get weekly vaccination trends for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    start_date = date.today() - timedelta(weeks=weeks)
    
    # PostgreSQL DATE_TRUNC for week
    result = await db.execute(
        select(
            func.date_trunc('week', Vaccination.vaccination_date).label('week_start'),
            func.count(Vaccination.id).label('count')
        ).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date >= start_date
            )
        ).group_by(func.date_trunc('week', Vaccination.vaccination_date))
        .order_by(func.date_trunc('week', Vaccination.vaccination_date))
    )
    
    weekly_data = result.all()
    
    trends = [
        {
            "week_start": str(row.week_start.date()),
            "count": row.count
        }
        for row in weekly_data
    ]
    
    return WeeklyTrendResponse(
        facility_id=facility_id,
        weeks=weeks,
        trends=trends
    )


@router.get("/facility/{facility_id}/monthly", response_model=MonthlyTrendResponse)
async def get_facility_monthly_trends(
    facility_id: int,
    months: int = Query(12, ge=1, le=24),
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get monthly vaccination trends for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    start_date = date.today() - timedelta(days=months * 30)
    
    # PostgreSQL DATE_TRUNC for month
    result = await db.execute(
        select(
            func.date_trunc('month', Vaccination.vaccination_date).label('month_start'),
            func.count(Vaccination.id).label('count')
        ).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date >= start_date
            )
        ).group_by(func.date_trunc('month', Vaccination.vaccination_date))
        .order_by(func.date_trunc('month', Vaccination.vaccination_date))
    )
    
    monthly_data = result.all()
    
    trends = [
        {
            "month_start": str(row.month_start.date()),
            "count": row.count
        }
        for row in monthly_data
    ]
    
    return MonthlyTrendResponse(
        facility_id=facility_id,
        months=months,
        trends=trends
    )


@router.get("/facility/{facility_id}/vaccine-distribution", response_model=VaccineDistributionResponse)
async def get_facility_vaccine_distribution(
    facility_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vaccine distribution for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    try:
        result = await db.execute(
            select(
                VaccineMaster.vaccine_name,
                func.count(Vaccination.id).label('count')
            ).join(
                Vaccination, Vaccination.vaccine_id == VaccineMaster.id
            ).where(
                and_(
                    Vaccination.facility_id == facility_id,
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date >= start_date,
                    Vaccination.vaccination_date <= end_date
                )
            ).group_by(VaccineMaster.id, VaccineMaster.vaccine_name)
            .order_by(func.count(Vaccination.id).desc())
        )
        
        vaccine_data = result.all()
        total_vaccinations = sum(row.count for row in vaccine_data) if vaccine_data else 0
        
        distribution = []
        for row in vaccine_data:
            percentage = (row.count / total_vaccinations * 100) if total_vaccinations > 0 else 0
            distribution.append(VaccineDistributionItem(
                vaccine_name=row.vaccine_name,
                count=row.count,
                percentage=round(percentage, 2)
            ))
        
        return VaccineDistributionResponse(
            facility_id=facility_id,
            start_date=str(start_date),
            end_date=str(end_date),
            total_vaccinations=total_vaccinations,
            distribution=distribution
        )
    except Exception as e:
        logger.error(f"Error getting vaccine distribution for facility {facility_id}: {e}")
        # Return empty distribution instead of failing
        return VaccineDistributionResponse(
            facility_id=facility_id,
            start_date=str(start_date),
            end_date=str(end_date),
            total_vaccinations=0,
            distribution=[]
        )


@router.get("/facility/{facility_id}/today-activity", response_model=TodayActivityResponse)
async def get_facility_today_activity(
    facility_id: int,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get today's vaccination activity for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    today = date.today()
    
    # Get vaccinations with beneficiary/child info
    result = await db.execute(
        select(
            Vaccination,
            Beneficiary,
            ChildProfile
        ).outerjoin(
            Beneficiary, Vaccination.beneficiary_id == Beneficiary.id
        ).outerjoin(
            ChildProfile, Vaccination.child_id == ChildProfile.id
        ).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.vaccination_date == today
            )
        ).order_by(Vaccination.vaccination_time.desc() if Vaccination.vaccination_time else Vaccination.created_at.desc())
    )
    
    activities = []
    for row in result.all():
        vaccination = row[0]
        beneficiary = row[1]
        child = row[2]
        
        # Determine name and age
        if child:
            child_name = f"{child.first_name} {child.last_name or ''}".strip()
            # Calculate age
            if child.date_of_birth:
                age_days = (today - child.date_of_birth).days
                if age_days < 30:
                    age = f"{age_days} days"
                elif age_days < 365:
                    age = f"{age_days // 30} months"
                else:
                    age = f"{age_days // 365} years"
            else:
                age = "Unknown"
        elif beneficiary:
            child_name = beneficiary.full_name or "Unknown"
            if beneficiary.date_of_birth:
                age_days = (today - beneficiary.date_of_birth).days
                if age_days < 30:
                    age = f"{age_days} days"
                elif age_days < 365:
                    age = f"{age_days // 30} months"
                else:
                    age = f"{age_days // 365} years"
            else:
                age = "Unknown"
        else:
            child_name = "Unknown"
            age = "Unknown"
        
        activities.append(TodayActivityItem(
            child_name=child_name,
            age=age,
            vaccine_name=vaccination.vaccine_name,
            doctor=vaccination.administered_by,
            status=vaccination.status.value,
            time=vaccination.vaccination_time.strftime("%H:%M") if vaccination.vaccination_time else None
        ))
    
    return TodayActivityResponse(
        facility_id=facility_id,
        date=str(today),
        activities=activities
    )


@router.get("/facility/{facility_id}/alerts", response_model=AlertsResponse)
async def get_facility_alerts(
    facility_id: int,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alerts for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    alerts = []
    today = date.today()
    
    # Check for missed vaccinations
    missed_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.MISSED
            )
        )
    )
    missed_count = missed_result.scalar() or 0
    
    if missed_count > 0:
        alerts.append(AlertItem(
            type="missed_vaccinations",
            message=f"{missed_count} missed vaccinations",
            severity="error",
            count=missed_count
        ))
    
    # Check for low completion rate
    total_vaccinations_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            Vaccination.facility_id == facility_id
        )
    )
    total_vaccinations = total_vaccinations_result.scalar() or 0
    
    if total_vaccinations > 0:
        completed_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                and_(
                    Vaccination.facility_id == facility_id,
                    Vaccination.status == VaccinationStatus.COMPLETED
                )
            )
        )
        completed_count = completed_result.scalar() or 0
        completion_rate = (completed_count / total_vaccinations) * 100
        
        if completion_rate < 80:
            alerts.append(AlertItem(
                type="low_completion_rate",
                message=f"Low completion rate: {completion_rate:.1f}%",
                severity="warning",
                count=int(completion_rate)
            ))
    
    # Check for high pending queue
    pending_result = await db.execute(
        select(func.count(Vaccination.id)).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.SCHEDULED
            )
        )
    )
    pending_count = pending_result.scalar() or 0
    
    if pending_count > 50:
        alerts.append(AlertItem(
            type="high_pending_queue",
            message=f"High pending queue: {pending_count} vaccinations",
            severity="warning",
            count=pending_count
        ))
    
    return AlertsResponse(
        facility_id=facility_id,
        alerts=alerts
    )


@router.get("/facility/{facility_id}/doctor-performance", response_model=DoctorPerformanceResponse)
async def get_facility_doctor_performance(
    facility_id: int,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get doctor performance for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    today = date.today()
    start_of_month = today.replace(day=1)
    
    # Get doctors for this facility
    doctors_result = await db.execute(
        select(
            User.id,
            User.full_name
        ).join(
            FacilityUser, FacilityUser.user_id == User.id
        ).where(
            and_(
                FacilityUser.facility_id == facility_id,
                FacilityUser.facility_role == "doctor",
                FacilityUser.is_active == True
            )
        )
    )
    
    doctors = []
    for row in doctors_result.all():
        doctor_id = row[0]
        doctor_name = row[1] or "Unknown"
        
        # Vaccinations today
        today_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                and_(
                    Vaccination.facility_id == facility_id,
                    Vaccination.recorded_by_user_id == doctor_id,
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date == today
                )
            )
        )
        vaccinations_today = today_result.scalar() or 0
        
        # Vaccinations this month
        month_result = await db.execute(
            select(func.count(Vaccination.id)).where(
                and_(
                    Vaccination.facility_id == facility_id,
                    Vaccination.recorded_by_user_id == doctor_id,
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date >= start_of_month,
                    Vaccination.vaccination_date <= today
                )
            )
        )
        vaccinations_this_month = month_result.scalar() or 0
        
        doctors.append(DoctorPerformanceItem(
            doctor_name=doctor_name,
            doctor_id=doctor_id,
            vaccinations_today=vaccinations_today,
            vaccinations_this_month=vaccinations_this_month
        ))
    
    return DoctorPerformanceResponse(
        facility_id=facility_id,
        doctors=doctors
    )


@router.get("/facility/{facility_id}/age-groups", response_model=AgeGroupResponse)
async def get_facility_age_group_analytics(
    facility_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get age group analytics for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Age groups
    age_groups = [
        ("Birth - 6 weeks", 0, 42),
        ("6 - 14 weeks", 42, 98),
        ("6 - 9 months", 180, 270),
        ("9 - 12 months", 270, 365),
        ("1 - 5 years", 365, 1825),
    ]
    
    age_group_data = []
    
    for age_group_name, min_days, max_days in age_groups:
        min_birth_date = end_date - timedelta(days=max_days)
        max_birth_date = end_date - timedelta(days=min_days)
        
        result = await db.execute(
            select(func.count(Vaccination.id)).join(
                ChildProfile, Vaccination.child_id == ChildProfile.id
            ).where(
                and_(
                    Vaccination.facility_id == facility_id,
                    Vaccination.status == VaccinationStatus.COMPLETED,
                    Vaccination.vaccination_date >= start_date,
                    Vaccination.vaccination_date <= end_date,
                    ChildProfile.date_of_birth >= min_birth_date,
                    ChildProfile.date_of_birth <= max_birth_date
                )
            )
        )
        count = result.scalar() or 0
        
        age_group_data.append(AgeGroupItem(
            age_group=age_group_name,
            count=count
        ))
    
    return AgeGroupResponse(
        facility_id=facility_id,
        age_groups=age_group_data
    )


@router.get("/facility/{facility_id}/missed-analytics", response_model=MissedVaccinationAnalytics)
async def get_facility_missed_vaccination_analytics(
    facility_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get missed vaccination analytics for a facility
    """
    current_user, facility_user = user_facility
    
    if not await is_super_admin(current_user, db):
        if facility_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view analytics for your own facility"
            )
    
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get missed vaccinations trend
    missed_result = await db.execute(
        select(
            Vaccination.vaccination_date,
            func.count(Vaccination.id).label('count')
        ).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.MISSED,
                Vaccination.vaccination_date >= start_date,
                Vaccination.vaccination_date <= end_date
            )
        ).group_by(Vaccination.vaccination_date)
        .order_by(Vaccination.vaccination_date)
    )
    
    missed_trend = [
        {"date": str(row.vaccination_date), "count": row.count}
        for row in missed_result.all()
    ]
    
    # Get completed vaccinations trend
    completed_result = await db.execute(
        select(
            Vaccination.vaccination_date,
            func.count(Vaccination.id).label('count')
        ).where(
            and_(
                Vaccination.facility_id == facility_id,
                Vaccination.status == VaccinationStatus.COMPLETED,
                Vaccination.vaccination_date >= start_date,
                Vaccination.vaccination_date <= end_date
            )
        ).group_by(Vaccination.vaccination_date)
        .order_by(Vaccination.vaccination_date)
    )
    
    completed_trend = [
        {"date": str(row.vaccination_date), "count": row.count}
        for row in completed_result.all()
    ]
    
    # Calculate totals and percentage
    total_missed = sum(item["count"] for item in missed_trend)
    total_completed = sum(item["count"] for item in completed_trend)
    total_all = total_missed + total_completed
    delayed_percentage = (total_missed / total_all * 100) if total_all > 0 else 0
    
    return MissedVaccinationAnalytics(
        facility_id=facility_id,
        total_missed=total_missed,
        delayed_percentage=round(delayed_percentage, 2),
        missed_trend=[DailyTrendItem(**item) for item in missed_trend],
        completed_trend=[DailyTrendItem(**item) for item in completed_trend]
    )


@router.get("/global/daily")
async def get_global_daily_analytics(
    date_filter: Optional[date] = Query(None, alias="date"),
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily vaccination analytics across all facilities (SUPER_ADMIN only)
    """
    target_date = date_filter or date.today()
    
    # Get facility-wise vaccinations for the date
    result = await db.execute(
        select(
            Facility.facility_id,
            Facility.name,
            func.count(Vaccination.id).label('count')
        ).join(
            Vaccination, Vaccination.facility_id == Facility.id
        ).where(
            and_(
                Vaccination.vaccination_date == target_date,
                Vaccination.status == VaccinationStatus.COMPLETED,
                Facility.is_active == True
            )
        ).group_by(Facility.id, Facility.facility_id, Facility.name)
        .order_by(func.count(Vaccination.id).desc())
    )
    
    facility_data = result.all()
    
    total_today = sum(row.count for row in facility_data)
    
    return {
        "date": str(target_date),
        "total_vaccinations": total_today,
        "facilities_active": len(facility_data),
        "by_facility": [
            {
                "facility_id": row.facility_id,
                "facility_name": row.name,
                "vaccinations": row.count
            }
            for row in facility_data
        ]
    }
