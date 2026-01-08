"""
LLM extraction service using OpenAI API.

This service extracts structured case data from email content using OpenAI's
function calling / structured output capabilities.
"""
import json
import logging
import random
from typing import Dict, Any
from openai import OpenAI
from app.config import settings
from app.schemas.extraction import CaseExtraction

logger = logging.getLogger(__name__)


# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# System prompt for extraction
EXTRACTION_SYSTEM_PROMPT = """You are an expert medical intake coordinator specializing in Independent Medical Examination (IME) case processing.

Your task is to extract structured information from emails about IME referrals. These emails may include:
- Email body text with case details
- **PDF documents converted to images** (medical records, declarations, cover letters, etc.)
- Text file attachments
- Images and scans of documents

**CRITICAL: You will receive PDF attachments as a series of page images. Carefully read ALL pages to extract complete information.**

**Vision Processing Guidelines:**

1. **Read All Pages Thoroughly**: Medical records often span multiple pages. Extract information from ALL provided images.

2. **Handwritten & Scanned Documents**: Many medical documents are handwritten or poorly scanned with text at angles. Use your vision capabilities to interpret unclear, rotated, or handwritten text.

3. **Extract Key Data from Images**: Look for patient names, dates, case numbers, exam details, referring party information across all document pages.

4. **Visual Attachment Categorization**: Categorize based on visual content, not just filename:
   - medical_records: Doctor notes, lab results, imaging reports, treatment histories, prescription records
   - declaration: Legal declarations, sworn statements, affidavits
   - cover_letter: Referral letters, intake forms, cover sheets
   - other: Everything else (provide category_reason)

5. **Cross-Reference Information**: If information appears in both email body and PDF images, prefer the email version (more authoritative and detailed).

**General Guidelines:**

1. **Handle Ambiguity Gracefully**: If information is unclear, extract your best interpretation and note the uncertainty in extraction_notes.

2. **Preserve Formatting**: Keep case numbers in their original format (e.g., "NF-39281", "2024-IME-1234").

3. **Confidence Scoring with Images**: Assign a confidence score (0.0 to 1.0) based on:
   - 0.9-1.0: All required fields clearly visible in images/text, high-quality documents
   - 0.7-0.9: Most fields extracted, minor OCR uncertainties or handwriting difficult to read
   - 0.5-0.7: Some fields missing, poor image quality, or significant portions illegible
   - 0.0-0.5: Very poor quality, mostly illegible, or missing critical information

4. **Email Intent Classification**:
   - new_referral: First submission of a case
   - scheduling_update: Confirmation, rescheduling, or time changes
   - document_submission: Additional documents for existing case
   - inquiry: Questions about a case
   - other: Doesn't fit above categories

5. **Date/Time Extraction**: Use ISO format (YYYY-MM-DD) for dates and HH:MM for times.

Extract all available information from both text and images, and provide a confidence assessment."""


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

    # TESTING: Simulate LLM failures to test retry logic
    if settings.SIMULATE_LLM_FAILURES:
        if random.random() < settings.LLM_FAILURE_RATE:
            raise Exception(f"SIMULATED LLM FAILURE: Connection timeout (testing retry mechanism - {int(settings.LLM_FAILURE_RATE * 100)}% failure rate)")

    # Build multimodal user content (text + images)
    user_content = []

    # Add email text content
    email_text = f"""Email Details:

Subject: {subject}
From: {sender}

Body:
{body}

Attachments:"""

    # Add attachment metadata
    for idx, att in enumerate(attachments, 1):
        filename = att.get('filename', 'unknown')
        content_type = att.get('content_type', 'unknown')
        text_preview = att.get('text_content', '')[:200] if att.get('text_content') else ''

        email_text += f"\n{idx}. {filename} ({content_type})"
        if text_preview:
            email_text += f" - Text preview: {text_preview}..."

    email_text += "\n\nExtract the case information from this email and attachments."
    user_content.append({"type": "text", "text": email_text})

    # Add PDF images to content
    for att in attachments:
        pdf_images = att.get('pdf_images', [])
        if pdf_images:
            filename = att.get('filename', 'unknown')
            for page_num, image_b64 in enumerate(pdf_images, 1):
                # Add image
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                        "detail": settings.VISION_IMAGE_DETAIL
                    }
                })
                # Add caption for context
                user_content.append({
                    "type": "text",
                    "text": f"[Page {page_num} of {filename}]"
                })

    # Use modern Messages API with vision support
    response = client.chat.completions.create(
        model="gpt-4o",  # GPT-4o supports vision
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "case_extraction",
                "strict": True,
                "schema": CaseExtraction.model_json_schema()
            }
        },
        temperature=0.1,  # Low temperature for consistency
    )

    # Parse structured JSON response
    extraction_dict = json.loads(response.choices[0].message.content)

    # Log token usage
    usage = response.usage
    logger.info(f"Token usage: {usage.prompt_tokens} prompt, "
               f"{usage.completion_tokens} completion, "
               f"{usage.total_tokens} total")

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
