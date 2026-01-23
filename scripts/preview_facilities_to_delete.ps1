# PowerShell script to preview which facilities will be deleted
# This script does NOT delete anything, it only shows what would be deleted
# 
# Usage:
#   .\scripts\preview_facilities_to_delete.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Preview Facilities to Delete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "This script shows what will be deleted WITHOUT actually deleting anything" -ForegroundColor Yellow
Write-Host ""

# Check if Docker is running
$dockerRunning = docker ps 2>&1 | Select-String "postgres"
if (-not $dockerRunning) {
    Write-Host "ERROR: PostgreSQL container is not running" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start the database first:" -ForegroundColor Yellow
    Write-Host "  cd vaccination-backend" -ForegroundColor Yellow
    Write-Host "  docker-compose up -d postgres" -ForegroundColor Yellow
    exit 1
}

# Get container name
$containerName = docker-compose ps -q postgres 2>&1
if ($LASTEXITCODE -ne 0 -or -not $containerName) {
    Write-Host "ERROR: Could not find postgres container" -ForegroundColor Red
    Write-Host "Make sure you're in the vaccination-backend directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found PostgreSQL container: $containerName" -ForegroundColor Green
Write-Host ""

# Copy SQL file to container
$sqlFile = Join-Path $PSScriptRoot "preview_facilities_to_delete.sql"
if (-not (Test-Path $sqlFile)) {
    Write-Host "ERROR: SQL file not found: $sqlFile" -ForegroundColor Red
    exit 1
}

Write-Host "Copying SQL file to container..." -ForegroundColor Yellow
docker cp $sqlFile "${containerName}:/tmp/preview_facilities_to_delete.sql"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to copy SQL file to container" -ForegroundColor Red
    exit 1
}

Write-Host "Executing preview query..." -ForegroundColor Yellow
Write-Host ""

docker-compose exec -T postgres psql -U postgres -d vaccination_db -f /tmp/preview_facilities_to_delete.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Preview completed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "To actually delete the facilities, run:" -ForegroundColor Yellow
    Write-Host "  .\scripts\delete_facilities_except.ps1" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ Error executing SQL script" -ForegroundColor Red
    exit 1
}


