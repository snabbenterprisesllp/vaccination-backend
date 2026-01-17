"""Child profile service"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import uuid
import logging
from datetime import datetime, timedelta

from app.models.child_profile import ChildProfile
from app.models.user import User
from app.models.vaccination import Vaccination, VaccinationSchedule
from app.schemas.child_profile import (
    ChildProfileCreate, 
    ChildProfileUpdate,
    VaccinationSummary,
    VaccineSummary,
    ScheduleSummary
)
from app.core.config import settings
from app.services.qr_service import QRCodeService
from datetime import date

logger = logging.getLogger(__name__)


class ChildProfileService:
    """Child profile management service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.qr_service = QRCodeService()
    
    async def create_profile(
        self,
        user: User,
        profile_data: ChildProfileCreate
    ) -> ChildProfile:
        """Create a new child profile"""
        # Generate unique QR token
        qr_token = str(uuid.uuid4())
        
        # Create profile
        profile = ChildProfile(
            parent_id=user.id,
            **profile_data.model_dump(),
            qr_code_token=qr_token
        )
        
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        
        # Create corresponding beneficiary record
        try:
            from app.models.beneficiary import Beneficiary, BeneficiaryType
            from app.models.beneficiary import Gender as BeneficiaryGender
            
            # Map child profile gender to beneficiary gender
            gender_map = {
                'male': BeneficiaryGender.MALE,
                'female': BeneficiaryGender.FEMALE,
                'other': BeneficiaryGender.OTHER
            }
            beneficiary_gender = gender_map.get(profile.gender.value if hasattr(profile.gender, 'value') else str(profile.gender), BeneficiaryGender.OTHER)
            
            beneficiary = Beneficiary(
                account_id=user.id,
                type=BeneficiaryType.CHILD,
                first_name=profile.first_name,
                middle_name=profile.middle_name,
                last_name=profile.last_name,
                date_of_birth=profile.date_of_birth,
                gender=beneficiary_gender,
                abha_id=profile.abha_number,
                abha_address=profile.abha_address,
                abha_linked=profile.abha_linked if profile.abha_linked is not None else False,
                abha_linked_at=profile.abha_linked_at,
                qr_code_url=profile.qr_code_url,
                qr_code_token=profile.qr_code_token,
                legacy_child_profile_id=profile.id
            )
            self.db.add(beneficiary)
            await self.db.commit()
            await self.db.refresh(beneficiary)
            logger.info(f"Created beneficiary {beneficiary.id} for child profile {profile.id}")
        except Exception as e:
            # Log but don't fail child creation if beneficiary creation fails
            logger.warning(f"Failed to create beneficiary for child {profile.id}: {e}. Child profile created successfully.")
        
        # Generate QR code (optional - won't fail if GCS is not available)
        # Only store real URLs (not base64 data URLs) to avoid database column size issues
        try:
            qr_url = await self.qr_service.generate_qr_code(
                data=qr_token,
                child_id=profile.id
            )
            # Only store if it's a real URL (not a base64 data URL)
            if qr_url and not qr_url.startswith('data:'):
                profile.qr_code_url = qr_url
                await self.db.commit()
                await self.db.refresh(profile)
            elif qr_url:
                # Base64 data URL - don't store in DB, can be generated on-the-fly from token
                logger.info(f"QR code generated as base64 for child {profile.id} (not stored in DB)")
        except Exception as e:
            # Log but don't fail child creation if QR generation fails
            logger.warning(f"QR code generation failed for child {profile.id}: {e}. Continuing without QR code.")
        
        return profile
    
    async def get_profile_by_id(
        self,
        profile_id: int,
        user: User
    ) -> Optional[ChildProfile]:
        """Get child profile by ID"""
        result = await self.db.execute(
            select(ChildProfile).where(
                and_(
                    ChildProfile.id == profile_id,
                    ChildProfile.parent_id == user.id,
                    ChildProfile.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_profiles(self, user: User) -> List[ChildProfile]:
        """Get all profiles for a user"""
        result = await self.db.execute(
            select(ChildProfile).where(
                and_(
                    ChildProfile.parent_id == user.id,
                    ChildProfile.is_active == True
                )
            ).order_by(ChildProfile.date_of_birth.desc())
        )
        return list(result.scalars().all())
    
    async def update_profile(
        self,
        profile_id: int,
        user: User,
        update_data: ChildProfileUpdate
    ) -> Optional[ChildProfile]:
        """Update child profile"""
        profile = await self.get_profile_by_id(profile_id, user)
        if not profile:
            return None
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile
    
    async def delete_profile(
        self,
        profile_id: int,
        user: User
    ) -> bool:
        """Soft delete child profile and corresponding beneficiary"""
        profile = await self.get_profile_by_id(profile_id, user)
        if not profile:
            return False
        
        # Soft delete child profile
        profile.is_active = False
        
        # Also soft delete corresponding beneficiary if exists
        from app.models.beneficiary import Beneficiary
        beneficiary_result = await self.db.execute(
            select(Beneficiary).where(
                and_(
                    Beneficiary.legacy_child_profile_id == profile_id,
                    Beneficiary.is_active == True
                )
            )
        )
        beneficiary = beneficiary_result.scalar_one_or_none()
        if beneficiary:
            beneficiary.is_active = False
            logger.info(f"Soft deleted beneficiary {beneficiary.id} for child profile {profile_id}")
        
        await self.db.commit()
        
        return True
    
    async def get_profile_by_qr_token(self, qr_token: str) -> Optional[ChildProfile]:
        """Get profile by QR code token"""
        result = await self.db.execute(
            select(ChildProfile).where(
                and_(
                    ChildProfile.qr_code_token == qr_token,
                    ChildProfile.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def regenerate_qr_code(
        self,
        profile_id: int,
        user: User
    ) -> Optional[ChildProfile]:
        """Regenerate QR code for profile"""
        profile = await self.get_profile_by_id(profile_id, user)
        if not profile:
            return None
        
        # Generate new token
        qr_token = str(uuid.uuid4())
        profile.qr_code_token = qr_token
        
        # Generate new QR code
        qr_url = await self.qr_service.generate_qr_code(
            data=qr_token,
            child_id=profile.id
        )
        # Only store if it's a real URL (not a base64 data URL)
        if qr_url and not qr_url.startswith('data:'):
            profile.qr_code_url = qr_url
        elif qr_url:
            # Base64 data URL - clear existing URL since we can't store it
            profile.qr_code_url = None
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile
    
    async def get_vaccination_summary(self, child_id: int) -> VaccinationSummary:
        """Get vaccination summary for QR scan (public-safe data only)"""
        # Get all vaccinations (completed, scheduled, etc.)
        from sqlalchemy import select, and_
        
        result = await self.db.execute(
            select(Vaccination).where(
                and_(
                    Vaccination.child_id == child_id,
                    Vaccination.is_active == True
                )
            ).order_by(Vaccination.vaccination_date.desc())
        )
        vaccinations = list(result.scalars().all())
        
        # Filter completed vaccinations for summary
        completed_vaccinations = [v for v in vaccinations if str(v.status) == 'completed' or (hasattr(v.status, 'value') and v.status.value == 'completed')]
        
        # Build summary (public-safe fields only) - show all vaccinations
        vaccines_received = [
            VaccineSummary(
                vaccine_name=v.vaccine_name,
                dose_number=v.dose_number,
                vaccination_date=v.vaccination_date,
                status=v.status.value if hasattr(v.status, 'value') else str(v.status)
            )
            for v in vaccinations
        ]
        
        # Get last completed vaccination date
        last_vaccination_date = completed_vaccinations[0].vaccination_date if completed_vaccinations else None
        
        return VaccinationSummary(
            total_count=len(completed_vaccinations),  # Count only completed
            last_vaccination_date=last_vaccination_date,
            vaccines_received=vaccines_received  # But show all in list
        )
    
    async def get_upcoming_schedules(self, child_id: int) -> List[ScheduleSummary]:
        """Get upcoming vaccination schedules for QR scan"""
        from sqlalchemy import select, and_
        result = await self.db.execute(
            select(VaccinationSchedule).where(
                and_(
                    VaccinationSchedule.child_id == child_id,
                    VaccinationSchedule.is_active == True,
                    VaccinationSchedule.completed == False,
                    VaccinationSchedule.due_date >= date.today()
                )
            ).order_by(VaccinationSchedule.due_date)
        )
        schedules = list(result.scalars().all())
        
        return [
            ScheduleSummary(
                vaccine_name=s.vaccine_name,
                dose_number=s.dose_number,
                due_date=s.due_date,
                scheduled_date=s.due_date  # Using due_date as scheduled_date
            )
            for s in schedules
        ]

