# ABHA M1 API Endpoints

## Overview

This document lists all ABHA endpoints available in the current implementation. The implementation follows **ABHA M1 scope only** - ABHA creation, linking, and demographic profile fetch.

## Base URL

All ABHA endpoints are prefixed with `/api/v1/abha`

## Authentication

All endpoints require authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## M1 Endpoints (Primary - Currently Used)

### 1. Initiate ABHA Linking

**Endpoint:** `POST /api/v1/abha/initiate`

**Description:** Initiates ABHA creation/linking process. Sends OTP via ABDM Gateway.

**Request Body:**
```json
{
  "person_type": "parent" | "child",
  "person_id": 123,
  "auth_method": "MOBILE_OTP" | "AADHAAR_OTP",
  "mobile_number": "+919876543210",  // Optional for MOBILE_OTP (uses user's mobile if not provided)
  "aadhaar_number": "123456789012"   // Required for AADHAAR_OTP
}
```

**Response:**
```json
{
  "transaction_id": "txn_abc123xyz",
  "message": "OTP sent successfully. Please verify to complete ABHA linking."
}
```

**Status Codes:**
- `200 OK` - OTP sent successfully
- `400 Bad Request` - Invalid request parameters
- `403 Forbidden` - Access denied
- `404 Not Found` - Person not found
- `503 Service Unavailable` - ABHA not configured

**Used By:**
- Frontend: `ABHALinkModal` component
- Service: `abhaService.initiate()`

---

### 2. Verify OTP and Complete ABHA Linking

**Endpoint:** `POST /api/v1/abha/verify`

**Description:** Verifies OTP with ABDM Gateway and completes ABHA linking. Fetches demographic profile.

**Request Body:**
```json
{
  "transaction_id": "txn_abc123xyz",
  "otp": "123456",
  "auth_method": "MOBILE_OTP" | "AADHAAR_OTP",
  "person_type": "parent" | "child",
  "person_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "abha_linked": true,
  "abha_number": "12****90",  // Masked ABHA number
  "abha_address": "12****90@abdm",
  "demographic": {
    "name": "John Doe",
    "date_of_birth": "1990-01-01",
    "gender": "male",
    "mobile": "+919876543210",
    "email": "john@example.com"
  },
  "message": "ABHA linked successfully"
}
```

**Status Codes:**
- `200 OK` - ABHA linked successfully
- `400 Bad Request` - Invalid OTP or request
- `403 Forbidden` - Access denied
- `404 Not Found` - Person not found
- `500 Internal Server Error` - Verification failed

**Used By:**
- Frontend: `ABHALinkModal` component
- Service: `abhaService.verify()`

---

## Legacy/Backward Compatibility Endpoints

These endpoints exist for backward compatibility but are **NOT used by the M1 implementation**:

### 3. Link ABHA (Legacy)

**Endpoint:** `POST /api/v1/abha/link`

**Description:** Legacy endpoint for linking ABHA to child profile (without ABDM Gateway integration).

**Request Body:**
```json
{
  "child_id": 123,
  "abha_number": "12****90",
  "abha_address": "12****90@abdm",
  "consent_given": true
}
```

**Status:** ⚠️ Legacy - Not used in M1 flow

---

### 4. Get ABHA Link for Child

**Endpoint:** `GET /api/v1/abha/child/{child_id}`

**Description:** Get ABHA link information for a child.

**Path Parameters:**
- `child_id` (integer) - Child profile ID

**Response:**
```json
{
  "id": 1,
  "child_id": 123,
  "abha_number": "12****90",
  "abha_address": "12****90@abdm",
  "consent_given": true,
  "consent_date": "2024-01-01T00:00:00Z",
  "linked": true,
  "linked_at": "2024-01-01T00:00:00Z"
}
```

**Status:** ⚠️ Legacy - Not used in M1 flow

---

### 5. Update ABHA Consent

**Endpoint:** `POST /api/v1/abha/child/{child_id}/consent`

**Description:** Update consent for ABHA link (M2 placeholder).

**Path Parameters:**
- `child_id` (integer) - Child profile ID

**Request Body:**
```json
{
  "consent_given": true,
  "consent_duration_days": 365
}
```

**Status:** ⚠️ M2 placeholder - Not used in M1

---

### 6. Get ABHA Profile

**Endpoint:** `GET /api/v1/abha/profile/{abha_number}`

**Description:** Get ABHA profile information (mock implementation).

**Path Parameters:**
- `abha_number` (string) - ABHA number

**Response:**
```json
{
  "abha_number": "12****90",
  "abha_address": "12****90@abdm",
  "name": "Mock User",
  "date_of_birth": "2020-01-01",
  "gender": "male",
  "mobile": null,
  "email": null
}
```

**Status:** ⚠️ Mock - Not integrated with ABDM Gateway

---

### 7. Unlink ABHA

**Endpoint:** `DELETE /api/v1/abha/child/{child_id}`

**Description:** Unlink ABHA from child profile.

**Path Parameters:**
- `child_id` (integer) - Child profile ID

**Response:** `204 No Content`

**Status:** ⚠️ Legacy - Soft delete only

---

## Frontend Service Usage

The frontend uses only the M1 endpoints via `abhaService`:

```typescript
// Initiate ABHA linking
await abhaService.initiate({
  person_type: 'parent',
  person_id: user.id,
  auth_method: 'MOBILE_OTP',
  mobile_number: '+919876543210'
})

// Verify OTP and complete linking
await abhaService.verify({
  transaction_id: 'txn_abc123',
  otp: '123456',
  auth_method: 'MOBILE_OTP',
  person_type: 'parent',
  person_id: user.id
})
```

---

## ABDM Gateway Endpoints (Internal)

The backend internally calls these ABDM Gateway endpoints:

1. **Get Access Token**
   - `POST {ABHA_BASE_URL}/v1/auth/token`
   - Uses client credentials flow

2. **Initiate Mobile OTP**
   - `POST {ABHA_BASE_URL}/v1/registration/mobile/generateOtp`

3. **Initiate Aadhaar OTP**
   - `POST {ABHA_BASE_URL}/v1/registration/aadhaar/generateOtp`

4. **Verify Mobile OTP**
   - `POST {ABHA_BASE_URL}/v1/registration/mobile/verifyOtp`

5. **Verify Aadhaar OTP**
   - `POST {ABHA_BASE_URL}/v1/registration/aadhaar/verifyOtp`

6. **Get Demographic Profile**
   - `GET {ABHA_BASE_URL}/v1/profile/{abha_address}`

---

## Summary

**Active M1 Endpoints (Used):**
- ✅ `POST /api/v1/abha/initiate` - Initiate ABHA linking
- ✅ `POST /api/v1/abha/verify` - Verify OTP and complete linking

**Legacy Endpoints (Not Used in M1):**
- ⚠️ `POST /api/v1/abha/link` - Legacy linking
- ⚠️ `GET /api/v1/abha/child/{child_id}` - Get link info
- ⚠️ `POST /api/v1/abha/child/{child_id}/consent` - M2 placeholder
- ⚠️ `GET /api/v1/abha/profile/{abha_number}` - Mock profile
- ⚠️ `DELETE /api/v1/abha/child/{child_id}` - Unlink

**Note:** Only the two M1 endpoints (`/initiate` and `/verify`) are actively used by the frontend. The other endpoints exist for backward compatibility but are not part of the M1 flow.

