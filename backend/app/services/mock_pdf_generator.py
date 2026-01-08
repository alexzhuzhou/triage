"""
Mock PDF image generator for testing.

Generates realistic-looking document images from text content in sample emails.
This allows testing PDF-to-image extraction without storing large binary files.
"""
import base64
import io
import logging
from typing import List
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def generate_mock_pdf_images(
    text_content: str,
    filename: str,
    chars_per_page: int = 2000
) -> List[str]:
    """
    Generate mock PDF page images from text content for testing.

    Creates simple PNG images with text rendered on a white background,
    simulating what a scanned or PDF document might look like.

    Args:
        text_content: Text to render on images
        filename: Filename for context (shown in header)
        chars_per_page: Characters to fit per page (default 2000)

    Returns:
        List of base64-encoded PNG images

    Example:
        >>> text = "Patient: John Doe\\nCase: NF-12345\\nExam: Orthopedic"
        >>> images = generate_mock_pdf_images(text, "medical_records.pdf")
        >>> len(images)
        1
    """
    if not text_content:
        logger.warning(f"Empty text content for {filename}")
        return []

    # Split text into pages
    pages = []
    for i in range(0, len(text_content), chars_per_page):
        page_text = text_content[i:i + chars_per_page]
        pages.append(page_text)

    logger.info(f"Generating {len(pages)} mock page(s) for {filename}")

    images = []
    for page_num, page_text in enumerate(pages, 1):
        try:
            # Create letter-size image (816x1056 at 96 DPI)
            img = Image.new('RGB', (816, 1056), color='white')
            draw = ImageDraw.Draw(img)

            # Try to load a system font, fall back to default if not available
            try:
                # Common system fonts
                font = ImageFont.truetype("arial.ttf", 12)
                header_font = ImageFont.truetype("arial.ttf", 14)
            except:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", 12)
                    header_font = ImageFont.truetype("DejaVuSans.ttf", 14)
                except:
                    # Fall back to default PIL font
                    font = ImageFont.load_default()
                    header_font = ImageFont.load_default()

            # Add header
            header_text = f"{filename} - Page {page_num}/{len(pages)}"
            draw.text((50, 30), header_text, fill='black', font=header_font)

            # Draw horizontal line under header
            draw.line([(50, 55), (766, 55)], fill='gray', width=1)

            # Render text with word wrapping
            y_position = 80
            max_width = 716  # Image width (816) - margins (50 * 2)
            line_height = 18

            words = page_text.split()
            line = ""

            for word in words:
                # Test if adding this word exceeds max width
                test_line = f"{line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]

                if text_width < max_width:
                    line = test_line
                else:
                    # Draw current line and start new one
                    if line:
                        draw.text((50, y_position), line, fill='black', font=font)
                        y_position += line_height
                        line = word

                    # Check if we've reached bottom of page
                    if y_position > 1000:
                        break

            # Draw remaining text
            if line and y_position < 1000:
                draw.text((50, y_position), line, fill='black', font=font)

            # Add page footer
            footer_text = f"Page {page_num}"
            draw.text((380, 1020), footer_text, fill='gray', font=font)

            # Convert to base64 PNG
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            buffer.seek(0)
            img_b64 = base64.b64encode(buffer.read()).decode('utf-8')
            images.append(img_b64)

            logger.debug(f"Generated mock image for page {page_num}")

        except Exception as e:
            logger.error(f"Failed to generate mock image for page {page_num}: {e}")
            # Continue with remaining pages instead of failing completely
            continue

    logger.info(f"Successfully generated {len(images)} mock image(s) for {filename}")

    return images
