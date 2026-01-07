"""
LLM extraction service using OpenAI API.

This service extracts structured case data from email content using OpenAI's
function calling / structured output capabilities.
"""
import json
from typing import Dict, Any
from openai import OpenAI
from app.config import settings
from app.schemas.extraction import CaseExtraction


# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# System prompt for extraction
EXTRACTION_SYSTEM_PROMPT = """You are an expert medical intake coordinator specializing in Independent Medical Examination (IME) case processing.

Your task is to extract structured information from emails about IME referrals. These emails may be:
- New case referrals with patient and exam details
- Scheduling updates or confirmations
- Document submissions for existing cases
- General inquiries

**Important Guidelines:**

1. **Handle Ambiguity Gracefully**: If information is unclear, extract your best interpretation and note the uncertainty in extraction_notes.

2. **Preserve Formatting**: Keep case numbers in their original format (e.g., "NF-39281", "2024-IME-1234").

3. **Confidence Scoring**: Assign a confidence score (0.0 to 1.0) based on:
   - 0.9-1.0: All required fields clearly present, well-structured email
   - 0.7-0.9: Most fields present, minor ambiguities
   - 0.5-0.7: Some fields missing or ambiguous
   - 0.0-0.5: Poorly structured, many missing fields or uncertainties

4. **Attachment Categorization**:
   - medical_records: Patient treatment history, doctor notes, imaging reports
   - declaration: Legal declarations, sworn statements
   - cover_letter: Referral letters, cover sheets
   - other: Anything else (provide category_reason)

5. **Email Intent Classification**:
   - new_referral: First submission of a case
   - scheduling_update: Confirmation, rescheduling, or time changes
   - document_submission: Additional documents for existing case
   - inquiry: Questions about a case
   - other: Doesn't fit above categories

6. **Date/Time Extraction**: Use ISO format (YYYY-MM-DD) for dates and HH:MM for times.

Extract all available information and provide a confidence assessment."""


def extract_case_from_email(
    subject: str,
    sender: str,
    body: str,
    attachments: list[Dict[str, Any]]
) -> CaseExtraction:
    """
    Extract structured case data from an email using OpenAI.

    This function calls the OpenAI API and lets any errors propagate up to the
    caller. This allows the queue retry mechanism to handle transient failures
    (timeouts, rate limits) with exponential backoff.

    Args:
        subject: Email subject line
        sender: Sender email address
        body: Email body text
        attachments: List of attachment metadata (filename, content_type, text_content)

    Returns:
        CaseExtraction: Structured extraction result

    Raises:
        Exception: If OpenAI API call fails (triggers retry in queue)
    """

    # Build user prompt with email content
    attachment_info = "\n".join([
        f"- {att.get('filename', 'unknown')} ({att.get('content_type', 'unknown')}): {att.get('text_content', '')[:200]}..."
        for att in attachments
    ]) if attachments else "No attachments"

    user_prompt = f"""Email Details:

Subject: {subject}
From: {sender}

Body:
{body}

Attachments:
{attachment_info}

Extract the case information from this email."""

    # Use OpenAI's function calling for structured output
    response = client.chat.completions.create(
        model="gpt-4o",  # Using GPT-4o for better structured outputs
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        functions=[{
            "name": "extract_case_data",
            "description": "Extract structured IME case data from email",
            "parameters": CaseExtraction.model_json_schema()
        }],
        function_call={"name": "extract_case_data"},
        temperature=0.1,  # Low temperature for consistency
    )

    # Parse the function call arguments
    function_args = response.choices[0].message.function_call.arguments
    extraction_dict = json.loads(function_args)

    # Validate and return as Pydantic model
    return CaseExtraction(**extraction_dict)


def validate_extraction_confidence(extraction: CaseExtraction) -> str:
    """
    Determine processing recommendation based on confidence threshold.

    Args:
        extraction: The case extraction result

    Returns:
        str: Recommendation ("auto_process", "needs_review", "requires_manual")
    """
    if extraction.confidence >= 0.8:
        return "auto_process"
    elif extraction.confidence >= 0.5:
        return "needs_review"
    else:
        return "requires_manual"
