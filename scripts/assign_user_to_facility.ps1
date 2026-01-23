# PowerShell script to assign a user to a facility
# This script assigns user with mobile_number '7680972845' to facility 'FAC-B6B48A218C8E'

$CONTAINER_NAME = "vaccination-backend-postgres-1"
$DB_NAME = "vaccination_db"
$DB_USER = "postgres"
$DB_PASSWORD = "postgres"
$SQL_FILE = "scripts/assign_user_to_facility.sql"

Write-Host "🔍 Assigning user 7680972845 to facility FAC-B6B48A218C8E..." -ForegroundColor Cyan

# Check if container is running
$containerRunning = docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}"
if (-not $containerRunning) {
    Write-Host "❌ Error: PostgreSQL container '$CONTAINER_NAME' is not running." -ForegroundColor Red
    Write-Host "   Please start the container first with: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

# Check if SQL file exists
if (-not (Test-Path $SQL_FILE)) {
    Write-Host "❌ Error: SQL file '$SQL_FILE' not found." -ForegroundColor Red
    exit 1
}

Write-Host "📋 Executing SQL script..." -ForegroundColor Yellow

# Execute SQL script
$env:PGPASSWORD = $DB_PASSWORD
docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME < $SQL_FILE

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ User assignment completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. User should now be able to login with mobile number 7680972845" -ForegroundColor White
    Write-Host "   2. Make sure to select 'Hospital' tab during login" -ForegroundColor White
    Write-Host "   3. User will have 'doctor' role in the facility" -ForegroundColor White
} else {
    Write-Host "❌ Error executing SQL script. Exit code: $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

