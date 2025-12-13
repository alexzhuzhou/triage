# Triage - IME Email Processing System

Backend service that processes inbound emails for Independent Medical Examination (IME) companies, extracting structured case data using LLM and persisting to a PostgreSQL database.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Email Ingest   │────▶│   FastAPI       │────▶│   PostgreSQL    │
│  (Simulated)    │     │   Backend       │     │   Database      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  OpenAI API     │
                        │  (Extraction)   │
                        └─────────────────┘
```

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15 + SQLAlchemy + Alembic
- **LLM**: OpenAI GPT-4o for structured data extraction
- **Testing**: Pytest

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key

### 2. Environment Setup

```bash
# Clone or navigate to the project
cd Triage

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-...
```

### 3. Start PostgreSQL

```bash
# Start PostgreSQL container
docker compose up -d

# Verify it's running
docker compose ps
```

### 4. Install Python Dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Run Database Migrations

```bash
# Apply database schema
alembic upgrade head
```

### 6. Start the API Server

```bash
# Run the FastAPI application
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Usage

### Process Sample Emails

The project includes sample email files in `backend/sample_emails/`. Process them all at once:

```bash
curl -X POST http://localhost:8000/emails/simulate-batch
```

Or via the interactive docs at http://localhost:8000/docs

### Ingest Individual Email

```bash
curl -X POST http://localhost:8000/emails/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "New IME Referral",
    "sender": "referrals@lawfirm.com",
    "recipients": ["intake@ime.com"],
    "body": "Case details...",
    "attachments": [],
    "received_at": "2025-03-10T10:00:00Z"
  }'
```

### List Cases

```bash
# All cases
curl http://localhost:8000/cases/

# Filter by confidence threshold
curl http://localhost:8000/cases/?min_confidence=0.8

# Filter by status
curl http://localhost:8000/cases/?status=pending
```

### Get Case Details

```bash
# By ID
curl http://localhost:8000/cases/{case_id}

# By case number
curl http://localhost:8000/cases/by-number/NF-39281
```

### Update Case

```bash
curl -X PATCH http://localhost:8000/cases/{case_id} \
  -H "Content-Type: application/json" \
  -d '{
    "status": "confirmed",
    "notes": "Patient confirmed attendance"
  }'
```

## API Endpoints

### Emails

- `POST /emails/ingest` - Submit an email for processing
- `POST /emails/simulate-batch` - Process all sample emails
- `GET /emails/{id}` - Get email details with extraction
- `GET /emails/` - List all emails (with filters)

### Cases

- `GET /cases/` - List cases (filterable by status, exam_type, confidence)
- `GET /cases/{id}` - Full case details with emails and attachments
- `GET /cases/by-number/{case_number}` - Get case by case number
- `PATCH /cases/{id}` - Update case fields

## Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings configuration
│   ├── database.py          # Database setup
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── case.py
│   │   ├── email.py
│   │   └── attachment.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── case.py
│   │   ├── email.py
│   │   └── extraction.py    # LLM extraction schema
│   ├── services/            # Business logic
│   │   ├── extraction.py    # OpenAI integration
│   │   └── ingestion.py     # Email processing pipeline
│   └── routers/             # API endpoints
│       ├── cases.py
│       └── emails.py
├── sample_emails/           # Sample email JSON files
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── requirements.txt
└── pytest.ini
```

## Data Models

### Case
Primary entity representing an IME case:
- `case_number`: Unique identifier (e.g., "NF-39281")
- `patient_name`: Claimant's full name
- `exam_type`: Type of examination (Orthopedic, Neurology, etc.)
- `exam_date`, `exam_time`: Scheduled examination
- `exam_location`: City/state or address
- `referring_party`: Law firm or organization
- `status`: pending | confirmed | completed
- `extraction_confidence`: 0.0-1.0 LLM confidence score

### Email
Source records that link to cases:
- Stores raw email data (subject, sender, body, recipients)
- `raw_extraction`: JSON blob of LLM response
- `processing_status`: pending | processing | processed | failed

### Attachment
Email attachments with categorization:
- Links to both email and case
- `category`: medical_records | declaration | cover_letter | other
- `content_preview`: First 500 characters

## LLM Extraction

The system uses OpenAI's GPT-4o with structured output (function calling) to extract:

**Required Fields:**
- patient_name, case_number, exam_type, attachments

**Optional Fields:**
- exam_date, exam_time, exam_location, referring_party, report_due_date

**Metadata:**
- confidence (0-1): Quality assessment
- extraction_notes: Ambiguities or uncertainties
- email_intent: new_referral | scheduling_update | document_submission | inquiry | other

### Confidence Thresholds

- `≥ 0.8`: High confidence - auto-process
- `0.5 - 0.8`: Medium confidence - flag for review
- `< 0.5`: Low confidence - requires manual review

## Database Management

### Create New Migration

```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

### Reset Database

```bash
# Stop containers
docker compose down -v

# Restart
docker compose up -d

# Reapply migrations
alembic upgrade head
```

## Development

### Code Quality

```bash
# Format code (if using black)
black app/

# Lint (if using ruff)
ruff check app/
```

### View API Logs

```bash
# API logs show SQL queries in development mode
# Check terminal where uvicorn is running
```

### Access Database

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d triage

# Example queries
\dt                    # List tables
SELECT * FROM cases;   # View cases
SELECT * FROM emails;  # View emails
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker compose ps

# View logs
docker compose logs postgres

# Restart database
docker compose restart postgres
```

### OpenAI API Errors

- Verify `OPENAI_API_KEY` is set correctly in `.env`
- Check API key has sufficient credits
- Review error messages in email `error_message` field

### Migration Issues

```bash
# Check current version
alembic current

# View migration history
alembic history
```

## Contributing

This is a take-home assignment demonstrating:
- ✅ Data modeling for messy real-world inputs
- ✅ Responsible, predictable LLM usage with structured output
- ✅ Pragmatic full-stack implementation
- ✅ Error handling and data preservation
- ✅ API design and documentation
- ✅ Testing practices

## License

Proprietary - Brighterway Take-Home Assignment
