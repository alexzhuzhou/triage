# Quick Setup Guide

## What's Been Built

**Complete Full-Stack Application** with:

**Backend:**
- FastAPI application with auto-generated docs
- PostgreSQL database integration
- OpenAI GPT-4o LLM extraction service
- **Real Email Integration** (IMAP - Gmail/Outlook):
  - Automatic background polling (every 60s)
  - Manual on-demand email fetching
  - Email parsing and format conversion
- Intelligent email ingestion pipeline with:
  - Confidence-based case updates
  - Conflict detection and manual review flagging
  - Missing critical fields validation
- RESTful API endpoints for cases, emails, and attachments
- Database migrations with Alembic
- Performance-optimized queries with eager loading
- Comprehensive test suite
- Docker Compose for local PostgreSQL

**Frontend:**
- React 18 + TypeScript + Vite
- TailwindCSS for styling
- React Query for data fetching
- Dashboard with search and filters
- Case detail page with email and attachment previews
- Email processing interface
- Color-coded badges and responsive design

 **Ten Sample Emails** (diverse scenarios for testing):
1. `email_001.json` - Clean referral (Johnathan Doe, NF-39281, Orthopedic)
2. `email_002.json` - Scheduling confirmation (Jane Smith, 2024-7781)
3. `email_003.json` - Messy intake (Robert L. Hernandez, RH-99102, Neurology)
4. `email_004.json` - Psychiatric case (Sarah Martinez, WC-2025-4432)
5. `email_005.json` - Additional docs for existing case (NF-39281)
6. `email_006.json` - Super messy outlier (Michael Thompson, missing info)
7. `email_007.json` - Urgent with missing info (David Kim, tests validation)
8. `email_008.json` - Schedule change/conflict (Jane Smith, tests conflict detection)
9. `email_009.json` - Clean cardiology case (Angela Chen, CA-2025-1189)
10. `email_010.json` - Extreme outlier forwarded mess (Patricia Rodriguez)

## Next Steps

### 1. Set Up Environment

```bash
# Create .env file from template
cp .env.example .env

# Edit .env and add your API key
# Required: OPENAI_API_KEY=sk-...

# Optional: Configure email integration
# EMAIL_ENABLED=true
# EMAIL_ADDRESS=your-email@gmail.com
# EMAIL_PASSWORD=your-app-password
```

**For email integration setup, see [EMAIL_INTEGRATION.md](EMAIL_INTEGRATION.md)**

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

### 5. Start the Frontend (Optional)

```bash
# From project root
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at http://localhost:5173

### 6. Test with Sample Emails

**Option 1: Using the Frontend** (Recommended)
1. Visit http://localhost:5173/process
2. Click "Process Sample Emails"
3. View results and navigate to dashboard

**Option 2: Using cURL**
```bash
# Process all sample emails at once
curl -X POST http://localhost:8000/emails/simulate-batch

# View results
curl http://localhost:8000/cases/
```

**Option 3: Using Interactive API Docs**
- Visit http://localhost:8000/docs
- Navigate to POST /emails/simulate-batch
- Click "Try it out" → "Execute"

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

### Email Polling
- `POST /email-polling/manual-poll` - Manually trigger email fetching from Gmail/Outlook
- `GET /email-polling/status` - Check email integration configuration

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

### Email 002 - Scheduling Confirmation
- Jane Smith case (2024-7781)
- Scheduling confirmation with cover letter
- Tests: New case creation
- Expected confidence: 0.85+

### Email 003 - Messy Intake
- Informal formatting ("Hi", "asap", "might be")
- Ambiguous case number (RH-99102 "or something close to that")
- Missing critical info (will trigger follow-up flag)
- Tests: Handling uncertainty, missing fields validation
- Expected confidence: 0.6-0.8

### Email 004 - Psychiatric Case
- Sarah Martinez, WC-2025-4432
- Tests: Different exam type (Psychiatric)

### Email 005 - Follow-up for Existing Case
- Additional documents for NF-39281
- Tests: Case matching and document_submission intent

### Email 006 - Super Messy Outlier
- Michael Thompson, poor formatting
- Missing critical information
- Tests: Extreme low-confidence handling

### Email 007 - Urgent with Missing Info
- David Kim, urgent request
- Missing exam date and location
- Tests: Missing field validation

### Email 008 - Schedule Change/Conflict
- Jane Smith case update with new date
- Tests: Conflict detection system

### Email 009 - Clean Cardiology Case
- Angela Chen, CA-2025-1189
- Professional formatting
- Tests: High-confidence extraction

### Email 010 - Extreme Outlier
- Patricia Rodriguez, forwarded mess
- Multiple formatting issues
- Tests: Worst-case scenario handling

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

## Key Features Implemented

### Intelligent Case Updates
- **High Confidence Auto-Update**: New extractions with higher confidence automatically update all fields
- **Low Confidence Conflict Detection**: Flags conflicting data for manual review with detailed notes
- Example: `"⚠️ MANUAL REVIEW NEEDED (Low confidence: 0.75)\nConflicts detected:\n  - Exam Date: 2025-03-18 -> 2025-03-22"`

### Missing Critical Fields Validation
- Automatically flags cases missing: exam_date, exam_location, report_due_date, exam_time
- Adds follow-up notes: `"🔔 FOLLOW-UP REQUIRED\nMissing critical information:\n  - Exam Date\n  - Report Due Date"`

### Frontend Features
- **Dashboard**: Search, filter by status/confidence, stats overview
- **Case Detail**: Edit status/notes, view related emails and attachments
- **Email Preview Modal**: Click emails to view full content and processing info
- **Attachment Preview Modal**: Click attachments to view content preview
- **Timezone-Safe Dates**: Correctly displays dates without timezone conversion issues

### Data Flexibility
- **Optional Timestamps**: `received_at` field auto-generates if not provided
- **Eager Loading**: Efficient queries with `joinedload()` to fetch emails and attachments
- **Full Response**: Case endpoints return complete data including emails and attachments

## Architecture Notes

- **Extraction**: OpenAI function calling for reliable structured output
- **Case Matching**: Matches on case_number to link multiple emails
- **Error Handling**: Never loses data, even on extraction failure
- **Confidence**: 0.8+ auto-process, 0.5-0.8 review, <0.5 manual
- **Database**: PostgreSQL with foreign keys and performance indexes (10+ indexes)
- **Normalization**: 3NF with strategic denormalization
- **Storage Ready**: S3/cloud file storage fields prepared
- **Frontend**: React Query for caching, TailwindCSS for styling

## Implemented Features

-  **Email Integration** - IMAP polling (Gmail, Outlook) with background tasks
-  **Manual Email Polling** - On-demand email fetching via API
-  **10 Sample Emails** - Comprehensive test coverage
-  **Intelligent Case Updates** - Confidence-based update strategy
-  **Conflict Detection** - Flags low-confidence conflicting data
-  **Missing Field Validation** - Automatic follow-up flagging

## Future Enhancements (Not Implemented)

- [ ] S3/cloud file upload and storage (fields ready)
- [ ] Email webhook integration for real-time processing
- [ ] Background job processing (Celery/RQ) for heavy workloads
- [ ] User authentication and authorization
- [ ] Audit logging and change history
- [ ] Export functionality (PDF, CSV)
- [ ] Full-text search on email content
- [ ] Email deduplication
- [ ] Calendar integration for exam scheduling

---


See README.md for detailed documentation.
