# Run Tab-Based Auth Migration
# This script runs the database migration for tab-based authentication

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Tab-Based Auth Migration" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if docker-compose is running
$dockerRunning = docker ps 2>&1 | Select-String "postgres"
if (-not $dockerRunning) {
    Write-Host "ERROR: Docker containers are not running!" -ForegroundColor Red
    Write-Host "Please start docker-compose first:" -ForegroundColor Yellow
    Write-Host "  docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "Step 1: Copying migration file to container..." -ForegroundColor Green
docker cp vaccination-backend/migrations/add_tab_auth_system.sql $(docker-compose ps -q postgres):/tmp/migration.sql

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to copy migration file" -ForegroundColor Red
    exit 1
}

Write-Host "Step 2: Running migration..." -ForegroundColor Green
docker-compose exec -T postgres psql -U postgres -d vaccination_db -f /tmp/migration.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "Migration completed successfully!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Restart backend: docker-compose restart backend" -ForegroundColor Yellow
    Write-Host "2. Test individual registration/login" -ForegroundColor Yellow
    Write-Host "3. Test hospital registration/login" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host "Migration failed!" -ForegroundColor Red
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host "Check the error messages above" -ForegroundColor Yellow
    exit 1
}


