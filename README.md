# Vaccination Locker - Backend API

Production-ready backend API for Baby Immunization & Vaccination Records Management System.

## 🚀 Overview

A comprehensive vaccination tracking and management system for both children (0-18 years) and adults, built with Python, FastAPI, and Google Cloud Platform. This API enables parents, hospitals, and administrators to manage vaccination records securely with ABHA integration, automated reminders, and a unified beneficiary system.

## ✨ Key Features

### Core Functionality
- **Unified Beneficiary System**: Single system managing both ADULT (parents) and CHILD beneficiaries
- **User Authentication**: OAuth2 + JWT-based secure authentication with TAB (Token-Based) hospital authentication
- **Parent & Child Profiles**: Complete medical profiles for both adults and children with QR code access
- **Vaccination Records**: Track all vaccines with hospital verification, vitals capture, and reaction tracking
- **Vaccination Timeline**: Age-based timeline with status tracking (Administered, Due, Upcoming, Due Next) following WHO/Indian schedules
- **Automated Reminders**: Scheduled vaccination reminders (7 days before, 1 day before, on due date, follow-up for missed)
- **Vaccine Master Database**: India Universal Immunization Program (UIP) + Private vaccines with dosage schedules
- **Vitals at Vaccination**: Capture temperature, weight, height, pulse rate, and oxygen saturation during vaccination
- **Hospital Management**: Government & private hospital registry with user management
- **Digital Document Locker**: Secure cloud storage for vaccination cards, birth certificates, discharge summaries, and medical reports organized by category
- **Vaccine Education**: Parent-friendly educational content explaining vaccine importance and safety
- **Vaccination Detail Pages**: Comprehensive views for each vaccination with edit, download, and share capabilities
- **ABHA Integration**: Link with Ayushman Bharat Health Account (future-ready, no direct ABDM API calls)
- **Audit Logging**: Complete audit trail for all operations with JSON-based change tracking
- **QR Code System**: Quick access to beneficiary profiles via QR scanning

### Technical Features
- **Async/Await**: High-performance async operations
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for performance optimization
- **Storage**: Google Cloud Storage for documents
- **Migrations**: Alembic for database migrations
- **API Documentation**: Auto-generated Swagger/OpenAPI docs
- **Docker**: Containerized deployment
- **CI/CD**: GitHub Actions for automated testing & deployment
- **Cloud Run**: Serverless deployment on GCP

## 📋 Prerequisites

- Python 3.11 or higher
- PostgreSQL 15+
- Redis 7+
- Google Cloud Platform account
- Docker & Docker Compose (optional)

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd vaccination-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create `.env` file from the example:

```bash
# Copy example file
cp .env.example .env

# Edit with your configuration
nano .env
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Application secret key
- `JWT_SECRET_KEY`: JWT signing key
- `GCP_PROJECT_ID`: Google Cloud project ID
- `GCS_BUCKET_NAME`: Cloud Storage bucket name
- `ABHA_CLIENT_ID` & `ABHA_CLIENT_SECRET`: ABHA API credentials

### 5. Google Cloud Setup

```bash
# Login to GCP
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Create service account
gcloud iam service-accounts create vaccination-backend

# Download key
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=vaccination-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Create GCS bucket
gsutil mb gs://YOUR_BUCKET_NAME
```

### 6. Database Setup

```bash
# Run migrations
alembic upgrade head

# Seed vaccine master data
python scripts/seed_vaccines.py
```

### 7. Run the Application

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Visit:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 🐳 Docker Setup

### Using Docker Compose (Recommended for Development)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Build Docker Image

```bash
# Build image
docker build -t vaccination-backend .

