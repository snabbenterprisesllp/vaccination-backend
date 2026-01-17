#!/usr/bin/env python3
"""
Script to run the beneficiary system migration
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings


def run_migration():
    """Run the beneficiary migration SQL script"""
    # Get database URL (remove asyncpg for sync connection)
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    elif database_url.startswith("postgresql://"):
        pass  # Already correct
    else:
        print(f"Error: Unsupported database URL format: {database_url}")
        return False
    
    print(f"Connecting to database...")
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'hidden'}")
    
    try:
        # Create sync engine for running raw SQL
        engine = create_engine(database_url)
        
        # Read migration file
        migration_file = Path(__file__).parent.parent / "migrations" / "add_beneficiary_system.sql"
        
        if not migration_file.exists():
            print(f"Error: Migration file not found: {migration_file}")
            return False
        
        print(f"Reading migration file: {migration_file}")
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Execute migration
        print("\n" + "="*60)
        print("Running Beneficiary System Migration")
        print("="*60 + "\n")
        
        with engine.connect() as connection:
            # Execute the migration in a transaction
            trans = connection.begin()
            try:
                # Split by semicolons and execute each statement
                statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
                
                for i, statement in enumerate(statements, 1):
                    if statement:
                        print(f"Executing statement {i}/{len(statements)}...")
                        connection.execute(text(statement))
                
                trans.commit()
                print("\n" + "="*60)
                print("✅ Migration completed successfully!")
                print("="*60)
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Error during migration: {e}")
                print("\nRolling back transaction...")
                return False
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    print("Beneficiary System Migration Script")
    print("="*60 + "\n")
    
    success = run_migration()
    
    if not success:
        print("\n⚠️  Migration failed. Please check the error messages above.")
        sys.exit(1)
    else:
        print("\n✨ Migration completed successfully!")
        print("You can now use the beneficiary-based vaccination system.")
        sys.exit(0)

