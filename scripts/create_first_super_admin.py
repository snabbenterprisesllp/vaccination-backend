#!/usr/bin/env python3
"""
Secure script to create the first SUPER_ADMIN user

This script requires a bootstrap token from environment variable
to prevent unauthorized SUPER_ADMIN creation.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.user import User, LoginType
from app.models.facility_user import FacilityUser, FacilityRole


async def create_first_super_admin():
    """Create the first SUPER_ADMIN user with bootstrap token validation"""
    print("="*60)
    print("Create First SUPER_ADMIN User")
    print("="*60 + "\n")
    
    # Check bootstrap token
    bootstrap_token = os.getenv('SUPER_ADMIN_BOOTSTRAP_TOKEN')
    allow_signup = os.getenv('ALLOW_SUPER_ADMIN_SIGNUP', 'false').lower() == 'true'
    
    if not bootstrap_token and not allow_signup:
        print("❌ Error: SUPER_ADMIN signup is disabled")
        print("\nTo enable:")
        print("1. Set ALLOW_SUPER_ADMIN_SIGNUP=true in .env")
        print("2. OR set SUPER_ADMIN_BOOTSTRAP_TOKEN=<secure-token> in .env")
        return False
    
    # Prompt for bootstrap token if required
    if bootstrap_token:
        print("Bootstrap token required.")
        entered_token = input("Enter bootstrap token: ").strip()
        if entered_token != bootstrap_token:
            print("❌ Invalid bootstrap token")
            return False
    
    # Check if SUPER_ADMIN already exists
    database_url = settings.DATABASE_URL
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Check for existing SUPER_ADMIN
            result = await db.execute(
                select(FacilityUser).where(
                    FacilityUser.facility_role == FacilityRole.SUPER_ADMIN,
                    FacilityUser.is_active == True
                ).limit(1)
            )
            existing_super_admin = result.scalar_one_or_none()
            
            if existing_super_admin:
                print("⚠️  SUPER_ADMIN already exists!")
                print(f"User ID: {existing_super_admin.user_id}")
                response = input("Create another SUPER_ADMIN? (yes/no): ").strip().lower()
                if response != 'yes':
                    return False
            
            # Get user details
            print("\nEnter SUPER_ADMIN details:")
            mobile_number = input("Mobile number: ").strip()
            full_name = input("Full name: ").strip()
            email = input("Email (optional): ").strip() or None
            
            # Check if user exists
            result = await db.execute(
                select(User).where(User.mobile_number == mobile_number)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"⚠️  User with mobile {mobile_number} already exists.")
                response = input("Assign SUPER_ADMIN role to this user? (yes/no): ").strip().lower()
                if response != 'yes':
                    return False
                user = existing_user
            else:
                # Create new user
                from datetime import datetime
                user = User(
                    mobile_number=mobile_number,
                    full_name=full_name,
                    email=email,
                    login_type=LoginType.HOSPITAL,
                    consent_given='Y',
                    consent_timestamp=datetime.utcnow().isoformat()
                )
                db.add(user)
                await db.flush()
                print(f"✅ Created new user: {user.id}")
            
            # Create SUPER_ADMIN assignment
            facility_user = FacilityUser(
                user_id=user.id,
                facility_id=None,  # NULL for SUPER_ADMIN (global scope)
                facility_role=FacilityRole.SUPER_ADMIN,
                is_active=True,
                assigned_by=None  # System assignment
            )
            db.add(facility_user)
            await db.commit()
            
            print("\n" + "="*60)
            print("✅ SUPER_ADMIN created successfully!")
            print("="*60)
            print(f"\nUser ID: {user.id}")
            print(f"Mobile: {user.mobile_number}")
            print(f"Name: {user.full_name}")
            print(f"\nThis user now has SUPER_ADMIN privileges.")
            print("They can:")
            print("  - Create and manage facilities")
            print("  - Assign FACILITY_ADMINS")
            print("  - View global analytics")
            print("  - Access all facility data")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("Create First SUPER_ADMIN User Script")
    print("="*60 + "\n")
    
    success = asyncio.run(create_first_super_admin())
    
    if not success:
        print("\n⚠️  Failed to create SUPER_ADMIN. Please check the error messages above.")
        sys.exit(1)
    else:
        print("\n✨ SUPER_ADMIN created successfully!")
        sys.exit(0)

