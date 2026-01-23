#!/usr/bin/env python3
"""
Script to run the multi-facility RBAC migration
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings


def run_migration():
    """Run the RBAC migration SQL script"""
    # Get database URL (remove asyncpg for sync connection)
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    elif database_url.startswith("postgresql://"):
        pass  # Already correct
    else:
        print(f"Error: Unsupported database URL format: {database_url}")
        return False
    
    # Replace Docker hostname with localhost for local execution
    if "@postgres:" in database_url:
        database_url = database_url.replace("@postgres:", "@localhost:")
        print("[INFO] Replaced Docker hostname 'postgres' with 'localhost' for local execution")
    
    # If DATABASE_URL is not set or uses defaults, try Docker Compose defaults
    import os
    if not database_url or "postgresql://" not in database_url:
        # Try Docker Compose defaults
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "password")
        db_name = os.getenv("DB_NAME", "vaccination_db")
        db_host = "localhost"  # Docker exposes on localhost
        db_port = os.getenv("DB_PORT", "5432")
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"[INFO] Using Docker Compose default credentials")
    
    print(f"Connecting to database...")
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'hidden'}")
    
    try:
        # Create sync engine for running raw SQL
        engine = create_engine(database_url)
        
        # Read migration file
        migration_file = Path(__file__).parent.parent / "migrations" / "add_multi_facility_rbac.sql"
        
        if not migration_file.exists():
            print(f"Error: Migration file not found: {migration_file}")
            return False
        
        print(f"Reading migration file: {migration_file}")
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Execute migration
        print("\n" + "="*60)
        print("Running Multi-Facility RBAC Migration")
        print("="*60 + "\n")
        
        with engine.connect() as connection:
            # Execute the migration in a transaction
            trans = connection.begin()
            try:
                # Split by semicolons and execute each statement
                # Handle DO $$ blocks properly
                statements = []
                current_statement = ""
                in_do_block = False
                
                for line in migration_sql.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('--'):
                        continue
                    
                    current_statement += line + '\n'
                    
                    if 'DO $$' in line:
                        in_do_block = True
                    if in_do_block and 'END $$;' in line:
                        statements.append(current_statement)
                        current_statement = ""
                        in_do_block = False
                    elif not in_do_block and line.endswith(';'):
                        statements.append(current_statement)
                        current_statement = ""
                
                if current_statement.strip():
                    statements.append(current_statement)
                
                for i, statement in enumerate(statements, 1):
                    if statement.strip():
                        print(f"Executing statement {i}/{len(statements)}...")
                        connection.execute(text(statement))
                
                trans.commit()
                print("\n" + "="*60)
                print("[SUCCESS] Migration completed successfully!")
                print("="*60)
                print("\nNext steps:")
                print("1. Create the first SUPER_ADMIN user")
                print("2. Run: python scripts/create_super_admin.py")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"\n[ERROR] Error during migration: {e}")
                print("\nRolling back transaction...")
                import traceback
                traceback.print_exc()
                return False
        
    except Exception as e:
        print(f"[ERROR] Error connecting to database: {e}")
        print("\nNote: Make sure PostgreSQL is running and DATABASE_URL is correctly configured.")
        print("For local development, DATABASE_URL should be: postgresql://user:password@localhost:5432/dbname")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    print("Multi-Facility RBAC Migration Script")
    print("="*60 + "\n")
    
    success = run_migration()
    
    if not success:
        print("\n[WARNING] Migration failed. Please check the error messages above.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Migration completed successfully!")
        print("You can now use the multi-facility RBAC system.")
        sys.exit(0)

