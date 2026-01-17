"""Beneficiary service"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import uuid
import logging
from datetime import datetime

from app.models.beneficiary import Beneficiary, BeneficiaryType, Gender
from app.models.user import User
from app.models.vaccination import Vaccination, VaccinationSchedule
from app.schemas.beneficiary import (
    BeneficiaryCreate,
    BeneficiaryUpdate,
    BeneficiaryResponse,
    ParentProfileResponse
)
from app.core.config import settings
from app.services.qr_service import QRCodeService

logger = logging.getLogger(__name__)


class BeneficiaryService:
    """Beneficiary management service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.qr_service = QRCodeService()
    
    async def create_beneficiary(
        self,
        user: User,
        beneficiary_data: BeneficiaryCreate
    ) -> Beneficiary:
        """Create a new beneficiary"""
        # Generate unique QR token if needed
        qr_token = str(uuid.uuid4()) if beneficiary_data.type == BeneficiaryType.CHILD else None
        
        # Create beneficiary
        beneficiary = Beneficiary(
            account_id=user.id,
            **beneficiary_data.model_dump(),
            qr_code_token=qr_token
        )
        
        self.db.add(beneficiary)
        await self.db.commit()
        await self.db.refresh(beneficiary)
        
        # Generate QR code for children (optional)
        if beneficiary.type == BeneficiaryType.CHILD and qr_token:
            try:
                qr_url = await self.qr_service.generate_qr_code(
                    data=qr_token,
                    child_id=beneficiary.id  # Using beneficiary id
                )
                if qr_url and not qr_url.startswith('data:'):
                    beneficiary.qr_code_url = qr_url
                    await self.db.commit()
                    await self.db.refresh(beneficiary)
            except Exception as e:
                logger.warning(f"QR code generation failed for beneficiary {beneficiary.id}: {e}")
        
        return beneficiary
    
    async def get_beneficiary_by_id(
        self,
        beneficiary_id: int,
        user: Optional[User] = None
    ) -> Optional[Beneficiary]:
        """Get beneficiary by ID (with optional user check for security)"""
        query = select(Beneficiary).where(
            and_(
                Beneficiary.id == beneficiary_id,
                Beneficiary.is_active == True
            )
        )
        
        # If user provided, ensure they own this beneficiary
        if user:
            query = query.where(Beneficiary.account_id == user.id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_beneficiaries(
        self,
        user: User,
        beneficiary_type: Optional[BeneficiaryType] = None
    ) -> List[Beneficiary]:
        """Get all beneficiaries for a user (optionally filtered by type)"""
        from app.models.child_profile import ChildProfile
        
        query = select(Beneficiary).where(
            and_(
                Beneficiary.account_id == user.id,
                Beneficiary.is_active == True
            )
        )
        
        if beneficiary_type:
            query = query.where(Beneficiary.type == beneficiary_type)
        
        result = await self.db.execute(
            query.order_by(Beneficiary.date_of_birth.desc())
        )
        beneficiaries = list(result.scalars().all())
        
        # For CHILD beneficiaries, sync with child_profiles table
        if beneficiary_type == BeneficiaryType.CHILD:
            # Get all active child profiles for this user
            child_profiles_result = await self.db.execute(
                select(ChildProfile).where(
                    and_(
                        ChildProfile.parent_id == user.id,
                        ChildProfile.is_active == True
                    )
                )
            )
            active_child_profiles = child_profiles_result.scalars().all()
            
            # Create beneficiaries for child profiles that don't have one
            beneficiary_map = {b.legacy_child_profile_id: b for b in beneficiaries if b.legacy_child_profile_id}
            
            for child_profile in active_child_profiles:
                if child_profile.id not in beneficiary_map:
                    # Create missing beneficiary
                    try:
                        from app.models.beneficiary import Gender as BeneficiaryGender
                        gender_map = {
                            'male': BeneficiaryGender.MALE,
                            'female': BeneficiaryGender.FEMALE,
                            'other': BeneficiaryGender.OTHER
                        }
                        beneficiary_gender = gender_map.get(
                            child_profile.gender.value if hasattr(child_profile.gender, 'value') else str(child_profile.gender),
                            BeneficiaryGender.OTHER
                        )
                        
                        new_beneficiary = Beneficiary(
                            account_id=user.id,
                            type=BeneficiaryType.CHILD,
                            first_name=child_profile.first_name,
                            middle_name=child_profile.middle_name,
                            last_name=child_profile.last_name,
                            date_of_birth=child_profile.date_of_birth,
                            gender=beneficiary_gender,
                            abha_id=child_profile.abha_number,
                            abha_address=child_profile.abha_address,
                            abha_linked=child_profile.abha_linked if child_profile.abha_linked is not None else False,
                            abha_linked_at=child_profile.abha_linked_at,
                            qr_code_url=child_profile.qr_code_url,
                            qr_code_token=child_profile.qr_code_token,
                            legacy_child_profile_id=child_profile.id
                        )
                        self.db.add(new_beneficiary)
                        await self.db.commit()
                        await self.db.refresh(new_beneficiary)
                        beneficiaries.append(new_beneficiary)
                        logger.info(f"Created missing beneficiary {new_beneficiary.id} for child profile {child_profile.id}")
                    except Exception as e:
                        logger.warning(f"Failed to create beneficiary for child {child_profile.id}: {e}")
            
            # Filter out beneficiaries whose legacy child profiles are inactive
            filtered_beneficiaries = []
            for beneficiary in beneficiaries:
                if beneficiary.legacy_child_profile_id:
                    # Check if the legacy child profile is still active
                    child_result = await self.db.execute(
                        select(ChildProfile).where(
                            ChildProfile.id == beneficiary.legacy_child_profile_id
                        )
                    )
                    child_profile = child_result.scalar_one_or_none()
                    # Only include if child profile doesn't exist or is active
                    if not child_profile or child_profile.is_active:
                        filtered_beneficiaries.append(beneficiary)
                    else:
                        # Child profile is inactive, also deactivate beneficiary
                        beneficiary.is_active = False
                        await self.db.commit()
                        logger.info(f"Deactivated beneficiary {beneficiary.id} because child profile {beneficiary.legacy_child_profile_id} is inactive")
                else:
                    # No legacy child profile, include it
                    filtered_beneficiaries.append(beneficiary)
            return filtered_beneficiaries
        
        return beneficiaries
    
    async def get_parent_beneficiary(
        self,
        user: User
    ) -> Optional[Beneficiary]:
        """Get or create parent beneficiary for a user"""
        # Try to find existing parent beneficiary
        result = await self.db.execute(
            select(Beneficiary).where(
                and_(
                    Beneficiary.account_id == user.id,
                    Beneficiary.type == BeneficiaryType.ADULT,
                    Beneficiary.is_active == True
                )
            )
        )
        beneficiary = result.scalar_one_or_none()
        
        if not beneficiary:
            # Create parent beneficiary from user data
            # Extract name from user.full_name
            name_parts = (user.full_name or "User").split(" ", 1)
            first_name = name_parts[0] if name_parts else "User"
            last_name = name_parts[1] if len(name_parts) > 1 else "User"  # Use "User" as default if no last name
            
            beneficiary = Beneficiary(
                account_id=user.id,
                type=BeneficiaryType.ADULT,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=datetime.now().date(),  # Default, should be updated
                gender=Gender.OTHER,  # Default, should be updated
                abha_id=user.abha_number,
                abha_address=user.abha_address,
                abha_linked=user.abha_linked,
                abha_linked_at=user.abha_linked_at,
                legacy_user_id=user.id
            )
            
            self.db.add(beneficiary)
            await self.db.commit()
            await self.db.refresh(beneficiary)
        
        return beneficiary
    
    async def get_parent_profile(
        self,
        user: User
    ) -> ParentProfileResponse:
        """Get parent profile with vaccinations"""
        # Get or create parent beneficiary
        beneficiary = await self.get_parent_beneficiary(user)
        
        if not beneficiary:
            raise ValueError("Parent beneficiary not found")
        
        # Get vaccinations for parent
        vaccinations_result = await self.db.execute(
            select(Vaccination).where(
                and_(
                    Vaccination.beneficiary_id == beneficiary.id,
                    Vaccination.is_active == True
                )
            ).order_by(Vaccination.vaccination_date.desc())
        )
        vaccinations = vaccinations_result.scalars().all()
        
        # Convert to dict format
        vaccinations_list = [
            {
                "id": v.id,
                "vaccine_name": v.vaccine_name,
                "dose_number": v.dose_number,
                "vaccination_date": v.vaccination_date.isoformat() if v.vaccination_date else None,
                "status": v.status.value if v.status else None,
                "hospital_id": v.hospital_id,
            }
            for v in vaccinations
        ]
        
        return ParentProfileResponse(
            beneficiary=BeneficiaryResponse.model_validate(beneficiary),
            vaccinations=vaccinations_list
        )
    
    async def get_beneficiary_vaccinations(
        self,
        beneficiary_id: int,
        user: Optional[User] = None
    ) -> List[dict]:
        """Get all vaccinations for a beneficiary"""
        # Verify beneficiary belongs to user if provided
        beneficiary = await self.get_beneficiary_by_id(beneficiary_id, user)
        if not beneficiary:
            return []
        
        result = await self.db.execute(
            select(Vaccination).where(
                and_(
                    Vaccination.beneficiary_id == beneficiary_id,
                    Vaccination.is_active == True
                )
            ).order_by(Vaccination.vaccination_date.desc())
        )
        vaccinations = result.scalars().all()
        
        # Convert to dict format
        return [
            {
                "id": v.id,
                "vaccine_name": v.vaccine_name,
                "dose_number": v.dose_number,
                "vaccination_date": v.vaccination_date.isoformat() if v.vaccination_date else None,
                "status": v.status.value if v.status else None,
                "hospital_id": v.hospital_id,
                "recorded_by_user_id": v.recorded_by_user_id,
            }
            for v in vaccinations
        ]
    
    async def update_beneficiary(
        self,
        beneficiary_id: int,
        user: User,
        update_data: BeneficiaryUpdate
    ) -> Optional[Beneficiary]:
        """Update beneficiary"""
        beneficiary = await self.get_beneficiary_by_id(beneficiary_id, user)
        if not beneficiary:
            return None
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(beneficiary, field, value)
        
        await self.db.commit()
        await self.db.refresh(beneficiary)
        
        return beneficiary
    
    async def get_beneficiary_by_qr_token(
        self,
        qr_token: str
    ) -> Optional[Beneficiary]:
        """Get beneficiary by QR code token"""
        result = await self.db.execute(
            select(Beneficiary).where(
                and_(
                    Beneficiary.qr_code_token == qr_token,
                    Beneficiary.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

