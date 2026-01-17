# ABHA M1 Configuration Guide

## Overview

ABHA (Ayushman Bharat Health Account) M1 integration requires ABDM Gateway credentials to authenticate and communicate with the ABDM platform.

## Required Environment Variables

To enable ABHA M1 functionality, you need to set the following environment variables:

```bash
# ABHA Integration (Required for ABHA features)
ABHA_BASE_URL=https://dev.abdm.gov.in/gateway  # ABDM Gateway URL (use sandbox URL for testing)
ABHA_CLIENT_ID=your_client_id                  # Your ABDM Gateway client ID
ABHA_CLIENT_SECRET=your_client_secret          # Your ABDM Gateway client secret
ABHA_ENABLED=true                              # Set to true to enable ABHA features
```

## Getting ABDM Gateway Credentials

1. **Register with ABDM**: Visit [ABDM Developer Portal](https://abdm.gov.in/)
2. **Create Application**: Register your application and get client credentials
3. **Sandbox Access**: For testing, use the ABDM sandbox environment
4. **Production Access**: For production, complete ABDM certification process

## Configuration Steps

### Option 1: Environment Variables (Recommended)

Add to your `.env` file or environment:

```bash
ABHA_BASE_URL=https://dev.abdm.gov.in/gateway
ABHA_CLIENT_ID=your_client_id_here
ABHA_CLIENT_SECRET=your_client_secret_here
ABHA_ENABLED=true
```

### Option 2: Docker Compose

Add to `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - ABHA_BASE_URL=https://dev.abdm.gov.in/gateway
      - ABHA_CLIENT_ID=${ABHA_CLIENT_ID}
      - ABHA_CLIENT_SECRET=${ABHA_CLIENT_SECRET}
      - ABHA_ENABLED=true
```

## Testing Without ABDM Gateway

If you don't have ABDM Gateway credentials yet, you can:

1. **Disable ABHA**: Set `ABHA_ENABLED=false` (default)
2. **UI will show**: "ABHA integration is not configured" message
3. **Features remain**: All other vaccination features work normally

## Error Messages

### "Failed to authenticate with ABDM Gateway"
- **Cause**: Missing or incorrect ABDM Gateway credentials
- **Solution**: Verify `ABHA_BASE_URL`, `ABHA_CLIENT_ID`, and `ABHA_CLIENT_SECRET` are set correctly

### "Cannot connect to ABDM Gateway"
- **Cause**: Network issue or incorrect `ABHA_BASE_URL`
- **Solution**: 
  - Verify the URL is correct
  - Check network connectivity
  - For sandbox: Use `https://dev.abdm.gov.in/gateway`
  - For production: Use `https://abdm.gov.in/gateway`

### "ABHA integration is not enabled"
- **Cause**: `ABHA_ENABLED=false` or not set
- **Solution**: Set `ABHA_ENABLED=true` in environment variables

## ABDM Gateway URLs

- **Sandbox/Development**: `https://dev.abdm.gov.in/gateway`
- **Production**: `https://abdm.gov.in/gateway` (after certification)

## Notes

- ABHA M1 only requires demographic profile access
- No health records are synced in M1
- Aadhaar numbers are never stored (only hashed before sending)
- ABHA numbers are masked before storage

