"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-03-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create cases table
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_number', sa.String(), nullable=False),
        sa.Column('patient_name', sa.String(), nullable=False),
        sa.Column('exam_type', sa.String(), nullable=False),
        sa.Column('exam_date', sa.Date(), nullable=True),
        sa.Column('exam_time', sa.Time(), nullable=True),
        sa.Column('exam_location', sa.String(), nullable=True),
        sa.Column('referring_party', sa.String(), nullable=True),
        sa.Column('referring_email', sa.String(), nullable=True),
        sa.Column('report_due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'CONFIRMED', 'COMPLETED', name='casestatus'), nullable=False),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cases_case_number'), 'cases', ['case_number'], unique=True)

    # Create emails table
    op.create_table(
        'emails',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('sender', sa.String(), nullable=False),
        sa.Column('recipients', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('processing_status', sa.Enum('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED', name='emailprocessingstatus'), nullable=False),
        sa.Column('raw_extraction', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create attachments table
    op.create_table(
        'attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('content_preview', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum('MEDICAL_RECORDS', 'DECLARATION', 'COVER_LETTER', 'OTHER', name='attachmentcategory'), nullable=False),
        sa.Column('category_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('attachments')
    op.drop_table('emails')
    op.drop_index(op.f('ix_cases_case_number'), table_name='cases')
    op.drop_table('cases')

    # Drop enums
    sa.Enum(name='attachmentcategory').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='emailprocessingstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='casestatus').drop(op.get_bind(), checkfirst=True)
