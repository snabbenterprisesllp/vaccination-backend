# Bootstrap Token Guide

## What is a Bootstrap Token?

The bootstrap token is a **secret password** that allows you to create the first SUPER_ADMIN user. It's a security measure to prevent unauthorized SUPER_ADMIN account creation.

## How to Set the Bootstrap Token

### Option 1: Set in `.env` File (Recommended)

1. Open or create `.env` file in `vaccination-backend/` directory
2. Add this line:

```env
SUPER_ADMIN_BOOTSTRAP_TOKEN=your-secret-token-here
```

**Example:**
```env
SUPER_ADMIN_BOOTSTRAP_TOKEN=my-super-secure-token-2024-xyz123
```

### Option 2: Generate a Secure Token

You can generate a secure random token using:

**On Windows (PowerShell):**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

**On Linux/Mac:**
```bash
openssl rand -hex 32
```

**Or use Python:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

**Or use an online generator:**
- Visit: https://www.random.org/strings/
- Generate a 32-character random string

## Example Bootstrap Tokens

Here are some examples (use your own unique token):

```
SUPER_ADMIN_BOOTSTRAP_TOKEN=super-admin-2024-secure-key-xyz789
SUPER_ADMIN_BOOTSTRAP_TOKEN=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
SUPER_ADMIN_BOOTSTRAP_TOKEN=MySecureToken@2024#VaccinationSystem
```

## Quick Setup

### For Development/Testing:

1. **Simple Token (Easy to remember):**
```env
SUPER_ADMIN_BOOTSTRAP_TOKEN=dev-bootstrap-123
```

2. **Or disable token requirement:**
```env
ALLOW_SUPER_ADMIN_SIGNUP=true
```

### For Production:

**Use a strong, random token:**
```env
SUPER_ADMIN_BOOTSTRAP_TOKEN=K8mN2pQ5rS9tU3vW7xY1zA4bC6dE8fG0hI2jK4lM6nO8pQ0rS2tU4vW6xY8zA0
```

## How to Use

1. **Set the token in `.env`:**
```env
SUPER_ADMIN_BOOTSTRAP_TOKEN=your-token-here
```

2. **Restart your backend server** (if running)

3. **Register as SUPER_ADMIN:**
   - Go to: `http://localhost:3000/register`
   - Click "Super Admin" tab
   - Enter the **same token** in the "Bootstrap Token" field
   - Complete registration

## Security Best Practices

✅ **DO:**
- Use a long, random token (at least 32 characters)
- Keep the token secret
- Don't commit `.env` file to Git
- Use different tokens for development and production
- Change token after creating first SUPER_ADMIN (optional)

❌ **DON'T:**
- Use simple passwords like "123456" or "admin"
- Share the token publicly
- Commit `.env` to version control
- Use the same token in multiple environments

## Alternative: Disable Token Requirement (Development Only)

For development/testing, you can disable the token requirement:

```env
ALLOW_SUPER_ADMIN_SIGNUP=true
```

**⚠️ WARNING:** Only use this in development! Never enable this in production.

## Troubleshooting

**Error: "Invalid bootstrap token"**
- Check that token in `.env` matches the token you entered
- Make sure there are no extra spaces
- Restart backend server after changing `.env`

**Token not working:**
- Verify `.env` file is in `vaccination-backend/` directory
- Check that `SUPER_ADMIN_BOOTSTRAP_TOKEN` is spelled correctly
- Ensure backend server has been restarted

## Quick Example

```env
# vaccination-backend/.env

# Other settings...
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/vaccination_db
SECRET_KEY=your-secret-key

# SUPER_ADMIN Bootstrap Token
SUPER_ADMIN_BOOTSTRAP_TOKEN=my-secure-bootstrap-token-2024
```

Then in the registration form, enter: `my-secure-bootstrap-token-2024`

## Summary

**For Quick Testing:**
```env
SUPER_ADMIN_BOOTSTRAP_TOKEN=test-token-123
```

**For Production:**
Generate a secure random token (32+ characters) and set it in `.env`

