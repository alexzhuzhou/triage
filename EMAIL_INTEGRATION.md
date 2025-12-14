# Email Integration Guide

## Overview

The Triage system now supports **real email integration** via IMAP, allowing automatic processing of incoming emails from Gmail, Outlook, or any IMAP-compatible email provider.

## Features

 **IMAP Email Fetching** - Connect to Gmail/Outlook using app passwords
 **Automatic Email Parsing** - Converts email format to internal schema
 **Background Polling** - Automatically checks for new emails every 60 seconds (configurable)
 **Manual Triggering** - On-demand email fetching via API endpoint
 **Simple Attachment Handling** - Extracts filename and metadata
 **No OAuth Required** - Uses app passwords for simplified setup

## Setup Instructions

### 1. Generate Gmail App Password

1. **Enable 2-Factor Authentication**:
   - Go to your Google Account: https://myaccount.google.com
   - Navigate to Security → 2-Step Verification
   - Follow the setup instructions

2. **Generate App Password**:
   - Visit: https://myaccount.google.com/apppasswords
   - Select "Mail" as the app
   - Select your device
   - Click "Generate"
   - Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

3. **Remove spaces** from the password: `abcdefghijklmnop`

### 2. Configure Environment Variables

Edit your `.env` file (or create from `.env.example`):

```bash
# Enable email integration
EMAIL_ENABLED=true

# Gmail configuration
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop
EMAIL_PORT=993
EMAIL_USE_SSL=true

# Polling interval in seconds (default: 60)
EMAIL_POLL_INTERVAL=60
```

### 3. For Outlook/Other Providers

**Outlook:**
```bash
EMAIL_IMAP_SERVER=outlook.office365.com
EMAIL_ADDRESS=your-email@outlook.com
EMAIL_PASSWORD=your-app-password
```

**Yahoo:**
```bash
EMAIL_IMAP_SERVER=imap.mail.yahoo.com
EMAIL_ADDRESS=your-email@yahoo.com
EMAIL_PASSWORD=your-app-password
```

## Usage

### Automatic Background Polling

When `EMAIL_ENABLED=true`, the system automatically:
1. Connects to your email server every 60 seconds (configurable)
2. Fetches unread emails
3. Parses and processes them through the LLM pipeline
4. Marks them as read

**Start the server:**
```bash
uvicorn app.main:app --reload
```

**Check logs:**
```
INFO: Starting email poller (interval: 60s)
INFO: Polling for emails (poll #1)
INFO: Found 2 unread email(s)
INFO: Successfully processed email: New IME Referral – Sarah Martinez
```

### Manual Polling (On-Demand)

Trigger email fetching manually via API:

**Using cURL:**
```bash
curl -X POST http://localhost:8000/email-polling/manual-poll
```

**Using Interactive Docs:**
1. Visit http://localhost:8000/docs
2. Navigate to `/email-polling/manual-poll`
3. Click "Try it out" → "Execute"

**Response:**
```json
{
  "processed": 2,
  "failed": 0,
  "emails": [
    {
      "subject": "New IME Referral – Sarah Martinez",
      "email_id": "uuid-here",
      "case_id": "case-uuid-here",
      "status": "processed"
    }
  ]
}
```

### Check Configuration Status

```bash
curl http://localhost:8000/email-polling/status
```

**Response:**
```json
{
  "enabled": true,
  "configured": true,
  "imap_server": "imap.gmail.com",
  "email_address": "your-email@gmail.com",
  "poll_interval": 60,
  "port": 993,
  "use_ssl": true
}
```

## How It Works

### Email Processing Flow

```
1. Email arrives → Gmail/Outlook Inbox
                       ↓
2. IMAP Fetcher ← Fetch unread emails (every 60s)
                       ↓
3. Email Parser ← Convert to EmailIngest schema
                       ↓
4. LLM Extraction ← Extract case data
                       ↓
5. Database ← Store case, email, attachments
                       ↓
6. Mark as Read ← Email marked as processed
```

### Email Format Conversion

**Input (Raw Email):**
```
From: referrals@lawfirm.com
To: scheduling@imegroup.com
Subject: New IME Referral
Body: Patient: John Doe, Case: NF-123...
Attachments: medical_records.pdf
```

**Output (EmailIngest Schema):**
```json
{
  "subject": "New IME Referral",
  "sender": "referrals@lawfirm.com",
  "recipients": ["scheduling@imegroup.com"],
  "body": "Patient: John Doe, Case: NF-123...",
  "attachments": [
    {
      "filename": "medical_records.pdf",
      "content_type": "application/pdf",
      "text_content": null
    }
  ],
  "received_at": "2025-04-05T10:30:00Z"
}
```

## Testing

### Send a Test Email

1. Send an email to your configured email address
2. Include case details in the body:
```
New IME Referral

Patient: Test Patient
Case Number: TEST-001
Exam Type: Orthopedic
Date: April 15, 2025
Location: Los Angeles, CA

Please confirm receipt.
```

3. Wait 60 seconds (or trigger manual poll)
4. Check the database or API:
```bash
curl http://localhost:8000/cases/
```

## Troubleshooting

### Email Polling Not Starting

**Check logs:**
```
INFO: Email polling is disabled (EMAIL_ENABLED=false)
```

**Solution:** Set `EMAIL_ENABLED=true` in `.env`

### Authentication Failed

**Error:**
```
ERROR: Failed to connect to email server: authentication failed
```

**Solutions:**
1. Verify app password is correct (no spaces)
2. Ensure 2FA is enabled on Gmail
3. Try regenerating the app password

### No Emails Found

**Check:**
1. Do you have unread emails in your inbox?
2. Is the email address correct?
3. Check IMAP server and port

**Test connection manually:**
```python
from app.services.email_fetcher import EmailFetcher

fetcher = EmailFetcher(
    imap_server="imap.gmail.com",
    email_address="your-email@gmail.com",
    password="your-app-password"
)
emails = fetcher.fetch_unread_emails()
print(f"Found {len(emails)} emails")
```


## API Endpoints

### POST /email-polling/manual-poll
Manually trigger email fetching and processing.

**Response:**
```json
{
  "processed": 2,
  "failed": 0,
  "emails": [...]
}
```

### GET /email-polling/status
Get current email configuration status.

**Response:**
```json
{
  "enabled": true,
  "configured": true,
  "imap_server": "imap.gmail.com",
  ...
}
```

## Advanced Configuration

### Change Polling Interval

Default is 60 seconds. To change:

```bash
EMAIL_POLL_INTERVAL=30  # Poll every 30 seconds
```

### Disable Automatic Polling

Use manual polling only:

```bash
EMAIL_ENABLED=false
```

Then trigger manually when needed:
```bash
curl -X POST http://localhost:8000/email-polling/manual-poll
```


**Questions?** Check the main README.md or API docs at http://localhost:8000/docs
