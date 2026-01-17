# Quick Start Guide

Get the Vaccination Locker Backend running in 5 minutes!

## 🚀 Quick Setup with Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd vaccination-backend

# 2. Create environment file
cp .env.template .env

# 3. Edit .env with minimal required settings
nano .env
# Set: SECRET_KEY, JWT_SECRET_KEY, GCP_PROJECT_ID, GCS_BUCKET_NAME

# 4. Start all services (PostgreSQL, Redis, Backend)
docker-compose up -d

# 5. Run migrations
docker-compose exec backend alembic upgrade head

# 6. Seed vaccine data
docker-compose exec backend python scripts/seed_vaccines.py

# 7. Access the API
# - API: http://localhost:8000
# - Docs: http://localhost:8000/api/v1/docs
```

## 📝 Manual Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up PostgreSQL
createdb vaccination_db

# 4. Set up Redis
# Install and start Redis server

# 5. Configure environment
cp .env.template .env
# Edit .env with your settings

# 6. Run migrations
alembic upgrade head

# 7. Seed data
python scripts/seed_vaccines.py

# 8. Start the server
uvicorn app.main:app --reload
```

## 🧪 Test the API

```bash
# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "parent@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe",
    "role": "parent"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "parent@example.com",
    "password": "SecurePass123"
  }'
```

## 📚 Next Steps

1. Visit Swagger docs: http://localhost:8000/api/v1/docs
2. Create a child profile
3. Add vaccination records
4. Upload documents
5. Generate QR codes

## 🛠️ Common Commands

```bash
# View logs
docker-compose logs -f backend

# Run tests
pytest

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Access database
docker-compose exec postgres psql -U postgres -d vaccination_db

# Access Redis CLI
docker-compose exec redis redis-cli
```

## 🐛 Troubleshooting

### Database connection error
- Check if PostgreSQL is running
- Verify DATABASE_URL in .env

### Redis connection error
- Check if Redis is running
- Verify REDIS_URL in .env

### GCS upload error
- Check if service account key exists
- Verify GCP credentials
- Check bucket permissions

## 📞 Need Help?

Check the full [README.md](README.md) for detailed documentation.

