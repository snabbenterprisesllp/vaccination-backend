#!/usr/bin/env python3
"""
Script to delete all facilities except the one with the specified facility_id

Usage:
    python scripts/delete_facilities_except.py FAC-B6B48A218C8E
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, text
from app.core.config import settings
from app.models.facility import Facility
from app.models.facility_user import FacilityUser
from app.models.vaccination import Vaccination


async def delete_facilities_except(facility_id_to_keep: str):
    """Delete all facilities except the one with the specified facility_id"""
    print("="*60)
    print(f"Deleting all facilities except: {facility_id_to_keep}")
    print("="*60 + "\n")
    
    database_url = settings.DATABASE_URL
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # First, find the facility to keep
            result = await db.execute(
                select(Facility).where(Facility.facility_id == facility_id_to_keep)
            )
            facility_to_keep = result.scalar_one_or_none()
            
            if not facility_to_keep:
                print(f"❌ Error: Facility with facility_id '{facility_id_to_keep}' not found!")
                print("\nAvailable facilities:")
                result = await db.execute(select(Facility))
                facilities = result.scalars().all()
                for f in facilities:
                    print(f"  - ID: {f.id}, facility_id: {f.facility_id}, Name: {f.name}")
                return False
            
            print(f"✅ Found facility to keep:")
            print(f"   ID: {facility_to_keep.id}")
            print(f"   facility_id: {facility_to_keep.facility_id}")
            print(f"   Name: {facility_to_keep.name}")
            print()
            
            # Get all facilities to delete
            result = await db.execute(
                select(Facility).where(Facility.facility_id != facility_id_to_keep)
            )
            facilities_to_delete = result.scalars().all()
            
            if not facilities_to_delete:
                print("✅ No facilities to delete. Only the specified facility exists.")
                return True
            
            print(f"⚠️  Found {len(facilities_to_delete)} facility(ies) to delete:")
            for f in facilities_to_delete:
                print(f"   - ID: {f.id}, facility_id: {f.facility_id}, Name: {f.name}")
            
            # Count related records
            print("\n📊 Checking related records...")
            
            facility_ids_to_delete = [f.id for f in facilities_to_delete]
            
            # Count facility_users
            facility_users_result = await db.execute(
                select(FacilityUser).where(FacilityUser.facility_id.in_(facility_ids_to_delete))
            )
            facility_users = facility_users_result.scalars().all()
            print(f"   - Facility Users: {len(facility_users)}")
            
            # Count vaccinations
            vaccinations_result = await db.execute(
                select(Vaccination).where(Vaccination.facility_id.in_(facility_ids_to_delete))
            )
            vaccinations = vaccinations_result.scalars().all()
            print(f"   - Vaccinations: {len(vaccinations)}")
            
            # Confirm deletion
            print("\n" + "="*60)
            print("⚠️  WARNING: This will permanently delete:")
            print(f"   - {len(facilities_to_delete)} facility(ies)")
            print(f"   - {len(facility_users)} facility user assignment(s)")
            print(f"   - {len(vaccinations)} vaccination record(s) (facility_id will be set to NULL)")
            print("="*60)
            
            confirm = input("\nType 'DELETE' to confirm: ")
            if confirm != 'DELETE':
                print("❌ Deletion cancelled.")
                return False
            
            print("\n🗑️  Starting deletion...")
            
            # Delete facility_users first (they have foreign key to facilities)
            if facility_users:
                await db.execute(
                    delete(FacilityUser).where(FacilityUser.facility_id.in_(facility_ids_to_delete))
                )
                print(f"✅ Deleted {len(facility_users)} facility user assignment(s)")
            
            # Set facility_id to NULL for vaccinations (instead of deleting them)
            if vaccinations:
                await db.execute(
                    text("UPDATE vaccinations SET facility_id = NULL WHERE facility_id = ANY(:ids)"),
                    {"ids": facility_ids_to_delete}
                )
                print(f"✅ Set facility_id to NULL for {len(vaccinations)} vaccination record(s)")
            
            # Delete facilities
            await db.execute(
                delete(Facility).where(Facility.facility_id != facility_id_to_keep)
            )
            print(f"✅ Deleted {len(facilities_to_delete)} facility(ies)")
            
            # Commit transaction
            await db.commit()
            
            print("\n✅ Successfully deleted all facilities except the specified one!")
            
            # Verify
            result = await db.execute(select(Facility))
            remaining_facilities = result.scalars().all()
            print(f"\n📋 Remaining facilities: {len(remaining_facilities)}")
            for f in remaining_facilities:
                print(f"   - ID: {f.id}, facility_id: {f.facility_id}, Name: {f.name}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/delete_facilities_except.py <facility_id>")
        print("\nExample:")
        print("  python scripts/delete_facilities_except.py FAC-B6B48A218C8E")
        sys.exit(1)
    
    facility_id = sys.argv[1]
    success = await delete_facilities_except(facility_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())


