"""
Vaccination Timeline Service
Calculates age-based vaccination timeline for child beneficiaries
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import logging

from app.models.beneficiary import Beneficiary, BeneficiaryType
from app.models.vaccine_master import VaccineMaster
from app.models.vaccination import Vaccination, VaccinationStatus

logger = logging.getLogger(__name__)


class VaccinationTimelineService:
    """Service for calculating vaccination timelines based on age"""
    
    # Grace period for upcoming vaccinations (days)
    GRACE_PERIOD_DAYS = 14  # 2 weeks grace period after due date
    UPCOMING_WINDOW_DAYS = 30  # Show as upcoming if within 30 days
    
    # Birth dose vaccines that should NOT show date ranges
    BIRTH_DOSE_VACCINES = [
        'bcg',
        'opv-0',
        'opv0',
        'hepatitis b',
        'hepb',
        'hepatitis-b'
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def is_birth_dose_vaccine(self, vaccine_name: str, age_string: str) -> bool:
        """
        Check if a vaccine is a birth dose vaccine
        Birth doses: BCG, OPV-0, Hepatitis B (Birth Dose)
        """
        vaccine_lower = vaccine_name.lower().strip()
        age_lower = age_string.lower().strip()
        
        # Check if age is "at birth" or "0"
        is_birth_age = "birth" in age_lower or age_lower == "0" or age_lower == "zero"
        
        # Check if vaccine name matches birth dose vaccines
        is_birth_vaccine = any(birth_vax in vaccine_lower for birth_vax in self.BIRTH_DOSE_VACCINES)
        
        # Also check for dose 0 or zero dose
        is_zero_dose = "dose 0" in vaccine_lower or "dose-0" in vaccine_lower or "zero dose" in vaccine_lower
        
        return is_birth_age or (is_birth_vaccine and is_zero_dose) or is_zero_dose
    
    def calculate_age_in_weeks(self, dob: date, reference_date: Optional[date] = None) -> int:
        """Calculate age in weeks from date of birth"""
        if reference_date is None:
            reference_date = date.today()
        delta = reference_date - dob
        return delta.days // 7
    
    def calculate_age_in_days(self, dob: date, reference_date: Optional[date] = None) -> int:
        """Calculate age in days from date of birth"""
        if reference_date is None:
            reference_date = date.today()
        delta = reference_date - dob
        return delta.days
    
    def parse_age_to_days(self, age_string: str) -> int:
        """
        Parse age string to days
        Examples: "At birth" -> 0, "6 weeks" -> 42, "9 months" -> 270, "5 years" -> 1825
        """
        age_lower = age_string.lower().strip()
        
        # At birth
        if "birth" in age_lower or age_lower == "0":
            return 0
        
        # Weeks
        import re
        weeks_match = re.search(r'(\d+)\s*week', age_lower)
        if weeks_match:
            return int(weeks_match.group(1)) * 7
        
        # Months (approximate: 30 days per month)
        months_match = re.search(r'(\d+)\s*month', age_lower)
        if months_match:
            return int(months_match.group(1)) * 30
        
        # Years
        years_match = re.search(r'(\d+)\s*year', age_lower)
        if years_match:
            return int(years_match.group(1)) * 365
        
        return 0
    
    def _get_vaccine_window_days(self, age_string: str, vaccine_name: str) -> int:
        """
        Get the vaccination window in days based on WHO/Indian standards
        Returns the number of days after the due date that the vaccine can still be given
        """
        age_lower = age_string.lower().strip()
        vaccine_lower = vaccine_name.lower()
        
        # At birth vaccines (BCG, OPV-0, Hepatitis B-0) - can be given up to 1 year
        if "birth" in age_lower or age_lower == "0":
            if "bcg" in vaccine_lower:
                return 365  # BCG can be given up to 1 year
            return 30  # Other birth vaccines: 1 month window
        
        # Early vaccines (6-14 weeks) - typically 4 week window
        if "week" in age_lower:
            weeks = int(age_lower.split()[0]) if age_lower.split()[0].isdigit() else 0
            if weeks <= 14:
                return 28  # 4 week window for early vaccines
        
        # 6 months vaccines - 4 week window
        if "6" in age_lower and "month" in age_lower:
            return 28
        
        # 9 months vaccines (MMR, etc.) - 4 week window
        if "9" in age_lower and "month" in age_lower:
            return 28
        
        # 12-15 months vaccines - 4 week window
        if "12" in age_lower or "15" in age_lower or "18" in age_lower:
            if "month" in age_lower:
                return 28
        
        # 2-5 years vaccines - 1 month window
        if "year" in age_lower:
            return 30
        
        # Default: 4 week window
        return 28
    
    def determine_status(
        self,
        has_vaccination: bool,
        current_age_days: int,
        due_age_days: int
    ) -> str:
        """
        Determine vaccination status:
        - COMPLETED: vaccination record exists
        - UPCOMING: current_age >= due_age AND within grace period
        - DUE_NEXT: current_age < due_age (future vaccinations)
        """
        if has_vaccination:
            return "COMPLETED"
        
        # Check if due and within grace period
        if current_age_days >= due_age_days:
            days_overdue = current_age_days - due_age_days
            if days_overdue <= self.GRACE_PERIOD_DAYS:
                return "UPCOMING"
            # Past grace period but still show as upcoming if within window
            if days_overdue <= self.UPCOMING_WINDOW_DAYS:
                return "UPCOMING"
        
        # Check if upcoming (within window before due)
        days_until_due = due_age_days - current_age_days
        if 0 <= days_until_due <= self.UPCOMING_WINDOW_DAYS:
            return "UPCOMING"
        
        # Due Next (Future)
        if current_age_days < due_age_days:
            return "DUE_NEXT"
        
        # Default to due next
        return "DUE_NEXT"
    
    def status_to_color(self, status: str) -> str:
        """Map status to color"""
        status_map = {
            "COMPLETED": "GREEN",
            "UPCOMING": "ORANGE",
            "DUE_NEXT": "GREY",
            "FUTURE": "GREY"  # Backward compatibility
        }
        return status_map.get(status, "GREY")
    
    async def get_child_timeline(
        self,
        beneficiary_id: int
    ) -> Dict:
        """
        Get vaccination timeline for a beneficiary (CHILD or ADULT)
        
        Returns timeline with status and color for each scheduled vaccine
        """
        # Get beneficiary (both CHILD and ADULT are supported)
        result = await self.db.execute(
            select(Beneficiary).where(
                and_(
                    Beneficiary.id == beneficiary_id,
                    Beneficiary.is_active == True
                )
            )
        )
        beneficiary = result.scalar_one_or_none()
        
        if not beneficiary:
            raise ValueError(f"Beneficiary not found: {beneficiary_id}")
        
        # Get all vaccines (mandatory and recommended for children)
        vaccines_result = await self.db.execute(
            select(VaccineMaster).where(
                VaccineMaster.is_active == True
            )
        )
        vaccines = vaccines_result.scalars().all()
        
        # Get recorded vaccinations for this child (check both beneficiary_id and legacy child_id)
        # First, get beneficiary to find legacy_child_profile_id if exists
        beneficiary_result = await self.db.execute(
            select(Beneficiary).where(Beneficiary.id == beneficiary_id)
        )
        beneficiary = beneficiary_result.scalar_one_or_none()
        
        # Build query to get vaccinations
        vaccination_query = select(Vaccination).where(
            and_(
                Vaccination.is_active == True
            )
        )
        
        # Check both beneficiary_id and legacy child_id
        if beneficiary and beneficiary.legacy_child_profile_id:
            vaccination_query = vaccination_query.where(
                or_(
                    Vaccination.beneficiary_id == beneficiary_id,
                    Vaccination.child_id == beneficiary.legacy_child_profile_id
                )
            )
        else:
            vaccination_query = vaccination_query.where(
                Vaccination.beneficiary_id == beneficiary_id
            )
        
        vaccinations_result = await self.db.execute(vaccination_query)
        recorded_vaccinations = vaccinations_result.scalars().all()
        
        # Create map of recorded vaccinations with flexible matching
        vaccination_map = {}
        for vax in recorded_vaccinations:
            # Normalize vaccine name (lowercase, strip spaces)
            normalized_name = vax.vaccine_name.lower().strip()
            # Create multiple keys for flexible matching
            key1 = f"{normalized_name}_dose_{vax.dose_number}"
            key2 = f"{normalized_name.replace(' ', '_')}_dose_{vax.dose_number}"
            key3 = f"{normalized_name.replace('-', '_')}_dose_{vax.dose_number}"
            # Store with all possible keys
            vaccination_map[key1] = vax
            vaccination_map[key2] = vax
            vaccination_map[key3] = vax
        
        # Calculate child's current age
        current_date = date.today()
        current_age_days = self.calculate_age_in_days(beneficiary.date_of_birth, current_date)
        current_age_weeks = self.calculate_age_in_weeks(beneficiary.date_of_birth, current_date)
        
        # Build timeline
        timeline_items = []
        
        for vaccine in vaccines:
            # Skip if not applicable for children (can add filter later)
            
            # Get dosage schedule
            schedule = vaccine.dosage_schedule or {}
            
            # Process vaccines with dosage schedule
            if schedule and len(schedule) > 0:
                # Process each dose in schedule
                for dose_key, age_string in schedule.items():
                    # Extract dose number
                    import re
                    dose_match = re.search(r'dose[_\s]*(\d+)', dose_key.lower()) or re.search(r'(\d+)', dose_key)
                    dose_number = int(dose_match.group(1)) if dose_match else 1
                    
                    # Calculate due age in days
                    due_age_days = self.parse_age_to_days(age_string)
                    
                    # Check if vaccination exists (with flexible matching)
                    normalized_vaccine_name = vaccine.vaccine_name.lower().strip()
                    vax_key1 = f"{normalized_vaccine_name}_dose_{dose_number}"
                    vax_key2 = f"{normalized_vaccine_name.replace(' ', '_')}_dose_{dose_number}"
                    vax_key3 = f"{normalized_vaccine_name.replace('-', '_')}_dose_{dose_number}"
                    
                    # Try multiple keys to find vaccination
                    recorded_vax = None
                    has_vaccination = False
                    for key in [vax_key1, vax_key2, vax_key3]:
                        if key in vaccination_map:
                            recorded_vax = vaccination_map[key]
                            has_vaccination = True
                            break
                    
                    # Also try fuzzy matching by vaccine name only (in case dose numbers don't match)
                    if not has_vaccination:
                        for vax in recorded_vaccinations:
                            if vax.vaccine_name.lower().strip() == normalized_vaccine_name:
                                recorded_vax = vax
                                has_vaccination = True
                                break
                    
                    # Determine status
                    status = self.determine_status(has_vaccination, current_age_days, due_age_days)
                    color = self.status_to_color(status)
                    
                    # Check if this is a birth dose vaccine
                    is_birth_dose = self.is_birth_dose_vaccine(vaccine.vaccine_name, age_string)
                    
                    # Calculate due date
                    due_date = beneficiary.date_of_birth + timedelta(days=due_age_days)
                    
                    # For birth doses, do NOT calculate date ranges
                    if is_birth_dose:
                        start_date = None
                        end_date = None
                    else:
                        # Calculate date range window based on vaccine type and age
                        # WHO/Indian standards: Most vaccines have a 1-4 week window
                        window_days = self._get_vaccine_window_days(age_string, vaccine.vaccine_name)
                        start_date = due_date
                        end_date = due_date + timedelta(days=window_days)
                    
                    # Format dose label for birth doses
                    if is_birth_dose:
                        if dose_number == 0 or "zero" in age_string.lower() or "0" in age_string.lower():
                            dose_label = "Zero Dose (Birth Dose)"
                        else:
                            dose_label = "Birth Dose"
                    else:
                        dose_label = f"Dose {dose_number}"
                    
                    timeline_items.append({
                        "vaccine_name": vaccine.vaccine_name,
                        "vaccine_code": vaccine.vaccine_code,
                        "dose": dose_label,
                        "dose_number": dose_number,
                        "due_age": age_string,
                        "due_age_days": due_age_days,
                        "due_date": due_date.isoformat(),
                        "date_range_start": start_date.isoformat() if start_date else None,
                        "date_range_end": end_date.isoformat() if end_date else None,
                        "status": status,
                        "color": color,
                        "vaccinated_on": recorded_vax.vaccination_date.isoformat() if recorded_vax else None,
                        "vaccination_id": recorded_vax.id if recorded_vax else None,
                        "is_birth_dose": is_birth_dose
                    })
            elif vaccine.recommended_age_start:
                # Single dose vaccine with recommended age
                due_age_days = self.parse_age_to_days(vaccine.recommended_age_start)
                
                # Check if vaccination exists (with flexible matching)
                normalized_vaccine_name = vaccine.vaccine_name.lower().strip()
                vax_key1 = f"{normalized_vaccine_name}_dose_1"
                vax_key2 = f"{normalized_vaccine_name.replace(' ', '_')}_dose_1"
                vax_key3 = f"{normalized_vaccine_name.replace('-', '_')}_dose_1"
                
                # Try multiple keys to find vaccination
                recorded_vax = None
                has_vaccination = False
                for key in [vax_key1, vax_key2, vax_key3]:
                    if key in vaccination_map:
                        recorded_vax = vaccination_map[key]
                        has_vaccination = True
                        break
                
                # Also try fuzzy matching by vaccine name only
                if not has_vaccination:
                    for vax in recorded_vaccinations:
                        if vax.vaccine_name.lower().strip() == normalized_vaccine_name:
                            recorded_vax = vax
                            has_vaccination = True
                            break
                
                # Determine status
                status = self.determine_status(has_vaccination, current_age_days, due_age_days)
                color = self.status_to_color(status)
                
                # Check if this is a birth dose vaccine
                is_birth_dose = self.is_birth_dose_vaccine(vaccine.vaccine_name, vaccine.recommended_age_start)
                
                # Calculate due date
                due_date = beneficiary.date_of_birth + timedelta(days=due_age_days)
                
                # For birth doses, do NOT calculate date ranges
                if is_birth_dose:
                    start_date = None
                    end_date = None
                else:
                    # Calculate date range window
                    window_days = self._get_vaccine_window_days(vaccine.recommended_age_start, vaccine.vaccine_name)
                    start_date = due_date
                    end_date = due_date + timedelta(days=window_days)
                
                # Format dose label for birth doses
                if is_birth_dose:
                    dose_label = "Birth Dose"
                else:
                    dose_label = "Dose 1"
                
                timeline_items.append({
                    "vaccine_name": vaccine.vaccine_name,
                    "vaccine_code": vaccine.vaccine_code,
                    "dose": dose_label,
                    "dose_number": 1,
                    "due_age": vaccine.recommended_age_start,
                    "due_age_days": due_age_days,
                    "due_date": due_date.isoformat(),
                    "date_range_start": start_date.isoformat() if start_date else None,
                    "date_range_end": end_date.isoformat() if end_date else None,
                    "status": status,
                    "color": color,
                    "vaccinated_on": recorded_vax.vaccination_date.isoformat() if recorded_vax else None,
                    "vaccination_id": recorded_vax.id if recorded_vax else None,
                    "is_birth_dose": is_birth_dose
                })
        
        # Sort by due_age_days
        timeline_items.sort(key=lambda x: x["due_age_days"])
        
        # Get upcoming reminders
        reminders = self.get_upcoming_reminders(timeline_items, current_date)
        
        return {
            "child": {
                "id": beneficiary.id,
                "name": beneficiary.full_name,
                "dob": beneficiary.date_of_birth.isoformat(),
                "age_weeks": current_age_weeks,
                "age_days": current_age_days
            },
            "timeline": timeline_items,
            "reminders": reminders
        }
    
    def get_upcoming_reminders(
        self,
        timeline_items: List[Dict],
        current_date: date,
        days_ahead: int = 14
    ) -> List[Dict]:
        """
        Get reminders for upcoming vaccinations within next X days
        """
        reminders = []
        target_date = current_date + timedelta(days=days_ahead)
        
        for item in timeline_items:
            # Skip birth dose vaccines from reminders (they're event-based, not scheduled)
            if item.get("is_birth_dose", False):
                continue
                
            if item["status"] == "UPCOMING" or item["status"] == "DUE_NEXT" or item["status"] == "FUTURE":
                due_date = datetime.fromisoformat(item["due_date"]).date()
                
                # Check if within reminder window
                if current_date <= due_date <= target_date:
                    days_remaining = (due_date - current_date).days
                    reminders.append({
                        "vaccine_name": item["vaccine_name"],
                        "dose": item["dose"],
                        "due_date": item["due_date"],
                        "due_age": item["due_age"],
                        "days_remaining": days_remaining,
                        "status": item["status"],
                        "color": item["color"]
                    })
        
        # Sort by days remaining
        reminders.sort(key=lambda x: x["days_remaining"])
        return reminders

