#!/usr/bin/env python3
"""
Script to check if a user exists and show their details
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


async def check_user(mobile_number: str):
    """Check if user exists and show details"""
    print("="*60)
    print(f"Checking user: {mobile_number}")
    print("="*60 + "\n")
    
    database_url = settings.DATABASE_URL
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Try exact match first
            result = await db.execute(
                select(User).where(User.mobile_number == mobile_number)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Try with different formats
                print(f"User not found with exact match: {mobile_number}")
                print("\nTrying variations...")
                
                # Try without spaces
                mobile_clean = mobile_number.replace(" ", "").replace("-", "")
                result = await db.execute(
                    select(User).where(User.mobile_number == mobile_clean)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    print(f"Found user with cleaned number: {mobile_clean}")
            
            if not user:
                print(f"\n❌ User not found in database")
                print(f"\nSearched for: {mobile_number}")
                print(f"Also tried: {mobile_number.replace(' ', '').replace('-', '')}")
                
                # List all users to help debug
                print("\nAll users in database:")
                result = await db.execute(select(User))
                all_users = result.scalars().all()
                if all_users:
                    for u in all_users:
                        print(f"  - ID: {u.id}, Mobile: {u.mobile_number}, Name: {u.full_name}, Role: {u.role.value}, LoginType: {u.login_type.value}")
                else:
                    print("  (No users found)")
                return
            
            print(f"\n✅ User found!")
            print(f"  ID: {user.id}")
            print(f"  Mobile: {user.mobile_number}")
            print(f"  Name: {user.full_name}")
            print(f"  Email: {user.email or 'N/A'}")
            print(f"  Role: {user.role.value}")
            print(f"  Login Type: {user.login_type.value}")
            print(f"  Is Active: {user.is_active}")
            print(f"  Created: {user.created_at}")
            
            # Check if SUPER_ADMIN
            result = await db.execute(
                select(FacilityUser).where(
                    FacilityUser.user_id == user.id,
                    FacilityUser.facility_role == FacilityRole.SUPER_ADMIN,
                    FacilityUser.is_active == True
                )
            )
            super_admin = result.scalar_one_or_none()
            
            if super_admin:
                print(f"\n  ✅ User is SUPER_ADMIN")
                print(f"  Facility User ID: {super_admin.id}")
                print(f"  Assigned by: {super_admin.assigned_by or 'System'}")
            else:
                print(f"\n  ⚠️  User is NOT a SUPER_ADMIN")
                
                # Check all facility roles
                result = await db.execute(
                    select(FacilityUser).where(
                        FacilityUser.user_id == user.id,
                        FacilityUser.is_active == True
                    )
                )
                facility_users = result.scalars().all()
                if facility_users:
                    print(f"  Facility roles:")
                    for fu in facility_users:
                        print(f"    - {fu.facility_role.value} (Facility ID: {fu.facility_id})")
                else:
                    print(f"  No facility roles assigned")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_user.py <mobile_number>")
        print("Example: python scripts/check_user.py 9437221134")
        sys.exit(1)
    
    mobile_number = sys.argv[1]
    asyncio.run(check_user(mobile_number))

