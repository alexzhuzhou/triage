# PDF to Image Conversion Setup

This project uses **pdf2image** with **poppler-utils** for high-quality PDF to image conversion. This enables vision-based extraction of scanned documents, handwritten forms, and PDFs with misaligned text.

## System Requirements

### 1. Install Poppler-Utils (Required)

pdf2image requires poppler-utils to be installed on your system.

#### Windows

**Option A: Using Chocolatey (Recommended)**
```bash
choco install poppler
```

**Option B: Manual Installation**
1. Download poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to `C:\Program Files\poppler`
3. Add `C:\Program Files\poppler\Library\bin` to your PATH environment variable

**Verify Installation:**
```bash
pdftocairo -v
```

#### macOS

Using Homebrew:
```bash
brew install poppler
```

**Verify Installation:**
```bash
pdftocairo -v
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

**Linux (Fedora/RHEL)**

```bash
sudo yum install poppler-utils
```

**Verify Installation:**
```bash
pdftocairo -v
```

### 2. Install Python Dependencies

From the `backend/` directory:

```bash
pip install -r requirements.txt
```

This will install:
- `pdf2image==1.17.0` - PDF to image conversion library
- `Pillow==10.2.0` - Image manipulation library

## How It Works

### Real Email Processing

When an email with PDF attachments is polled:

1. **Email Parser** (`app/services/email_parser.py`) detects PDFs
2. **PDF Converter** (`app/services/pdf_converter.py`) converts each PDF to PNG images:
   - Uses `pdf2image.convert_from_bytes()` for in-memory processing
   - Parallel processing with `ProcessPoolExecutor` for multi-page PDFs
   - Chunks PDFs into 100-page segments for efficiency
   - Uses `pdftocairo` backend for high-quality rendering
   - Default 150 DPI (configurable)
3. **Base64 Encoding**: Images are encoded to base64 strings
4. **LLM Extraction** (`app/services/extraction.py`): Images sent to GPT-4o Vision API
5. **Vision Processing**: LLM reads text from images (handles scanned/rotated/handwritten content)

### Sample Email Testing

Sample emails in `backend/sample_emails/*.json` include `text_content` fields (pre-extracted text). During batch processing:

1. **Mock Image Generator** (`app/services/mock_pdf_generator.py`) creates PNG images from text
2. Uses Pillow to render text on white background (simulates scanned documents)
3. Generated images are sent to Vision API for testing

This allows testing the full vision pipeline without storing large binary PDF files in the repository.

## Configuration

Edit `backend/.env` to customize PDF processing:

```bash
# PDF Processing (all optional, defaults shown)
PDF_CONVERSION_ENABLED=true       # Enable/disable PDF conversion
PDF_CONVERSION_DPI=150            # Image resolution (150=balanced, 300=high quality)
PDF_MAX_PAGES=None                # Max pages to process (None=unlimited)
PDF_IMAGE_FORMAT=png              # Output format ('png' or 'jpeg')
PDF_COMPRESSION_QUALITY=85        # JPEG quality 0-100 (only for jpeg format)
VISION_IMAGE_DETAIL=high          # OpenAI vision detail ('low', 'high', 'auto')
```

## Performance Considerations

### Token Costs

Vision API charges based on image size and detail level:
- **High detail**: ~1,275 tokens per page @ 150 DPI (~2,000 @ 300 DPI)
- **Low detail**: ~85 tokens per page
- **Auto**: OpenAI decides based on image size

**Example**: 10-page PDF @ 150 DPI with high detail ≈ 12,750 tokens

### Processing Speed

- **Single page PDF**: ~1-2 seconds (no parallelization)
- **Multi-page PDF (100+ pages)**: Parallel processing with chunk size of 100 pages
- **Chunk processing**: Multiple chunks processed concurrently using `ProcessPoolExecutor`

### Memory Usage

- PDFs are processed in-memory (no temp files)
- Parallel workers increase memory usage (each worker loads PDF bytes)
- Monitor memory for very large PDFs (500+ pages)

## Troubleshooting

### "poppler not installed" Error

**Error Message:**
```
PDFConversionError: pdf2image is not installed. Install with: pip install pdf2image
Also requires poppler-utils: https://github.com/Belval/pdf2image#windows
```

**Solution:**
1. Verify poppler is installed: `pdftocairo -v`
2. On Windows, ensure `poppler/Library/bin` is in PATH
3. Restart terminal/IDE after installing poppler

### "Unable to get page count" Error

**Error Message:**
```
Failed to read PDF metadata: ...
```

**Solution:**
The converter will automatically fall back to converting without metadata. If this fails:
1. Check if PDF is corrupted: Open it manually
2. Try a different PDF
3. Check poppler installation

### Slow Performance on Large PDFs

**Issue**: PDFs with 200+ pages take a long time to process

**Solutions:**
1. Reduce DPI: `PDF_CONVERSION_DPI=100` (faster, lower quality)
2. Limit pages: `PDF_MAX_PAGES=50` (process first 50 pages only)
3. Use JPEG format: `PDF_IMAGE_FORMAT=jpeg` (smaller images, faster upload)
4. Lower vision detail: `VISION_IMAGE_DETAIL=low` (85 tokens/page vs 1275)

### Windows-Specific Issues

**ProcessPoolExecutor Errors on Windows:**

If you see spawn/pickle errors, this is likely due to Windows' multiprocessing behavior. The current implementation handles this by:
1. Single-chunk PDFs skip parallel processing
2. Chunk processing uses separate worker processes

If issues persist, you can force single-threaded processing by setting `max_workers=1` in the converter.

## Testing

### Test PDF Conversion

```python
# Python script to test conversion
from app.services.pdf_converter import convert_pdf_to_images

# Load a test PDF
with open('test.pdf', 'rb') as f:
    pdf_bytes = f.read()

# Convert to images
images = convert_pdf_to_images(pdf_bytes, dpi=150, max_pages=5)

print(f"Converted {len(images)} pages")
print(f"First image size: {len(images[0])} characters (base64)")
```

### Test with Sample Emails

```bash
# Process all sample emails (includes mock PDF image generation)
curl -X POST http://localhost:8000/emails/simulate-batch

# Check logs for PDF conversion messages
# Look for: "Generated N mock images for filename.pdf"
```

### Test with Real Email

Requires email integration setup (see `EMAIL_INTEGRATION.md`):

```bash
# Manually poll for emails
curl -X POST http://localhost:8000/email-polling/manual-poll

# Check logs for PDF conversion messages
# Look for: "Converted PDF filename.pdf to N images"
```

## Switching Back to PyMuPDF

If you need to switch back to PyMuPDF (zero system dependencies):

1. Edit `backend/app/services/pdf_converter.py`
2. Replace imports and implementation with PyMuPDF version (uses `fitz` library)
3. Update `requirements.txt`: Replace `pdf2image` with `PyMuPDF==1.26.1`
4. No poppler installation needed

**Trade-offs:**
- ✅ No system dependencies (pure Python)
- ✅ Simpler installation
- ❌ No parallel processing
- ❌ Slower for large PDFs (100+ pages)
- ❌ Slightly lower rendering quality (no pdftocairo)
