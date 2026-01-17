# Run Beneficiary System Migration
# This script runs the database migration for the beneficiary system

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Beneficiary System Migration" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if docker-compose is running
$dockerRunning = docker ps 2>&1 | Select-String "postgres"
$useDocker = $false

if ($dockerRunning) {
    Write-Host "Docker containers detected. Using Docker method..." -ForegroundColor Green
    $useDocker = $true
} else {
    Write-Host "Docker not running. Will use direct database connection..." -ForegroundColor Yellow
    Write-Host "Make sure your DATABASE_URL in .env uses 'localhost' not 'postgres'" -ForegroundColor Yellow
    Write-Host ""
}

if ($useDocker) {
    # Method 1: Using Docker
    Write-Host "Step 1: Copying migration file to container..." -ForegroundColor Green
    $containerName = docker-compose ps -q postgres 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $containerName) {
        Write-Host "ERROR: Could not find postgres container" -ForegroundColor Red
        exit 1
    }
    
    docker cp migrations/add_beneficiary_system.sql ${containerName}:/tmp/migration.sql
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to copy migration file" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Step 2: Running migration in container..." -ForegroundColor Green
    docker-compose exec -T postgres psql -U postgres -d vaccination_db -f /tmp/migration.sql
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=========================================" -ForegroundColor Green
        Write-Host "Migration completed successfully!" -ForegroundColor Green
        Write-Host "=========================================" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "=========================================" -ForegroundColor Red
        Write-Host "Migration failed!" -ForegroundColor Red
        Write-Host "=========================================" -ForegroundColor Red
        exit 1
    }
} else {
    # Method 2: Using Python script
    Write-Host "Step 1: Running Python migration script..." -ForegroundColor Green
    python scripts/run_migration_simple.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=========================================" -ForegroundColor Green
        Write-Host "Migration completed successfully!" -ForegroundColor Green
        Write-Host "=========================================" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "=========================================" -ForegroundColor Red
        Write-Host "Migration failed!" -ForegroundColor Red
        Write-Host "=========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "1. Check your DATABASE_URL in .env file" -ForegroundColor Yellow
        Write-Host "2. Make sure PostgreSQL is running" -ForegroundColor Yellow
        Write-Host "3. If using Docker, start it with: docker-compose up -d" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart backend server" -ForegroundColor Yellow
Write-Host "2. Refresh the dashboard - parent profile should load" -ForegroundColor Yellow
Write-Host ""

