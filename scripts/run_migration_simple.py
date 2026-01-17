#!/usr/bin/env python3
"""
Simple script to run the beneficiary migration using psycopg2
"""
import os
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Try to load from .env file
def get_db_url():
    """Get database URL from environment or .env file"""
    # First try environment variable
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Try to read from .env file
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    
    return None

def parse_db_url(url):
    """Parse PostgreSQL URL into connection parameters"""
    if not url:
        return None
    
    # Remove postgresql+asyncpg:// or postgresql:// prefix
    url = url.replace('postgresql+asyncpg://', '').replace('postgresql://', '')
    
    # Parse: user:password@host:port/database
    if '@' in url:
        auth, rest = url.split('@', 1)
        if ':' in auth:
            user, password = auth.split(':', 1)
        else:
            user, password = auth, ''
        
        if '/' in rest:
            host_port, database = rest.split('/', 1)
            if ':' in host_port:
                host, port = host_port.split(':')
            else:
                host, port = host_port, '5432'
        else:
            host, port, database = rest, '5432', ''
    else:
        return None
    
    return {
        'host': host,
        'port': port,
        'database': database,
        'user': user,
        'password': password
    }

def run_migration():
    """Run the migration"""
    print("="*60)
    print("Beneficiary System Migration")
    print("="*60 + "\n")
    
    # Get database URL
    db_url = get_db_url()
    if not db_url:
        print("❌ Error: DATABASE_URL not found in environment or .env file")
        print("\nPlease set DATABASE_URL in your .env file or environment variable")
        return False
    
    # Parse connection details
    conn_params = parse_db_url(db_url)
    if not conn_params:
        print(f"❌ Error: Could not parse DATABASE_URL: {db_url[:50]}...")
        return False
    
    print(f"Connecting to database: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
    
    # Read migration file
    migration_file = Path(__file__).parent.parent / "migrations" / "add_beneficiary_system.sql"
    if not migration_file.exists():
        print(f"❌ Error: Migration file not found: {migration_file}")
        return False
    
    print(f"Reading migration file: {migration_file.name}\n")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Connect and execute
    try:
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Executing migration...")
        print("-" * 60)
        
        # Execute the SQL
        cursor.execute(migration_sql)
        
        cursor.close()
        conn.close()
        
        print("-" * 60)
        print("✅ Migration completed successfully!")
        print("="*60)
        return True
        
    except psycopg2.Error as e:
        print(f"\n[ERROR] Database error: {e}")
        if "could not translate host name" in str(e):
            print("\nNote: If using Docker, the host 'postgres' only works inside Docker containers.")
            print("For local connection, update DATABASE_URL to use 'localhost' instead of 'postgres'")
        return False
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

