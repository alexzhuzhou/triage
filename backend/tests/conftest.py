"""
Pytest configuration and fixtures.
"""
import pytest
import uuid as uuid_module
from sqlalchemy import create_engine, event, TypeDecorator, CHAR
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from fastapi.testclient import TestClient


# Define a platform-independent UUID type before importing models
class UUID(TypeDecorator):
    """Platform-independent UUID type for testing."""
    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid=True):
        """Accept as_uuid parameter for compatibility but always store as UUID."""
        self.as_uuid = as_uuid
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid_module.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid_module.UUID):
            return value
        return uuid_module.UUID(value)


# Monkey-patch the PostgreSQL UUID to work with SQLite
import sqlalchemy.dialects.postgresql as postgresql_dialect
postgresql_dialect.UUID = UUID

# Now import the app components
from app.database import Base, get_db
from app.main import app


# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Enable foreign key constraints in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_email_ingest():
    """Sample EmailIngest object for testing."""
    from app.schemas.email import EmailIngest
    from datetime import datetime
    return EmailIngest(
        subject="Test Email",
        sender="test@example.com",
        recipients=["intake@test.com"],
        body="Test email body",
        attachments=[],
        received_at=datetime.utcnow()
    )


@pytest.fixture
def mock_email_message():
    """Create a mock email.Message object."""
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["Subject"] = "Test Subject"
    msg["From"] = "sender@example.com"
    msg["To"] = "recipient@example.com"
    msg["Date"] = "Mon, 15 Jan 2024 10:00:00 +0000"
    msg.set_content("Test email body content")
    return msg
