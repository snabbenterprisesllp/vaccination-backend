# OTP Authentication API - Request/Response Examples

## Complete Authentication Flows

### Flow 1: New User Registration

#### Step 1: Send OTP
```bash
curl -X POST http://localhost:8000/api/v1/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "+919876543210"
  }'
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "OTP sent successfully",
  "mobile_number": "****3210",
  "expires_in_seconds": 180
}
```

**Error - Rate Limited (429):**
```json
{
  "detail": "Too many OTP requests. Please try again later."
}
```

**Error - Invalid Format (400):**
```json
{
  "detail": "Invalid mobile number format. Use format: +919876543210 or 9876543210"
}
```

---

#### Step 2: Verify OTP (New User)
```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "+919876543210",
    "otp": "123456",
    "device_info": "iPhone 13, iOS 16.0"
  }'
```

**Success Response - New User (200):**
```json
{
  "success": true,
  "message": "OTP verified. Please complete registration.",
  "is_new_user": true,
  "mobile_number": "+919876543210"
}
```

**Error - Invalid OTP (401):**
```json
{
  "detail": "Invalid or expired OTP"
}
```

---

#### Step 3: Complete Registration
```bash
curl -X POST http://localhost:8000/api/v1/auth/complete-registration \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "+919876543210",
    "full_name": "Rahul Kumar",
    "role": "parent",
    "email": "rahul@example.com",
    "consent_given": true
  }'
```

**Success Response (201):**
```json
{
  "success": true,
  "message": "Registration successful",
  "user_id": 123,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsIm1vYmlsZV9udW1iZXIiOiIrOTE5ODc2NTQzMjEwIiwicm9sZSI6InBhcmVudCIsImV4cCI6MTcwNDgwMDAwMCwidHlwZSI6ImFjY2VzcyJ9.signature",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsIm1vYmlsZV9udW1iZXIiOiIrOTE5ODc2NTQzMjEwIiwicm9sZSI6InBhcmVudCIsImV4cCI6MTcwNTQwNDgwMCwidHlwZSI6InJlZnJlc2gifQ.signature",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### Flow 2: Existing User Login

#### Step 1: Send OTP (same as above)

#### Step 2: Verify OTP (Existing User)
```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "+919876543210",
    "otp": "123456",
    "device_info": "Chrome 120, Windows 11"
  }'
```

**Success Response - Existing User (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "is_new_user": false,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

## Token Management

### Refresh Access Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh-token \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error - Invalid Token (401):**
```json
{
  "detail": "Invalid or expired refresh token"
}
```

---

## Protected Endpoints

### Get Current User
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Success Response (200):**
```json
{
  "id": 123,
  "mobile_number": "+919876543210",
  "email": "rahul@example.com",
  "full_name": "Rahul Kumar",
  "role": "parent",
  "hospital_id": null,
  "is_active": true,
  "created_at": "2024-01-09T12:30:00Z"
}
```

**Error - Unauthorized (401):**
```json
{
  "detail": "Could not validate credentials"
}
```

---

### Logout
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## Hospital User Registration

```bash
curl -X POST http://localhost:8000/api/v1/auth/complete-registration \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "+919876543210",
    "full_name": "Apollo Hospital Delhi",
    "role": "hospital",
    "email": "apollo.delhi@example.com",
    "hospital_id": "HOSP12345",
    "consent_given": true
  }'
```

**Success Response (201):**
```json
{
  "success": true,
  "message": "Registration successful",
  "user_id": 124,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

## Error Scenarios

### Scenario 1: OTP Expired
**Request:**
```bash
# Wait 4+ minutes after OTP sent, then verify
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "+919876543210", "otp": "123456"}'
```

**Response (401):**
```json
{
  "detail": "Invalid or expired OTP"
}
```

---

### Scenario 2: Max Attempts Exceeded
**Request:**
```bash
# Try wrong OTP 3 times
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "+919876543210", "otp": "000000"}'
```

**After 3rd attempt (401):**
```json
{
  "detail": "Invalid or expired OTP"
}
```
*Note: OTP is invalidated after 3 failed attempts*

---

### Scenario 3: User Already Registered
**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/complete-registration \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "+919876543210",
    "full_name": "Test User",
    "role": "parent"
  }'
```

**Response (400):**
```json
{
  "detail": "User already registered. Please login."
}
```

---

## Testing Scenarios

### Development Mode (Console SMS)

When `SMS_PROVIDER=console`, OTP is printed to backend logs:

```bash
# Terminal output:
==================================================
📱 OTP FOR +919876543210: 123456
⏰ Valid for 3 minutes
==================================================
```

Use this OTP in your verification request.

---

### Production Mode (Real SMS)

1. Configure SMS provider (MSG91/Gupshup)
2. User receives SMS with OTP
3. User enters OTP in app
4. App sends verification request

---

## JavaScript/TypeScript Examples

### Using Fetch API
```javascript
// Send OTP
async function sendOTP(mobileNumber) {
  const response = await fetch('http://localhost:8000/api/v1/auth/send-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mobile_number: mobileNumber })
  });
  return await response.json();
}

// Verify OTP
async function verifyOTP(mobileNumber, otp) {
  const response = await fetch('http://localhost:8000/api/v1/auth/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mobile_number: mobileNumber,
      otp: otp,
      device_info: navigator.userAgent
    })
  });
  return await response.json();
}

// Get current user
async function getCurrentUser(accessToken) {
  const response = await fetch('http://localhost:8000/api/v1/auth/me', {
    headers: { 'Authorization': `Bearer ${accessToken}` }
  });
  return await response.json();
}
```

---

### Using Axios
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1/auth'
});

// Send OTP
const sendOTP = (mobileNumber) =>
  api.post('/send-otp', { mobile_number: mobileNumber });

// Verify OTP
const verifyOTP = (mobileNumber, otp) =>
  api.post('/verify-otp', {
    mobile_number: mobileNumber,
    otp,
    device_info: navigator.userAgent
  });

// Complete Registration
const completeRegistration = (data) =>
  api.post('/complete-registration', data);

// Get Current User
const getCurrentUser = (token) =>
  api.get('/me', {
    headers: { Authorization: `Bearer ${token}` }
  });
```

---

## Python Examples

```python
import requests

API_BASE = "http://localhost:8000/api/v1/auth"

# Send OTP
response = requests.post(
    f"{API_BASE}/send-otp",
    json={"mobile_number": "+919876543210"}
)
print(response.json())

# Verify OTP
response = requests.post(
    f"{API_BASE}/verify-otp",
    json={
        "mobile_number": "+919876543210",
        "otp": "123456",
        "device_info": "Python Client"
    }
)
data = response.json()
access_token = data.get("access_token")

# Get Current User
response = requests.get(
    f"{API_BASE}/me",
    headers={"Authorization": f"Bearer {access_token}"}
)
print(response.json())
```

---

## Rate Limiting Examples

### Test Rate Limit
```bash
# Send 4 OTP requests rapidly
for i in {1..4}; do
  curl -X POST http://localhost:8000/api/v1/auth/send-otp \
    -H "Content-Type: application/json" \
    -d '{"mobile_number": "+919876543210"}'
  echo "\n---Request $i---\n"
  sleep 1
done
```

First 3 requests succeed, 4th will return 429 (Too Many Requests).

---

**Note**: Replace `http://localhost:8000` with your actual API URL in production.