# Run container
docker run -p 8000:8000 --env-file .env vaccination-backend
```

## 📁 Project Structure

```
vaccination-backend/
├── app/
│   ├── api/                    # API endpoints
│   │   └── v1/
│   │       ├── auth.py         # Authentication endpoints
│   │       ├── auth_tabs.py    # TAB authentication for hospitals
│   │       ├── otp_auth.py     # OTP-based authentication
│   │       ├── beneficiaries.py # Unified beneficiary endpoints
│   │       ├── children.py     # Child profile endpoints
│   │       ├── vaccinations.py # Vaccination endpoints
│   │       ├── vaccines.py     # Vaccine master endpoints
│   │       ├── hospitals.py    # Hospital endpoints
│   │       ├── documents.py    # Document endpoints
│   │       ├── abha.py         # ABHA integration endpoints
│   │       └── reminders.py    # Vaccination reminder endpoints
│   ├── core/                   # Core configuration
│   │   ├── config.py           # App settings
│   │   ├── database.py         # Database connection
│   │   ├── redis.py            # Redis client
│   │   ├── security.py         # Auth & security
│   │   ├── authorization.py    # Role-based authorization
│   │   └── logging.py          # Logging setup
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── beneficiary.py      # Unified beneficiary model
│   │   ├── child_profile.py
│   │   ├── vaccination.py
│   │   ├── vaccine_master.py
│   │   ├── hospital.py
│   │   ├── hospital_user.py    # Hospital user model
│   │   ├── document.py
│   │   ├── abha_link.py
│   │   ├── vaccination_reminder.py # Reminder models
│   │   ├── audit_log.py
│   │   └── login_audit.py      # Login audit tracking
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py
│   │   ├── beneficiary.py      # Beneficiary schemas
│   │   ├── child_profile.py
│   │   ├── vaccination.py
│   │   ├── vaccine_master.py
│   │   ├── hospital.py
│   │   ├── document.py
│   │   ├── abha.py
│   │   ├── reminder.py         # Reminder schemas
│   │   └── otp.py              # OTP schemas
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── hospital_auth_service.py # Hospital authentication
│   │   ├── otp_auth_service.py # OTP authentication
│   │   ├── otp_service.py      # OTP generation/validation
│   │   ├── beneficiary_service.py # Beneficiary management
│   │   ├── child_profile_service.py
│   │   ├── vaccination_service.py
│   │   ├── vaccination_timeline_service.py # Timeline generation
│   │   ├── vaccination_reminder_service.py # Reminder scheduling
│   │   ├── qr_service.py
│   │   └── token_service.py    # Token management
│   ├── utils/                  # Utilities
│   │   ├── gcs_client.py       # GCS operations
│   │   ├── local_storage.py    # Local file storage
│   │   └── audit_logger.py     # Audit logging
│   └── main.py                 # Application entry point
├── alembic/                    # Database migrations
├── scripts/                    # Utility scripts
│   └── seed_vaccines.py        # Seed vaccine data
├── tests/                      # Test suite
├── .github/workflows/          # CI/CD pipelines
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration
└── README.md                   # This file
```

## 🔌 API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - Register new user
- `POST /login` - Login user
- `GET /me` - Get current user
- `PUT /me` - Update current user
- `POST /logout` - Logout user

### Beneficiaries (`/api/v1/beneficiaries`)
- `GET /parent/profile` - Get or create parent beneficiary
- `GET /` - Get all beneficiaries for current user
- `GET /children` - Get all child beneficiaries
- `GET /{beneficiary_id}` - Get specific beneficiary
- `PUT /{beneficiary_id}` - Update beneficiary profile
- `GET /{beneficiary_id}/vaccinations` - Get beneficiary's vaccinations
- `GET /{beneficiary_id}/vaccination-timeline` - Get age-based vaccination timeline
- `GET /qr/{qr_token}` - Get profile by QR (public)

### Child Profiles (`/api/v1/children`)
- `POST /` - Create child profile (auto-creates beneficiary)
- `GET /` - Get all children for current user
- `GET /{child_id}` - Get specific child
- `PUT /{child_id}` - Update child profile
- `DELETE /{child_id}` - Delete child profile (soft delete)
- `GET /{child_id}/vaccination-timeline` - Get child's vaccination timeline

### Vaccinations (`/api/v1/vaccinations`)
- `POST /` - Create vaccination record (supports both child_id and beneficiary_id)
- `GET /` - Get all vaccinations (with filters)
- `GET /{vaccination_id}` - Get specific vaccination with details
- `PUT /{vaccination_id}` - Update vaccination record (including vitals)
- `DELETE /{vaccination_id}` - Delete vaccination (soft delete)
- `POST /schedule` - Create vaccination schedule
- `GET /schedule/child/{child_id}` - Get child's schedules
- `PUT /schedule/{schedule_id}` - Update schedule
- `POST /vial-scan` - Scan vaccine vial barcode
- **Vitals Support**: Temperature, weight, height, pulse rate, oxygen saturation at vaccination time

### Vaccine Master (`/api/v1/vaccines`)
- `GET /` - List all vaccines (with filters)
- `GET /{vaccine_id}` - Get specific vaccine
- `POST /` - Create vaccine (Admin only)
- `PUT /{vaccine_id}` - Update vaccine (Admin only)

### Hospitals (`/api/v1/hospitals`)
- `GET /` - List hospitals (with filters)
- `GET /{hospital_id}` - Get specific hospital
- `POST /search` - Advanced hospital search
- `POST /` - Create hospital (Admin/Hospital only)
- `PUT /{hospital_id}` - Update hospital

### Documents (`/api/v1/documents`)
- `POST /upload` - Upload document (requires child_id)
- `GET /child/{child_id}` - Get child's documents
- `GET /{document_id}` - Get specific document
- `GET /{document_id}/download` - Get signed download URL
- `DELETE /{document_id}` - Delete document
- **Document Types**: Birth certificate, discharge summary, vaccination card, vaccine proof, medical reports, ABHA card, prescriptions, other

### Vaccination Reminders (`/api/v1/reminders`)
- `POST /beneficiaries/{beneficiary_id}/schedule` - Schedule reminders for all upcoming vaccinations
- `GET /beneficiaries/{beneficiary_id}/upcoming` - Get upcoming reminders (within X days)
- `GET /beneficiaries/{beneficiary_id}/next` - Get next upcoming reminder
- `PUT /preferences/beneficiaries/{beneficiary_id}/vaccines/{vaccine_id}` - Update notification preferences
- `GET /preferences/beneficiaries/{beneficiary_id}/vaccines/{vaccine_id}` - Get notification preferences
- **Reminder Types**: 7 days before, 1 day before, on due date, 7 days after missed, birth dose reminders
- **Notification Channels**: Push, SMS, Email (configurable per vaccine)

### ABHA Integration (`/api/v1/abha`)
- `POST /link` - Link ABHA to beneficiary profile
- `GET /child/{child_id}` - Get ABHA link status
- `POST /child/{child_id}/consent` - Update consent
- `GET /profile/{abha_number}` - Get ABHA profile (future-ready)
- `DELETE /child/{child_id}` - Unlink ABHA
- **Note**: ABHA integration is future-ready, no direct ABDM API calls implemented yet

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

## 🗄️ Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# View current version
alembic current

# View migration history
alembic history
```

