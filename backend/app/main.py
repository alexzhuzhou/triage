"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import emails, cases, attachments
from app.config import settings

# Create FastAPI app
app = FastAPI(
    title="Triage - IME Email Processing",
    description="Backend service for processing IME referral emails with LLM extraction",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(emails.router)
app.include_router(cases.router)
app.include_router(attachments.router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "service": "Triage - IME Email Processing",
        "version": "1.0.0",
        "environment": settings.ENV,
        "docs": "/docs",
        "endpoints": {
            "emails": "/emails",
            "cases": "/cases",
            "attachments": "/attachments"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
