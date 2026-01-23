# Fix: "Invalid bootstrap token or SUPER_ADMIN signup is disabled"

## Quick Fix Options

### Option 1: Enable Signup Without Token (Easiest - Development Only)

Add this to your `vaccination-backend/.env` file:

```env
ALLOW_SUPER_ADMIN_SIGNUP=true
```

**Then restart your backend server.**

After this, you can register as SUPER_ADMIN without entering any bootstrap token in the form.

### Option 2: Set Bootstrap Token

1. **Add to `.env` file:**
```env
SUPER_ADMIN_BOOTSTRAP_TOKEN=my-secure-token-123
```

2. **Restart backend server**

3. **Use the same token in registration form:**
   - Go to registration page
   - Enter `my-secure-token-123` in the "Bootstrap Token" field

## Step-by-Step Fix

### Step 1: Open `.env` file

Navigate to: `vaccination-backend/.env`

### Step 2: Add one of these lines

**For easy testing (no token needed):**
```env
ALLOW_SUPER_ADMIN_SIGNUP=true
```

**OR for secure setup (with token):**
```env
SUPER_ADMIN_BOOTSTRAP_TOKEN=test-token-123
```

### Step 3: Restart Backend Server

**If using Docker:**
```bash
docker-compose restart backend
```

**If running directly:**
- Stop the server (Ctrl+C)
- Start again: `python -m uvicorn app.main:app --reload`
```

### Step 4: Try Registration Again

- If you set `ALLOW_SUPER_ADMIN_SIGNUP=true`: Leave bootstrap token field empty or enter anything
- If you set `SUPER_ADMIN_BOOTSTRAP_TOKEN=test-token-123`: Enter `test-token-123` in the form

## Common Issues

### Issue 1: .env file not being read
- Make sure `.env` is in `vaccination-backend/` directory
- Check file name is exactly `.env` (not `.env.txt` or `.env.example`)
- Restart backend server after changing `.env`

### Issue 2: Token mismatch
- Token in `.env` must exactly match token in form
- No extra spaces before/after
- Case-sensitive

### Issue 3: Server not restarted
- Changes to `.env` only take effect after restart
- Always restart backend after modifying `.env`

## Recommended Setup for Development

```env
# vaccination-backend/.env

# Enable SUPER_ADMIN signup without token (development only)
ALLOW_SUPER_ADMIN_SIGNUP=true
```

This is the easiest option for development/testing.

## Recommended Setup for Production

```env
# vaccination-backend/.env

# Use a secure random token
SUPER_ADMIN_BOOTSTRAP_TOKEN=lmQZkukteVslbJ7iLjSlyuSwdGy42ZHk3XU5o8cFGN4
```

Then use the same token in the registration form.