## 🚀 Deployment

### Deploy to Google Cloud Run

```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Build and submit
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vaccination-backend

# Deploy
gcloud run deploy vaccination-backend \
  --image gcr.io/YOUR_PROJECT_ID/vaccination-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$DATABASE_URL,REDIS_URL=$REDIS_URL
```

### Deploy with CI/CD

Push to `main` branch triggers automatic deployment via GitHub Actions.

## 🔒 Security Features

- **JWT Authentication**: Secure token-based auth
- **Password Hashing**: Bcrypt password hashing
- **CORS Protection**: Configurable CORS policies
- **Rate Limiting**: API rate limiting
- **Input Validation**: Pydantic schema validation
- **SQL Injection Prevention**: ORM-based queries
- **Audit Logging**: Complete audit trail
- **Role-Based Access**: RBAC for endpoints

## 📊 Monitoring & Logging

Logs are structured in JSON format for easy parsing:

```python
{
  "timestamp": "2024-01-09T10:30:00Z",
  "level": "INFO",
  "message": "User registered",
  "user_id": 123,
  "email": "user@example.com"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `REDIS_URL` | Redis connection string | Yes | - |
| `SECRET_KEY` | App secret key | Yes | - |
| `JWT_SECRET_KEY` | JWT signing key | Yes | - |
| `GCP_PROJECT_ID` | GCP project ID | Yes | - |
| `GCS_BUCKET_NAME` | Cloud Storage bucket | Yes | - |
| `ABHA_CLIENT_ID` | ABHA API client ID | Yes | - |
| `ABHA_CLIENT_SECRET` | ABHA API secret | Yes | - |
| `SMTP_HOST` | Email SMTP host | No | smtp.gmail.com |
| `SMTP_USER` | Email SMTP user | No | - |
| `ENVIRONMENT` | Environment (dev/prod) | No | development |
| `DEBUG` | Debug mode | No | True |
| `LOG_LEVEL` | Logging level | No | INFO |

## 📄 License

MIT License - see LICENSE file for details

## 📞 Support

For support, email support@vaccinationlocker.com or open an issue.

## 🙏 Acknowledgments

- India Universal Immunization Program
- Ayushman Bharat Digital Mission (ABDM)
- FastAPI Framework
- Google Cloud Platform

