"""add indexes and file storage fields

Revision ID: 002
Revises: 001
Create Date: 2025-12-13 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add file storage columns to attachments
    op.add_column('attachments', sa.Column('file_path', sa.String(), nullable=True))
    op.add_column('attachments', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('attachments', sa.Column('storage_provider', sa.String(), nullable=True))

    # Create indexes on cases table
    op.create_index('ix_cases_status', 'cases', ['status'])
    op.create_index('ix_cases_extraction_confidence', 'cases', ['extraction_confidence'])
    op.create_index('ix_cases_created_at', 'cases', ['created_at'])
    op.create_index('ix_cases_exam_date', 'cases', ['exam_date'])

    # Create indexes on emails table
    op.create_index('ix_emails_case_id', 'emails', ['case_id'])
    op.create_index('ix_emails_processing_status', 'emails', ['processing_status'])
    op.create_index('ix_emails_received_at', 'emails', ['received_at'])

    # Create indexes on attachments table
    op.create_index('ix_attachments_email_id', 'attachments', ['email_id'])
    op.create_index('ix_attachments_case_id', 'attachments', ['case_id'])
    op.create_index('ix_attachments_category', 'attachments', ['category'])


def downgrade() -> None:
    # Drop indexes on attachments
    op.drop_index('ix_attachments_category', table_name='attachments')
    op.drop_index('ix_attachments_case_id', table_name='attachments')
    op.drop_index('ix_attachments_email_id', table_name='attachments')

    # Drop indexes on emails
    op.drop_index('ix_emails_received_at', table_name='emails')
    op.drop_index('ix_emails_processing_status', table_name='emails')
    op.drop_index('ix_emails_case_id', table_name='emails')

    # Drop indexes on cases
    op.drop_index('ix_cases_exam_date', table_name='cases')
    op.drop_index('ix_cases_created_at', table_name='cases')
    op.drop_index('ix_cases_extraction_confidence', table_name='cases')
    op.drop_index('ix_cases_status', table_name='cases')

    # Drop file storage columns from attachments
    op.drop_column('attachments', 'storage_provider')
    op.drop_column('attachments', 'file_size')
    op.drop_column('attachments', 'file_path')
