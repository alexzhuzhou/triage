"""
PDF to image conversion service using pdf2image.

Converts PDF attachments to PNG images for vision-based LLM extraction.
Uses parallel processing for efficient handling of multi-page PDFs.
"""
import base64
import io
import logging
from typing import List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image
from app.config import settings

logger = logging.getLogger(__name__)


class PDFConversionError(Exception):
    """Exception raised when PDF conversion fails."""
    pass


def convert_pdf_chunk(
    pdf_content: bytes,
    first_page: int,
    last_page: int,
    dpi: int,
    image_format: str,
    compression_quality: int
) -> List[str]:
    """
    Convert a chunk of PDF pages to base64-encoded images.

    Args:
        pdf_content: Raw PDF bytes
        first_page: Starting page number (1-indexed)
        last_page: Ending page number (1-indexed)
        dpi: Resolution for rendering
        image_format: Output format ('png' or 'jpeg')
        compression_quality: JPEG quality 0-100

    Returns:
        List of base64-encoded image strings for this chunk
    """
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise PDFConversionError(
            "pdf2image is not installed. Install with: pip install pdf2image\n"
            "Also requires poppler-utils: https://github.com/Belval/pdf2image#windows"
        )

    chunk_images = []

    try:
        logger.debug(f"Converting pages {first_page}-{last_page} at {dpi} DPI")

        # Convert chunk using pdf2image with pdftocairo backend for better quality
        pil_images = convert_from_bytes(
            pdf_content,
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
            fmt=image_format,
            use_pdftocairo=True  # Better rendering quality
        )

        # Convert PIL Images to base64
        for page_num, img in enumerate(pil_images, start=first_page):
            try:
                buffer = io.BytesIO()

                if image_format.lower() == 'jpeg':
                    img.save(buffer, format='JPEG', quality=compression_quality, optimize=True)
                else:
                    img.save(buffer, format='PNG', optimize=True)

                buffer.seek(0)
                img_b64 = base64.b64encode(buffer.read()).decode('utf-8')
                chunk_images.append(img_b64)

                logger.debug(f"Encoded page {page_num} to base64")

            except Exception as e:
                logger.warning(f"Failed to encode page {page_num}: {str(e)}")
                continue

        logger.info(f"Successfully converted chunk {first_page}-{last_page}: {len(chunk_images)} images")

    except Exception as e:
        logger.error(f"Failed to convert chunk {first_page}-{last_page}: {str(e)}")
        raise

    return chunk_images


