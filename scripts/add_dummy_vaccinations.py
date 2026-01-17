"""
Script to add dummy vaccination records for parent beneficiaries
"""
import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.beneficiary import Beneficiary, BeneficiaryType
from app.models.vaccination import Vaccination, VaccinationStatus
from app.models.vaccine_master import VaccineMaster
from app.models.user import User
from app.core.config import settings

# Common adult vaccines
ADULT_VACCINES = [
    "COVID-19",
    "Influenza (Flu)",
    "Tetanus",
    "Diphtheria",
    "Hepatitis B",
    "MMR (Measles, Mumps, Rubella)",
    "Varicella (Chickenpox)",
    "Pneumococcal",
    "Shingles (Herpes Zoster)"
]


async def get_parent_beneficiary(db: AsyncSession, user_email: str = None):
    """Get parent beneficiary - if email provided, get that user's beneficiary, otherwise get first parent"""
    if user_email:
        # Get specific user's beneficiary
        user_result = await db.execute(
            select(User).where(User.email == user_email)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            print(f"User with email {user_email} not found")
            return None
        
        beneficiary_result = await db.execute(
            select(Beneficiary).where(
                Beneficiary.account_id == user.id,
                Beneficiary.type == BeneficiaryType.ADULT,
                Beneficiary.is_active == True
            )
        )
        beneficiary = beneficiary_result.scalar_one_or_none()
        
        if not beneficiary:
            print(f"Parent beneficiary not found for user {user_email}")
            return None
        
        return beneficiary
    else:
        # Get first parent beneficiary
        beneficiary_result = await db.execute(
            select(Beneficiary).where(
                Beneficiary.type == BeneficiaryType.ADULT,
                Beneficiary.is_active == True
            ).limit(1)
        )
        beneficiary = beneficiary_result.scalar_one_or_none()
        return beneficiary


async def get_vaccine_by_name(db: AsyncSession, vaccine_name: str):
    """Get vaccine by name (fuzzy match)"""
    result = await db.execute(
        select(VaccineMaster).where(
            VaccineMaster.vaccine_name.ilike(f"%{vaccine_name}%"),
            VaccineMaster.is_active == True
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def add_dummy_vaccinations(db: AsyncSession, beneficiary_id: int, count: int = 5):
    """Add dummy vaccination records for a beneficiary"""
    beneficiary_result = await db.execute(
        select(Beneficiary).where(Beneficiary.id == beneficiary_id)
    )
    beneficiary = beneficiary_result.scalar_one_or_none()
    
    if not beneficiary:
        print(f"Beneficiary {beneficiary_id} not found")
        return
    
    print(f"\nAdding {count} dummy vaccination records for: {beneficiary.full_name} (ID: {beneficiary_id})")
    
    # Get some vaccines
    vaccines_to_use = []
    for vaccine_name in ADULT_VACCINES[:count]:
        vaccine = await get_vaccine_by_name(db, vaccine_name)
        if vaccine:
            vaccines_to_use.append(vaccine)
        else:
            # If vaccine not found, try to get any active vaccine
            all_vaccines_result = await db.execute(
                select(VaccineMaster).where(VaccineMaster.is_active == True).limit(1)
            )
            fallback_vaccine = all_vaccines_result.scalar_one_or_none()
            if fallback_vaccine:
                vaccines_to_use.append(fallback_vaccine)
    
    if not vaccines_to_use:
        print("No vaccines found in database. Please seed vaccines first.")
        return
    
    # Create vaccination records
    created_count = 0
    base_date = date.today()
    
    for i, vaccine in enumerate(vaccines_to_use):
        # Create vaccinations with dates in the past (1-12 months ago)
        months_ago = count - i
        vaccination_date = base_date - timedelta(days=months_ago * 30)
        
        vaccination = Vaccination(
            beneficiary_id=beneficiary_id,
            vaccine_id=vaccine.id,
            vaccine_name=vaccine.vaccine_name,
            dose_number=1 if i < 3 else 2,  # First 3 are dose 1, rest are dose 2
            vaccination_date=vaccination_date,
            vaccination_time=datetime.now() - timedelta(days=months_ago * 30),
            status=VaccinationStatus.COMPLETED,
            hospital_id=None,  # Can be set if hospitals exist
            administered_by=f"Dr. Test {i+1}",
            batch_number=f"BATCH-{2024-i}-{i+1:03d}",
            manufacturer="Test Manufacturer",
            site_of_administration="Left Arm" if i % 2 == 0 else "Right Arm",
            route_of_administration="Intramuscular",
            notes=f"Dummy vaccination record {i+1} for testing purposes",
            verified_by_parent=True,
            verified_at=datetime.now() - timedelta(days=months_ago * 30),
            is_active=True
        )
        
        db.add(vaccination)
        created_count += 1
        print(f"  ✓ Created: {vaccine.vaccine_name} - Dose {vaccination.dose_number} on {vaccination_date}")
    
    await db.commit()
    print(f"\n✅ Successfully created {created_count} dummy vaccination records!")


async def main():
    """Main function"""
    import os
    
    # Get database URL from environment or use default
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Try to construct from settings
        try:
            database_url = settings.DATABASE_URL
        except:
            database_url = "postgresql+asyncpg://postgres:password@localhost:5432/vaccination_db"
    
    print(f"Connecting to database...")
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'hidden'}")
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get user email from command line if provided
        user_email = sys.argv[1] if len(sys.argv) > 1 else None
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        
        # Get parent beneficiary
        beneficiary = await get_parent_beneficiary(db, user_email)
        
        if not beneficiary:
            print("\n❌ No parent beneficiary found.")
            print("Usage: python scripts/add_dummy_vaccinations.py [user_email] [count]")
            print("Example: python scripts/add_dummy_vaccinations.py user@example.com 5")
            return
        
        # Add dummy vaccinations
        await add_dummy_vaccinations(db, beneficiary.id, count)
    
    await engine.dispose()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())

