# OTP-Based Authentication System

## Overview

This is a secure, production-ready OTP-based authentication system for the Baby Vaccination/Immunization Locker App. It replaces traditional password-based authentication with mobile number + OTP verification.

## 🔐 Security Features

- **No Password Storage**: Zero password-related vulnerabilities
- **Hashed OTP Storage**: OTPs are SHA-256 hashed before storing in Redis
- **Rate Limiting**: Max 3 OTP requests per minute per mobile number
- **OTP Expiry**: 3-minute validity window
- **Max Attempts**: 3 verification attempts before OTP invalidation
- **Token-based Auth**: JWT access (15 min) + refresh (7 days) tokens
- **Audit Logging**: All login attempts tracked with IP, device info
- **GDPR/ABHA Ready**: Consent tracking built-in

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │
│ (Flutter/Web)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│          FastAPI Backend                │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │  OTP Service │  │ Token Service│   │
│  └──────┬───────┘  └──────┬───────┘   │
│         │                  │            │
│  ┌──────▼──────────────────▼───────┐   │
│  │   OTP Auth Service              │   │
│  └──────┬──────────────────────────┘   │
│         │                                │
└─────────┼────────────────────────────────┘
          │
    ┌─────┼─────┐
    │     │     │
    ▼     ▼     ▼
┌───────┐ ┌────────┐ ┌──────────┐
│ Redis │ │Postgres│ │SMS Provider│
│ (OTP) │ │(Users) │ │(Msg91/etc) │
└───────┘ └────────┘ └──────────┘
```

## 📋 User Flow

### New User Registration
```
1. User enters mobile number
2. System sends OTP
3. User verifies OTP
4. System detects new user
5. User completes registration (name, role, etc.)
6. System issues JWT tokens
7. User logged in
```

### Existing User Login
```
1. User enters mobile number
2. System sends OTP
3. User verifies OTP
4. System detects existing user
5. System issues JWT tokens
6. User logged in
```

## 🚀 API Endpoints

### 1. Send OTP
**POST** `/api/v1/auth/send-otp`

Request:
```json
{
  "mobile_number": "+919876543210"
}
```

Response:
```json
{
  "success": true,
  "message": "OTP sent successfully",
  "mobile_number": "****3210",
  "expires_in_seconds": 180
}
```

Rate Limit: 3 requests/minute per mobile

---

### 2. Verify OTP
**POST** `/api/v1/auth/verify-otp`

Request:
```json
{
  "mobile_number": "+919876543210",
  "otp": "123456",
  "device_info": "iOS 16.0 / iPhone 13"
}
```

Response (Existing User):
```json
{
  "success": true,
  "message": "Login successful",
  "is_new_user": false,
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Response (New User):
```json
{
  "success": true,
  "message": "OTP verified. Please complete registration.",
  "is_new_user": true,
  "mobile_number": "+919876543210"
}
```

---

### 3. Complete Registration
**POST** `/api/v1/auth/complete-registration`

Request:
```json
{
  "mobile_number": "+919876543210",
  "full_name": "John Doe",
  "role": "parent",
  "email": "john@example.com",
  "consent_given": true
}
```

Response:
```json
{
  "success": true,
  "message": "Registration successful",
  "user_id": 123,
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### 4. Refresh Token
**POST** `/api/v1/auth/refresh-token`

Request:
```json
{
  "refresh_token": "eyJhbGc..."
}
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### 5. Get Current User
**GET** `/api/v1/auth/me`

Headers:
```
Authorization: Bearer <access_token>
```

Response:
```json
{
  "id": 123,
  "mobile_number": "+919876543210",
  "email": "john@example.com",
  "full_name": "John Doe",
  "role": "parent",
  "hospital_id": null,
  "is_active": true,
  "created_at": "2024-01-09T12:00:00Z"
}
```

---

### 6. Logout
**POST** `/api/v1/auth/logout`

Headers:
```
Authorization: Bearer <access_token>
```

Response:
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## ⚙️ Configuration

### Required Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (for OTP storage)
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/vaccination_db

# SMS Provider (choose one: console, msg91, gupshup)
SMS_PROVIDER=console  # Use 'console' for development

# MSG91 Configuration (if using msg91)
MSG91_AUTH_KEY=your-msg91-auth-key
MSG91_TEMPLATE_ID=your-template-id

# Gupshup Configuration (if using gupshup)
GUPSHUP_API_KEY=your-gupshup-api-key
GUPSHUP_SOURCE=your-sender-id

# Application
APP_NAME=Vaccination Locker
ENVIRONMENT=development
DEBUG=True
```

## 📦 SMS Provider Configuration

### Development (Console)
```python
SMS_PROVIDER=console
```
OTPs will be printed to console - perfect for development.

### MSG91
```python
SMS_PROVIDER=msg91
MSG91_AUTH_KEY=your-auth-key
MSG91_TEMPLATE_ID=your-template-id
```

### Gupshup
```python
SMS_PROVIDER=gupshup
GUPSHUP_API_KEY=your-api-key
GUPSHUP_SOURCE=your-sender-id
```

### Adding Custom Provider

1. Extend `SMSProvider` class in `app/services/otp_service.py`
2. Implement `send_otp` method
3. Add to `SMSProviderFactory`

Example:
```python
class CustomSMSProvider(SMSProvider):
    async def send_otp(self, mobile_number: str, otp: str) -> bool:
        # Your SMS sending logic
        return True
```

## 🔒 Security Best Practices

### OTP Storage
- ✅ OTPs are **hashed** (SHA-256) before Redis storage
- ✅ Stored in Redis with **3-minute TTL**
- ✅ **Deleted after** successful verification or max attempts
- ✅ **Never logged** in plain text

### Rate Limiting
- 3 OTP requests per minute per mobile number
- 3 verification attempts per OTP
- Automatic IP-based throttling

### Token Management
- Access tokens: 15 minutes (short-lived)
- Refresh tokens: 7 days
- Tokens include: user_id, mobile_number, role
- Automatic refresh mechanism

### Audit Logging
Every login tracked with:
- User ID & mobile number
- IP address
- User agent
- Device info
- Timestamp

### Mobile Number Security
- Masked in logs (****3210)
- Normalized format (+91XXXXXXXXXX)
- Validated before processing

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    mobile_number VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL, -- parent, hospital, admin
    hospital_id VARCHAR(50),
    device_info VARCHAR(500),
    consent_given CHAR(1) DEFAULT 'N',
    consent_timestamp VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Login Audits Table
```sql
CREATE TABLE login_audits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    mobile_number VARCHAR(15) NOT NULL,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    device_info VARCHAR(500),
    login_method VARCHAR(50) DEFAULT 'otp',
    login_time TIMESTAMP DEFAULT NOW(),
    session_id VARCHAR(255),
    logout_time TIMESTAMP
);
```

## 🧪 Testing

### Test OTP Flow (Development)
```bash
# 1. Start backend
docker-compose up -d

