#!/usr/bin/env python3
"""
Script to list all existing SUPER_ADMIN users
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.user import User
from app.models.facility_user import FacilityUser, FacilityRole


async def list_super_admins():
    """List all existing SUPER_ADMIN users"""
    print("="*60)
    print("Existing SUPER_ADMIN Users")
    print("="*60 + "\n")
    
    database_url = settings.DATABASE_URL
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Get all SUPER_ADMIN users
            result = await db.execute(
                select(FacilityUser, User).join(
                    User, FacilityUser.user_id == User.id
                ).where(
                    FacilityUser.facility_role == FacilityRole.SUPER_ADMIN,
                    FacilityUser.is_active == True
                )
            )
            super_admins = result.all()
            
            if not super_admins:
                print("No SUPER_ADMIN users found in the database.")
                return
            
            print(f"Found {len(super_admins)} SUPER_ADMIN user(s):\n")
            
            for idx, (facility_user, user) in enumerate(super_admins, 1):
                print(f"{idx}. User ID: {user.id}")
                print(f"   Mobile: {user.mobile_number}")
                print(f"   Name: {user.full_name}")
                print(f"   Email: {user.email or 'N/A'}")
                print(f"   Created: {facility_user.created_at}")
                print()
            
            print("="*60)
            print("\nTo login as SUPER_ADMIN:")
            print("1. Use the mobile number above")
            print("2. Request OTP via: POST /api/v1/auth/otp/request")
            print("3. Verify OTP via: POST /api/v1/auth/otp/verify")
            print("\nTo create additional SUPER_ADMINS:")
            print("1. Login as an existing SUPER_ADMIN")
            print("2. Use: POST /api/v1/auth/super-admin/create")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(list_super_admins())

