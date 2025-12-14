# Quick Setup Guide

## What's Been Built

✅ **Complete Backend MVP** with:
- FastAPI application with auto-generated docs
- PostgreSQL database integration
- OpenAI GPT-4o LLM extraction service
- Email ingestion pipeline with case matching
- RESTful API endpoints for cases and emails
- Database migrations with Alembic
- Comprehensive test suite
- Docker Compose for local PostgreSQL

✅ **Three Sample Emails**:
1. `email_001.json` - Clean, well-structured referral
2. `email_002.json` - Scheduling update for existing case
3. `email_003.json` - Messy, unstructured intake

## Next Steps

### 1. Set Up Environment

```bash
# Create .env file from template
cp .env.example .env

# Edit .env and add your OpenAI API key
# Required: OPENAI_API_KEY=sk-...
```

### 2. Start Database

```bash
# From project root
docker compose up -d

# Verify running
docker compose ps
```

### 3. Install Dependencies & Run Migrations

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head
```

### 4. Start the API

```bash
# From backend directory
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs to see the interactive API documentation.

### 5. Test with Sample Emails

```bash
# Process all sample emails at once
curl -X POST http://localhost:8000/emails/simulate-batch

# View results
curl http://localhost:8000/cases/

# Or use the interactive docs at http://localhost:8000/docs
```

## Verify Everything Works

### Check Health

```bash
curl http://localhost:8000/health
```

### Run Tests

```bash
cd backend
pytest -v
```

### Expected Test Output

```
tests/test_api.py::test_root_endpoint PASSED
tests/test_api.py::test_health_check PASSED
tests/test_api.py::test_list_cases_empty PASSED
...
```

## API Highlights

### Process Emails
- `POST /emails/simulate-batch` - Process all sample emails
- `POST /emails/ingest` - Process individual email

### Query Cases
- `GET /cases/` - List all cases
- `GET /cases/?min_confidence=0.8` - High-confidence cases only
- `GET /cases/{id}` - Full case details
- `PATCH /cases/{id}` - Update case

### Query Attachments
- `GET /attachments/` - List all attachments
- `GET /attachments/?category=medical_records` - Filter by category
- `GET /attachments/case/{case_id}/attachments` - All attachments for a case
- `GET /attachments/by-category/medical_records` - Get medical records only

### Interactive Docs
Visit http://localhost:8000/docs for full API documentation with try-it-out functionality.

## Sample Email Scenarios

### Email 001 - Clean Referral
- Well-structured with all fields present
- Expected confidence: 0.9+
- Tests: Complete data extraction

### Email 002 - Scheduling Update
- Follow-up email for case NF-39281
- Tests: Case matching, update logic
- Expected confidence: 0.85+

### Email 003 - Messy Intake
- Informal formatting, ambiguous case number
- Multiple case number formats (2024-WC-8891 vs WC8891)
- Tests: Handling uncertainty, extraction robustness
- Expected confidence: 0.6-0.8

## Troubleshooting

### Database won't start
```bash
docker compose down -v
docker compose up -d
```

### API won't start
- Check `.env` file exists
- Verify `DATABASE_URL` is correct
- Ensure port 8000 is free

### Tests failing
- Activate virtual environment
- Ensure all dependencies installed
- Check database is running

## What to Explore

1. **Interactive API Docs** - http://localhost:8000/docs
2. **Process sample emails** - See LLM extraction in action
3. **Query cases by confidence** - See confidence scoring
4. **Filter attachments by category** - Test attachment endpoints
5. **Update a case** - Test PATCH endpoint
6. **Check raw_extraction** - See full LLM response
7. **Explore database indexes** - Check query performance in PostgreSQL
8. **Run tests** - Verify everything works

## Architecture Notes

- **Extraction**: Uses OpenAI function calling for structured output
- **Case Matching**: Matches on case_number to link multiple emails
- **Error Handling**: Never loses data, even on extraction failure
- **Confidence**: 0.8+ auto-process, 0.5-0.8 review, <0.5 manual
- **Database**: PostgreSQL with proper foreign keys and performance indexes
- **Normalization**: 3NF with strategic denormalization (attachments link to both email and case)
- **Storage Ready**: File storage fields prepared for S3/cloud integration

## Next Features (Not Implemented - Future Work)

- [ ] Frontend UI (React + TypeScript)
- [ ] S3/cloud file upload and storage (fields ready)
- [ ] Email webhook integration
- [ ] Background job processing (Celery)
- [ ] User authentication
- [ ] Audit logging
- [ ] Export functionality
- [ ] Full-text search on email content

---

**MVP Status**: ✅ Complete and functional

See README.md for full documentation.
