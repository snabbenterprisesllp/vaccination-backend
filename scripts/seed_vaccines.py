"""
Seed database with India Universal Immunization Program vaccines
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.vaccine_master import VaccineMaster, VaccineType, VaccineCategory


VACCINES_DATA = [
    {
        "vaccine_name": "BCG",
        "vaccine_code": "BCG001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Bacillus Calmette-Guérin vaccine",
        "protects_against": "Tuberculosis",
        "total_doses": 1,
        "dosage_schedule": {"dose_1": "At birth or as early as possible"},
        "recommended_age_start": "At birth",
        "recommended_age_end": "1 year",
        "route_of_administration": "Intradermal",
        "site_of_administration": "Left upper arm",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "Hepatitis B (Birth Dose)",
        "vaccine_code": "HEPB001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Hepatitis B birth dose",
        "protects_against": "Hepatitis B",
        "total_doses": 1,
        "dosage_schedule": {"dose_1": "At birth (within 24 hours)"},
        "recommended_age_start": "At birth",
        "recommended_age_end": "24 hours",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Anterolateral thigh",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "OPV (Oral Polio Vaccine)",
        "vaccine_code": "OPV001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Oral Polio Vaccine",
        "protects_against": "Poliomyelitis",
        "total_doses": 4,
        "dosage_schedule": {
            "dose_0": "At birth",
            "dose_1": "6 weeks",
            "dose_2": "10 weeks",
            "dose_3": "14 weeks"
        },
        "recommended_age_start": "At birth",
        "recommended_age_end": "5 years",
        "route_of_administration": "Oral",
        "site_of_administration": "Oral",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "Pentavalent (DTwP-Hib-HepB)",
        "vaccine_code": "PENTA001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Combined vaccine for Diphtheria, Tetanus, Pertussis, Hib, and Hepatitis B",
        "protects_against": "Diphtheria, Tetanus, Pertussis, Haemophilus influenzae type B, Hepatitis B",
        "total_doses": 3,
        "dosage_schedule": {
            "dose_1": "6 weeks",
            "dose_2": "10 weeks",
            "dose_3": "14 weeks"
        },
        "recommended_age_start": "6 weeks",
        "recommended_age_end": "1 year",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Anterolateral thigh",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "Rotavirus Vaccine",
        "vaccine_code": "ROTA001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Rotavirus vaccine",
        "protects_against": "Rotavirus diarrhea",
        "total_doses": 3,
        "dosage_schedule": {
            "dose_1": "6 weeks",
            "dose_2": "10 weeks",
            "dose_3": "14 weeks"
        },
        "recommended_age_start": "6 weeks",
        "recommended_age_end": "32 weeks",
        "route_of_administration": "Oral",
        "site_of_administration": "Oral",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "PCV (Pneumococcal Conjugate Vaccine)",
        "vaccine_code": "PCV001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Pneumococcal Conjugate Vaccine",
        "protects_against": "Pneumococcal diseases",
        "total_doses": 3,
        "dosage_schedule": {
            "dose_1": "6 weeks",
            "dose_2": "14 weeks",
            "booster": "9-12 months"
        },
        "recommended_age_start": "6 weeks",
        "recommended_age_end": "2 years",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Anterolateral thigh",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "IPV (Inactivated Polio Vaccine)",
        "vaccine_code": "IPV001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Inactivated Polio Vaccine",
        "protects_against": "Poliomyelitis",
        "total_doses": 2,
        "dosage_schedule": {
            "dose_1": "6 weeks",
            "dose_2": "14 weeks"
        },
        "recommended_age_start": "6 weeks",
        "recommended_age_end": "1 year",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Anterolateral thigh",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "MR (Measles-Rubella)",
        "vaccine_code": "MR001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Measles and Rubella vaccine",
        "protects_against": "Measles, Rubella",
        "total_doses": 2,
        "dosage_schedule": {
            "dose_1": "9-12 months",
            "dose_2": "16-24 months"
        },
        "recommended_age_start": "9 months",
        "recommended_age_end": "15 years",
        "route_of_administration": "Subcutaneous",
        "site_of_administration": "Upper arm",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "JE (Japanese Encephalitis)",
        "vaccine_code": "JE001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.RECOMMENDED,
        "description": "Japanese Encephalitis vaccine",
        "protects_against": "Japanese Encephalitis",
        "total_doses": 2,
        "dosage_schedule": {
            "dose_1": "9-12 months",
            "dose_2": "16-24 months"
        },
        "recommended_age_start": "9 months",
        "recommended_age_end": "15 years",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Upper arm",
        "available_in_govt": True,
        "available_in_private": True,
    },
    {
        "vaccine_name": "DPT Booster",
        "vaccine_code": "DPT001",
        "vaccine_type": VaccineType.UNIVERSAL,
        "category": VaccineCategory.MANDATORY,
        "description": "Diphtheria, Pertussis, and Tetanus booster",
        "protects_against": "Diphtheria, Pertussis, Tetanus",
        "total_doses": 2,
        "dosage_schedule": {
            "booster_1": "16-24 months",
            "booster_2": "5-6 years"
        },
        "recommended_age_start": "16 months",
        "recommended_age_end": "7 years",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Upper arm",
        "available_in_govt": True,
        "available_in_private": True,
    },
    # Private/Optional vaccines
    {
        "vaccine_name": "Chickenpox (Varicella)",
        "vaccine_code": "VAR001",
        "vaccine_type": VaccineType.PRIVATE,
        "category": VaccineCategory.RECOMMENDED,
        "description": "Varicella (Chickenpox) vaccine",
        "protects_against": "Chickenpox",
        "total_doses": 2,
        "dosage_schedule": {
            "dose_1": "12-15 months",
            "dose_2": "4-6 years"
        },
        "recommended_age_start": "12 months",
        "recommended_age_end": "13 years",
        "route_of_administration": "Subcutaneous",
        "site_of_administration": "Upper arm",
        "available_in_govt": False,
        "available_in_private": True,
    },
    {
        "vaccine_name": "MMR (Measles-Mumps-Rubella)",
        "vaccine_code": "MMR001",
        "vaccine_type": VaccineType.PRIVATE,
        "category": VaccineCategory.RECOMMENDED,
        "description": "Measles, Mumps, and Rubella vaccine",
        "protects_against": "Measles, Mumps, Rubella",
        "total_doses": 2,
        "dosage_schedule": {
            "dose_1": "12-15 months",
            "dose_2": "4-6 years"
        },
        "recommended_age_start": "12 months",
        "recommended_age_end": "13 years",
        "route_of_administration": "Subcutaneous",
        "site_of_administration": "Upper arm",
        "available_in_govt": False,
        "available_in_private": True,
    },
    {
        "vaccine_name": "Hepatitis A",
        "vaccine_code": "HEPA001",
        "vaccine_type": VaccineType.PRIVATE,
        "category": VaccineCategory.RECOMMENDED,
        "description": "Hepatitis A vaccine",
        "protects_against": "Hepatitis A",
        "total_doses": 2,
        "dosage_schedule": {
            "dose_1": "12-18 months",
            "dose_2": "6-12 months after dose 1"
        },
        "recommended_age_start": "12 months",
        "recommended_age_end": "18 years",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Upper arm",
        "available_in_govt": False,
        "available_in_private": True,
    },
    {
        "vaccine_name": "Typhoid Conjugate Vaccine",
        "vaccine_code": "TCV001",
        "vaccine_type": VaccineType.PRIVATE,
        "category": VaccineCategory.RECOMMENDED,
        "description": "Typhoid Conjugate Vaccine",
        "protects_against": "Typhoid fever",
        "total_doses": 1,
        "dosage_schedule": {"dose_1": "6 months - 2 years"},
        "recommended_age_start": "6 months",
        "recommended_age_end": "18 years",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Upper arm",
        "available_in_govt": False,
        "available_in_private": True,
    },
    {
        "vaccine_name": "HPV (Human Papillomavirus)",
        "vaccine_code": "HPV001",
        "vaccine_type": VaccineType.PRIVATE,
        "category": VaccineCategory.RECOMMENDED,
        "description": "Human Papillomavirus vaccine",
        "protects_against": "HPV-related cancers",
        "total_doses": 2,
        "dosage_schedule": {
            "dose_1": "9-14 years",
            "dose_2": "6 months after dose 1"
        },
        "recommended_age_start": "9 years",
        "recommended_age_end": "26 years",
        "route_of_administration": "Intramuscular",
        "site_of_administration": "Upper arm",
        "available_in_govt": False,
        "available_in_private": True,
    },
]


async def seed_vaccines():
    """Seed vaccine master data"""
    async with AsyncSessionLocal() as session:
        try:
            for vaccine_data in VACCINES_DATA:
                # Check if vaccine already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(VaccineMaster).where(
                        VaccineMaster.vaccine_code == vaccine_data["vaccine_code"]
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    vaccine = VaccineMaster(**vaccine_data)
                    session.add(vaccine)
                    print(f"Added: {vaccine_data['vaccine_name']}")
                else:
                    print(f"Skipped (exists): {vaccine_data['vaccine_name']}")
            
            await session.commit()
            print(f"\nSuccessfully seeded {len(VACCINES_DATA)} vaccines!")
        
        except Exception as e:
            print(f"Error seeding vaccines: {e}")
            await session.rollback()
        
        finally:
            await session.close()


if __name__ == "__main__":
    print("Seeding vaccine master data...\n")
    asyncio.run(seed_vaccines())

