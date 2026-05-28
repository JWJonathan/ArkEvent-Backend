# Email Verification System Setup Guide

This guide explains how to set up and use the email verification system in your ArkEvent Django backend.

## System Overview

The email verification system includes:
- **User Registration**: Generate and send verification codes via email
- **Email Verification**: Users verify their email with the code
- **Password Reset**: Send reset codes for password recovery
- **Async Email Sending**: Uses Celery + Redis for background tasks

## Prerequisites

The following are already installed in your `requirements.txt`:
- ✅ Django 6.0.5
- ✅ Celery 5.6.3
- ✅ Redis 7.4.0
- ✅ djangorestframework 3.17.1

## Configuration Steps

### 1. Environment Variables (.env)

Add these to your `.env` file:

```bash
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
DEFAULT_FROM_EMAIL=noreply@arkevent.com
SERVER_EMAIL=server@arkevent.com

# Email Verification Settings
EMAIL_VERIFICATION_TIMEOUT_HOURS=24
EMAIL_VERIFICATION_CODE_LENGTH=6

# Redis (for Celery - already configured)
REDIS_URL=redis://localhost:6379/0
```

### 2. Gmail Configuration (if using Gmail)

To use Gmail for sending emails:

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an "App Password":
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer"
   - Copy the 16-character password
3. Use this password as `EMAIL_HOST_PASSWORD` in your `.env`

**Note:** Gmail has a sending limit of 500 emails/day for personal accounts.

### 3. Start Required Services

#### Start Redis (if not running):
```bash
redis-server
```

#### Start Celery Worker (new terminal):
```bash
cd /home/jwj/ArkEvent-Backend
source venv/bin/activate
celery -A arkevent_backend worker -l info
```

#### Start Django Development Server:
```bash
cd /home/jwj/ArkEvent-Backend
source venv/bin/activate
python3 manage.py runserver 8030
```

## API Endpoints

### 1. User Registration
**POST** `/api/users/auth/register/`

```json
{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+50932277129",
    "role": "user"
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "data": {
        "detail": "Inscription réussie. Veuillez vérifier votre email.",
        "user_id": "edfcf7e2-7ae6-429f-810b-78f089170d0a"
    },
    "message": ""
}
```

**What happens:**
- User is created with `email_verified = False`
- A 6-digit verification code is generated
- Email with the code is sent asynchronously via Celery

### 2. Verify Email
**POST** `/api/users/auth/verify-email/` (Requires Authentication)

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "otp": "123456"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "detail": "Email vérifié avec succès."
    },
    "message": ""
}
```

**What happens:**
- Code is verified against stored value
- `email_verified` is set to `True`
- `is_verified` is set to `True`
- Verification code is cleared from database

### 3. Resend Verification Code
**POST** `/api/users/auth/resend-code/`

**Request:**
```json
{
    "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "detail": "Code de vérification renvoyé à votre email."
    },
    "message": ""
}
```

### 4. Request Password Reset
**POST** `/api/users/auth/password-reset-request/`

**Request:**
```json
{
    "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "detail": "Si l'email existe, un code de réinitialisation a été envoyé."
    },
    "message": ""
}
```

### 5. Confirm Password Reset
**POST** `/api/users/auth/password-reset-confirm/`

**Request:**
```json
{
    "email": "user@example.com",
    "otp": "123456",
    "new_password": "NewSecurePass123!"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "detail": "Mot de passe réinitialisé avec succès."
    },
    "message": ""
}
```

## File Structure

Here's what was created/modified:

```
apps/users/
├── models.py                          # Added email_verified, email_verification_code
├── views.py                           # Updated with real verification logic
├── serializers.py                     # Email verification serializers
├── tasks.py                           # NEW: Celery tasks for email sending
├── migrations/
│   └── 0009_*.py                      # NEW: Email verification fields migration

arkevent_backend/
├── settings.py                        # Added email configuration
├── celery.py                          # Already configured

.env                                    # Add email settings here
```

## Testing the System

### Test 1: Register a User
```bash
curl -X POST http://127.0.0.1:8030/api/users/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test User",
    "first_name": "Test",
    "last_name": "User",
    "phone": "+50912345678",
    "role": "user"
  }'
```

Check your email for the verification code!

### Test 2: Verify Email
1. Get the access token from login
2. Verify with the code sent to your email

```bash
curl -X POST http://127.0.0.1:8030/api/users/auth/verify-email/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"otp": "123456"}'
```

### Test 3: Check Celery Worker
In the Celery worker terminal, you should see:
```
[2026-05-28 16:50:23,123: INFO/MainProcess] Task apps.users.tasks.send_verification_email[...] received
[2026-05-28 16:50:23,456: INFO/ForkPoolWorker-1] Task apps.users.tasks.send_verification_email[...] succeeded
```

## Troubleshooting

### Email Not Being Sent?

1. **Check Celery Worker is Running**
   ```bash
   # Terminal should show worker messages
   celery -A arkevent_backend worker -l info
   ```

2. **Check Redis Connection**
   ```bash
   redis-cli ping
   # Should respond: PONG
   ```

3. **Check Email Configuration in .env**
   - Ensure EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are correct
   - For Gmail, use app-specific password, not your regular password

4. **Check Django Logs**
   - Look for email backend errors in Django server output
   - Check database for email_verification_code field

### Verification Code Issues?

- Code expires after 24 hours (configurable via EMAIL_VERIFICATION_TIMEOUT_HOURS)
- Use `/api/users/auth/resend-code/` to get a new code
- Code is cleared after successful verification

## Database Schema

New fields added to `arkevent.users` table:

| Field | Type | Description |
|-------|------|-------------|
| `email_verified` | BOOLEAN | Whether email is verified |
| `email_verification_code` | VARCHAR(10) | Current verification code |

## Celery Tasks

### `send_verification_email(user_id, code)`
Sends registration verification email to user.

**Parameters:**
- `user_id`: UUID of the user
- `code`: 6-digit verification code

**Returns:**
```python
{
    'success': True/False,
    'message': 'Email sent to user@example.com' or error message
}
```

### `send_password_reset_email(user_id, code)`
Sends password reset email to user.

**Parameters:**
- `user_id`: UUID of the user
- `code`: 6-digit reset code

## Email Template Customization

To customize the email templates, edit the HTML in:
- `apps/users/tasks.py` - Functions `send_verification_email()` and `send_password_reset_email()`

Current template features:
- Responsive HTML design
- ArkEvent branding (purple #5B3FFF)
- French language content
- Plain text fallback

## Production Considerations

1. **Email Provider:** Consider using SendGrid, AWS SES, or MailChimp for production
2. **Rate Limiting:** Add rate limiting to prevent code spam
3. **Code Expiration:** Implement code expiration (currently 24 hours)
4. **Security:** Never log verification codes
5. **Monitoring:** Monitor Celery task failures

## Additional Features to Add

1. **Email Verification Expiration:**
   ```python
   # Track when code was sent
   email_code_sent_at = models.DateTimeField(null=True, blank=True)
   ```

2. **Rate Limiting:**
   ```python
   from django_ratelimit.decorators import ratelimit
   ```

3. **SMS Verification:**
   - Add Twilio for SMS-based verification

4. **Email Templates:**
   - Use Django templates instead of hardcoded HTML

## Support

For issues or questions:
1. Check the Celery worker output
2. Check Redis connectivity
3. Verify email configuration in .env
4. Check Django logs for validation errors