def convert_pdf_to_images(
    pdf_content: bytes,
    max_pages: Optional[int] = None,
    dpi: Optional[int] = None,
    image_format: Optional[str] = None,
    compression_quality: Optional[int] = None,
    chunk_size: int = 100,
    max_workers: Optional[int] = None
) -> List[str]:
    """
    Convert PDF to list of base64-encoded images using pdf2image with parallel processing.

    Args:
        pdf_content: Raw PDF bytes from email attachment
        max_pages: Maximum pages to convert (None = all pages)
        dpi: Resolution for rendering (150 recommended for balance, 300 for high quality)
        image_format: Output format ('png' or 'jpeg')
        compression_quality: JPEG quality 0-100 (only used if format='jpeg')
        chunk_size: Number of pages to process per chunk (default 100)
        max_workers: Max parallel workers (None = CPU count)

    Returns:
        List of base64-encoded image strings in page order

    Raises:
        PDFConversionError: If PDF is invalid or conversion fails

    Example:
        >>> pdf_bytes = open('document.pdf', 'rb').read()
        >>> images = convert_pdf_to_images(pdf_bytes, max_pages=5, dpi=150)
        >>> len(images)
        5
    """
    try:
        from pdf2image import pdfinfo_from_bytes
    except ImportError:
        raise PDFConversionError(
            "pdf2image is not installed. Install with: pip install pdf2image\n"
            "Also requires poppler-utils: https://github.com/Belval/pdf2image#windows"
        )

    # Use settings defaults if not provided
    dpi = dpi or settings.PDF_CONVERSION_DPI
    max_pages = max_pages if max_pages is not None else settings.PDF_MAX_PAGES
    image_format = image_format or settings.PDF_IMAGE_FORMAT
    compression_quality = compression_quality or settings.PDF_COMPRESSION_QUALITY

    if not pdf_content:
        logger.warning("Empty PDF content provided")
        return []

    try:
        # Get PDF metadata to determine page count
        info = pdfinfo_from_bytes(pdf_content)
        total_pages = info.get("Pages", 0)

        if total_pages == 0:
            logger.info("PDF has 0 pages, returning empty list")
            return []

        pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
        logger.info(f"Converting PDF: {pages_to_process}/{total_pages} pages at {dpi} DPI")

    except Exception as e:
        logger.error(f"Failed to read PDF metadata: {str(e)}")
        # Fallback: Try converting without knowing page count
        logger.info("Attempting conversion without metadata...")
        try:
            from pdf2image import convert_from_bytes
            pil_images = convert_from_bytes(
                pdf_content,
                dpi=dpi,
                use_pdftocairo=True
            )

            images = []
            for idx, img in enumerate(pil_images, 1):
                if max_pages and idx > max_pages:
                    break

                buffer = io.BytesIO()
                if image_format.lower() == 'jpeg':
                    img.save(buffer, format='JPEG', quality=compression_quality, optimize=True)
                else:
                    img.save(buffer, format='PNG', optimize=True)
                buffer.seek(0)
                img_b64 = base64.b64encode(buffer.read()).decode('utf-8')
                images.append(img_b64)

            logger.info(f"Fallback conversion successful: {len(images)} images")
            return images

        except Exception as fallback_error:
            raise PDFConversionError(f"Failed to convert PDF: {str(fallback_error)}")

    # Split pages into chunks for parallel processing
    chunks = []
    for i in range(1, pages_to_process + 1, chunk_size):
        first_page = i
        last_page = min(i + chunk_size - 1, pages_to_process)
        chunks.append((first_page, last_page))

    logger.info(f"Processing {len(chunks)} chunks with chunk_size={chunk_size}")

    # Process chunks in parallel
    all_images = {}  # Dict to preserve page order: {page_num: base64_image}

    if len(chunks) == 1:
        # Single chunk - no need for parallel processing
        chunk_images = convert_pdf_chunk(
            pdf_content,
            chunks[0][0],
            chunks[0][1],
            dpi,
            image_format,
            compression_quality
        )
        for idx, img in enumerate(chunk_images, start=chunks[0][0]):
            all_images[idx] = img
    else:
        # Multiple chunks - use parallel processing
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(
                    convert_pdf_chunk,
                    pdf_content,
                    first_page,
                    last_page,
                    dpi,
                    image_format,
                    compression_quality
                ): (first_page, last_page)
                for first_page, last_page in chunks
            }

            for future in as_completed(future_to_chunk):
                first_page, last_page = future_to_chunk[future]
                try:
                    chunk_images = future.result()
                    # Store images with their page numbers
                    for idx, img in enumerate(chunk_images, start=first_page):
                        all_images[idx] = img

                except Exception as e:
                    logger.error(f"Chunk {first_page}-{last_page} failed: {str(e)}")
                    # Continue with other chunks instead of failing completely
                    continue

    # Convert dict to ordered list
    images = [all_images[page_num] for page_num in sorted(all_images.keys())]

    logger.info(f"Successfully converted {len(images)}/{pages_to_process} pages")

    if len(images) == 0:
        raise PDFConversionError("Failed to convert any pages from PDF")

    return images


def estimate_token_cost(num_pages: int, dpi: int = 150, detail: str = "high") -> int:
    """
    Estimate token cost for PDF images sent to vision API.

    Based on OpenAI's vision pricing:
    - High detail: ~765-2000 tokens per image depending on size
    - Low detail: ~85 tokens per image

    Args:
        num_pages: Number of PDF pages
        dpi: Image resolution (affects size)
        detail: Vision API detail level ('low', 'high', 'auto')

    Returns:
        Estimated total tokens for all images
    """
    if detail == "low":
        tokens_per_image = 85
    elif detail == "high":
        # At 150 DPI, typical letter-size page = ~1200x1600 pixels
        # OpenAI charges based on tiles (512x512)
        # 1200x1600 = ~6 tiles = ~1275 tokens
        tokens_per_image = 1275 if dpi <= 150 else 2000
    else:  # auto
        tokens_per_image = 1000  # Average estimate

    return num_pages * tokens_per_image
