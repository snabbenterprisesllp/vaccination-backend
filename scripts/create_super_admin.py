#!/usr/bin/env python3
"""
Script to create the first SUPER_ADMIN user
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


async def create_super_admin():
    """Create or assign SUPER_ADMIN role to a user"""
    print("="*60)
    print("Create SUPER_ADMIN User")
    print("="*60 + "\n")
    
    # Get database URL
    database_url = settings.DATABASE_URL
    
    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Option 1: Use existing user
            print("Option 1: Assign SUPER_ADMIN to existing user")
            print("Option 2: Create new user and assign SUPER_ADMIN")
            print("\nEnter option (1 or 2): ", end="")
            option = input().strip()
            
            user = None
            
            if option == "1":
                # List existing users
                result = await db.execute(
                    select(User).order_by(User.created_at.desc()).limit(10)
                )
                users = result.scalars().all()
                
                if not users:
                    print("No users found. Please create a user first.")
                    return False
                
                print("\nExisting users:")
                for u in users:
                    print(f"  {u.id}: {u.mobile_number} - {u.full_name or 'N/A'}")
                
                print("\nEnter user ID to assign SUPER_ADMIN: ", end="")
                user_id = int(input().strip())
                
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    print(f"❌ User with ID {user_id} not found")
                    return False
                
            elif option == "2":
                # Create new user
                print("\nEnter mobile number: ", end="")
                mobile_number = input().strip()
                
                print("Enter full name: ", end="")
                full_name = input().strip()
                
                print("Enter email (optional): ", end="")
                email = input().strip() or None
                
                # Check if user already exists
                result = await db.execute(
                    select(User).where(User.mobile_number == mobile_number)
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    print(f"⚠️  User with mobile {mobile_number} already exists. Using existing user.")
                    user = existing_user
                else:
                    # Create new user
                    from app.models.user import LoginType
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
            
            else:
                print("❌ Invalid option")
                return False
            
            # Check if user already has SUPER_ADMIN
            result = await db.execute(
                select(FacilityUser).where(
                    FacilityUser.user_id == user.id,
                    FacilityUser.facility_role == FacilityRole.SUPER_ADMIN,
                    FacilityUser.is_active == True
                )
            )
            existing_super_admin = result.scalar_one_or_none()
            
            if existing_super_admin:
                print(f"⚠️  User {user.id} ({user.mobile_number}) already has SUPER_ADMIN role")
                return True
            
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
    print("Create SUPER_ADMIN User Script")
    print("="*60 + "\n")
    
    success = asyncio.run(create_super_admin())
    
    if not success:
        print("\n⚠️  Failed to create SUPER_ADMIN. Please check the error messages above.")
        sys.exit(1)
    else:
        print("\n✨ SUPER_ADMIN created successfully!")
        sys.exit(0)

