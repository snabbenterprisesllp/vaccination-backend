# PowerShell script to delete all facilities except FAC-B6B48A218C8E
# 
# Usage:
#   .\scripts\delete_facilities_except.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Delete Facilities Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
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
$sqlFile = Join-Path $PSScriptRoot "delete_facilities_except.sql"
if (-not (Test-Path $sqlFile)) {
    Write-Host "ERROR: SQL file not found: $sqlFile" -ForegroundColor Red
    exit 1
}

Write-Host "Copying SQL file to container..." -ForegroundColor Yellow
docker cp $sqlFile "${containerName}:/tmp/delete_facilities_except.sql"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to copy SQL file to container" -ForegroundColor Red
    exit 1
}

Write-Host "Executing SQL script..." -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  WARNING: This will delete all facilities except FAC-B6B48A218C8E" -ForegroundColor Red
Write-Host ""

# Check if running in non-interactive mode or if AUTO_CONFIRM is set
$autoConfirm = $env:AUTO_CONFIRM -eq "true" -or $args[0] -eq "-y" -or $args[0] -eq "--yes"

if (-not $autoConfirm) {
    try {
        $confirm = Read-Host "Type 'DELETE' to confirm"
        if ($confirm -ne 'DELETE') {
            Write-Host "Operation cancelled." -ForegroundColor Yellow
            exit 0
        }
    } catch {
        Write-Host "ERROR: Cannot read input. Use -y flag or set AUTO_CONFIRM=true to skip confirmation" -ForegroundColor Red
        Write-Host "Example: .\scripts\delete_facilities_except.ps1 -y" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "Auto-confirm enabled. Proceeding with deletion..." -ForegroundColor Yellow
}

Write-Host ""
docker-compose exec -T postgres psql -U postgres -d vaccination_db -f /tmp/delete_facilities_except.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Successfully deleted facilities!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Error executing SQL script" -ForegroundColor Red
    exit 1
}

