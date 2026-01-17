"""Vaccination service"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import date, datetime

from app.models.vaccination import Vaccination, VaccinationSchedule
from app.models.child_profile import ChildProfile
from app.models.beneficiary import Beneficiary
from app.models.hospital import Hospital
from app.schemas.vaccination import (
    VaccinationCreate,
    VaccinationUpdate,
    VaccinationScheduleCreate,
    VaccinationScheduleUpdate
)


class VaccinationService:
    """Vaccination management service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_vaccination(
        self,
        vaccination_data: VaccinationCreate,
        recorded_by_user_id: Optional[int] = None
    ) -> Vaccination:
        """Create a new vaccination record"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Prefer beneficiary_id over child_id
        if vaccination_data.beneficiary_id:
            # Validate beneficiary exists
            logger.info(f"Validating beneficiary for vaccination creation: beneficiary_id={vaccination_data.beneficiary_id}")
            beneficiary_result = await self.db.execute(
                select(Beneficiary).where(
                    and_(
                        Beneficiary.id == vaccination_data.beneficiary_id,
                        Beneficiary.is_active == True
                    )
                )
            )
            beneficiary = beneficiary_result.scalar_one_or_none()
            
            if not beneficiary:
                logger.error(f"Beneficiary not found or inactive: beneficiary_id={vaccination_data.beneficiary_id}")
                raise ValueError(f"Beneficiary not found or inactive (ID: {vaccination_data.beneficiary_id})")
            
            logger.info(f"Beneficiary validated: id={beneficiary.id}, name={beneficiary.full_name}, type={beneficiary.type.value}")
            
        elif vaccination_data.child_id:
            # Legacy: validate child profile exists
            logger.info(f"Validating child profile for vaccination creation: child_id={vaccination_data.child_id}")
            child_result = await self.db.execute(
                select(ChildProfile).where(
                    and_(
                        ChildProfile.id == vaccination_data.child_id,
                        ChildProfile.is_active == True
                    )
                )
            )
            child_profile = child_result.scalar_one_or_none()
            
            if not child_profile:
                logger.error(f"Child profile not found or inactive: child_id={vaccination_data.child_id}")
                raise ValueError(f"Child profile not found or inactive (ID: {vaccination_data.child_id})")
            
            logger.info(f"Child profile validated: id={child_profile.id}, name={child_profile.full_name}")
        else:
            raise ValueError("Either beneficiary_id or child_id must be provided")
        
        # Validate hospital_id if provided
        if vaccination_data.hospital_id:
            logger.info(f"Validating hospital for vaccination creation: hospital_id={vaccination_data.hospital_id}")
            hospital_result = await self.db.execute(
                select(Hospital).where(
                    and_(
                        Hospital.id == vaccination_data.hospital_id,
                        Hospital.is_active == True
                    )
                )
            )
            hospital = hospital_result.scalar_one_or_none()
            
            if not hospital:
                logger.error(f"Hospital not found or inactive: hospital_id={vaccination_data.hospital_id}")
                raise ValueError(f"Hospital not found or inactive (ID: {vaccination_data.hospital_id})")
            
            logger.info(f"Hospital validated: id={hospital.id}, name={hospital.name}")
        
        # Create vaccination
        vaccination_dict = vaccination_data.model_dump(exclude={'child_id' if vaccination_data.beneficiary_id else 'beneficiary_id'})
        vaccination = Vaccination(**vaccination_dict)
        vaccination.vaccination_time = datetime.now()
        
        # Set recorded_by_user_id if provided
        if recorded_by_user_id:
            vaccination.recorded_by_user_id = recorded_by_user_id
        
        self.db.add(vaccination)
        await self.db.commit()
        await self.db.refresh(vaccination)
        
        logger.info(f"Vaccination created successfully: id={vaccination.id}, vaccine={vaccination.vaccine_name}")
        return vaccination
    
    async def get_vaccination_by_id(
        self,
        vaccination_id: int
    ) -> Optional[Vaccination]:
        """Get vaccination by ID"""
        result = await self.db.execute(
            select(Vaccination).where(Vaccination.id == vaccination_id)
        )
        return result.scalar_one_or_none()
    
    async def get_child_vaccinations(
        self,
        child_id: int
    ) -> List[Vaccination]:
        """Get all vaccinations for a child"""
        result = await self.db.execute(
            select(Vaccination).where(
                and_(
                    Vaccination.child_id == child_id,
                    Vaccination.is_active == True
                )
            ).order_by(Vaccination.vaccination_date.desc())
        )
        return list(result.scalars().all())
    
    async def get_all_vaccinations(
        self,
        hospital_id: Optional[int] = None
    ) -> List[Vaccination]:
        """Get all vaccinations (for hospital staff/admin)"""
        query = select(Vaccination).where(
            Vaccination.is_active == True
        )
        
        if hospital_id:
            query = query.where(Vaccination.hospital_id == hospital_id)
        
        result = await self.db.execute(
            query.order_by(Vaccination.vaccination_date.desc())
        )
        return list(result.scalars().all())
    
    async def update_vaccination(
        self,
        vaccination_id: int,
        update_data: VaccinationUpdate
    ) -> Optional[Vaccination]:
        """Update vaccination record"""
        vaccination = await self.get_vaccination_by_id(vaccination_id)
        if not vaccination:
            return None
        
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(vaccination, field, value)
        
        await self.db.commit()
        await self.db.refresh(vaccination)
        
        return vaccination
    
    async def delete_vaccination(self, vaccination_id: int) -> bool:
        """Soft delete vaccination"""
        vaccination = await self.get_vaccination_by_id(vaccination_id)
        if not vaccination:
            return False
        
        vaccination.is_active = False
        await self.db.commit()
        
        return True
    
    # Schedule methods
    async def create_schedule(
        self,
        schedule_data: VaccinationScheduleCreate
    ) -> VaccinationSchedule:
        """Create vaccination schedule"""
        schedule = VaccinationSchedule(**schedule_data.model_dump())
        
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        
        return schedule
    
    async def get_child_schedules(
        self,
        child_id: int,
        upcoming_only: bool = False
    ) -> List[VaccinationSchedule]:
        """Get vaccination schedules for a child"""
        query = select(VaccinationSchedule).where(
            and_(
                VaccinationSchedule.child_id == child_id,
                VaccinationSchedule.is_active == True
            )
        )
        
        if upcoming_only:
            query = query.where(
                and_(
                    VaccinationSchedule.completed == False,
                    VaccinationSchedule.due_date >= date.today()
                )
            )
        
        result = await self.db.execute(
            query.order_by(VaccinationSchedule.due_date)
        )
        return list(result.scalars().all())
    
    async def update_schedule(
        self,
        schedule_id: int,
        update_data: VaccinationScheduleUpdate
    ) -> Optional[VaccinationSchedule]:
        """Update vaccination schedule"""
        result = await self.db.execute(
            select(VaccinationSchedule).where(VaccinationSchedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return None
        
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(schedule, field, value)
        
        await self.db.commit()
        await self.db.refresh(schedule)
        
        return schedule
    
    async def get_due_schedules(self, days_ahead: int = 7) -> List[VaccinationSchedule]:
        """Get schedules due within specified days"""
        from datetime import timedelta
        
        end_date = date.today() + timedelta(days=days_ahead)
        
        result = await self.db.execute(
            select(VaccinationSchedule).where(
                and_(
                    VaccinationSchedule.completed == False,
                    VaccinationSchedule.due_date.between(date.today(), end_date),
                    VaccinationSchedule.is_active == True
                )
            ).order_by(VaccinationSchedule.due_date)
        )
        return list(result.scalars().all())