# 2. Send OTP
curl -X POST http://localhost:8000/api/v1/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "+919876543210"}'

# 3. Check console for OTP (in console mode)
# OTP will be printed: 📱 OTP FOR +919876543210: 123456

# 4. Verify OTP
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "+919876543210", "otp": "123456"}'
```

### Testing with Production SMS
1. Set SMS provider in `.env`
2. Configure API keys
3. Test with real mobile number
4. Verify SMS delivery

## 🚨 Error Handling

| Error | Status Code | Description |
|-------|-------------|-------------|
| Invalid mobile format | 400 | Mobile number format invalid |
| Rate limit exceeded | 429 | Too many OTP requests |
| Invalid OTP | 401 | OTP verification failed |
| OTP expired | 401 | OTP validity window passed |
| Max attempts | 401 | 3 verification attempts exhausted |
| User not found | 401 | User doesn't exist |
| Invalid token | 401 | JWT validation failed |
| Inactive user | 403 | User account deactivated |

## 📱 Frontend Integration

See detailed examples:
- [Flutter Example](./FRONTEND_FLUTTER_EXAMPLE.md)
- [Next.js Example](./FRONTEND_NEXTJS_EXAMPLE.md)

## 🔄 Migration from Password-based Auth

### Database Migration
```bash
# Run Alembic migration
alembic upgrade head
```

### Migration Steps
1. ✅ Add `mobile_number` column to users table
2. ✅ Make `email` optional
3. ✅ Remove `password_hash` dependency
4. ✅ Create `login_audits` table
5. ✅ Update frontend to use OTP flow

### Backward Compatibility
- Old endpoints available at `/api/v1/auth/legacy/*` (if needed)
- Gradual migration possible
- Users can be migrated user-by-user

## 📚 Additional Resources

- [API Documentation](http://localhost:8000/docs) - Swagger UI
- [RedOC Documentation](http://localhost:8000/redoc)
- [Frontend Examples](./FRONTEND_FLUTTER_EXAMPLE.md)

## 🆘 Troubleshooting

### OTP not received
1. Check SMS provider configuration
2. Verify mobile number format (+country code)
3. Check SMS provider balance/quota
4. Review backend logs for errors

### OTP expired quickly
- Default: 3 minutes
- Adjust in `OTPService.OTP_EXPIRY_MINUTES`

### Rate limit issues
- Default: 3 requests/minute
- Adjust in `OTPService.MAX_OTP_REQUESTS_PER_WINDOW`

### Redis connection errors
- Verify Redis is running: `docker ps`
- Check REDIS_URL in .env
- Test connection: `redis-cli ping`

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs backend`
- Review error messages in API response
- Verify environment configuration

---

**Status**: ✅ Production Ready

**Version**: 1.0.0

**Last Updated**: January 2024


