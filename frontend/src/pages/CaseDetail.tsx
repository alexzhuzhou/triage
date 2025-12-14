import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useCase, useUpdateCase } from '../hooks/useCases';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { StatusBadge } from '../components/StatusBadge';
import { CategoryBadge } from '../components/CategoryBadge';
import { AttachmentPreviewModal } from '../components/AttachmentPreviewModal';
import { EmailPreviewModal } from '../components/EmailPreviewModal';
import { formatDateOnly } from '../utils/dateUtils';
import type { Attachment, Email } from '../types';

export function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: caseData, isLoading, error } = useCase(id!);
  const updateCase = useUpdateCase();

  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    status: '',
    notes: '',
  });
  const [previewAttachment, setPreviewAttachment] = useState<Attachment | null>(null);
  const [previewEmail, setPreviewEmail] = useState<Email | null>(null);

  const handleEdit = () => {
    if (caseData) {
      setEditForm({
        status: caseData.status,
        notes: caseData.notes || '',
      });
      setIsEditing(true);
    }
  };

  const handleSave = async () => {
    if (!id) return;

    await updateCase.mutateAsync({
      id,
      updates: editForm,
    });

    setIsEditing(false);
  };

  if (isLoading) return <LoadingSpinner />;

  if (error || !caseData) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
        Case not found or error loading case.
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <Link
          to="/"
          className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block"
        >
          ← Back to Dashboard
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {caseData.case_number}
            </h1>
            <p className="mt-2 text-gray-600">{caseData.patient_name}</p>
          </div>
          {!isEditing && (
            <button
              onClick={handleEdit}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Edit Case
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Case Information */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Case Information
            </h2>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">Status</label>
                  {isEditing ? (
                    <select
                      value={editForm.status}
                      onChange={(e) =>
                        setEditForm({ ...editForm, status: e.target.value })
                      }
                      className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="pending">Pending</option>
                      <option value="confirmed">Confirmed</option>
                      <option value="completed">Completed</option>
                    </select>
                  ) : (
                    <div className="mt-1">
                      <StatusBadge status={caseData.status} />
                    </div>
                  )}
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Extraction Confidence
                  </label>
                  <div className="mt-1">
                    <ConfidenceBadge confidence={caseData.extraction_confidence} />
                  </div>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-500">Exam Type</label>
                <p className="mt-1 text-gray-900">{caseData.exam_type}</p>
              </div>

              {caseData.exam_date && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Exam Date & Time
                  </label>
                  <p className="mt-1 text-gray-900">
                    {formatDateOnly(caseData.exam_date)}
                    {caseData.exam_time && ` at ${caseData.exam_time}`}
                  </p>
                </div>
              )}

              {caseData.exam_location && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Location</label>
                  <p className="mt-1 text-gray-900">{caseData.exam_location}</p>
                </div>
              )}

              {caseData.referring_party && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Referring Party
                  </label>
                  <p className="mt-1 text-gray-900">{caseData.referring_party}</p>
                  {caseData.referring_email && (
                    <p className="mt-1 text-sm text-gray-600">
                      {caseData.referring_email}
                    </p>
                  )}
                </div>
              )}

              {caseData.report_due_date && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Report Due Date
                  </label>
                  <p className="mt-1 text-gray-900">
                    {formatDateOnly(caseData.report_due_date)}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Notes */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Notes</h2>
            {isEditing ? (
              <textarea
                value={editForm.notes}
                onChange={(e) =>
                  setEditForm({ ...editForm, notes: e.target.value })
                }
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                placeholder="Add notes about this case..."
              />
            ) : (
              <p className="text-gray-700 whitespace-pre-wrap">
                {caseData.notes || 'No notes available.'}
              </p>
            )}
          </div>

          {isEditing && (
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateCase.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {updateCase.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Attachments */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Attachments ({caseData.attachments?.length || 0})
            </h2>
            {caseData.attachments && caseData.attachments.length > 0 ? (
              <div className="space-y-3">
                {caseData.attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    onClick={() => setPreviewAttachment(attachment)}
                    className="border border-gray-200 rounded-lg p-3 cursor-pointer hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <p className="text-sm font-medium text-gray-900 truncate flex-1">
                        {attachment.filename}
                      </p>
                    </div>
                    <CategoryBadge category={attachment.category} />
                    {attachment.category_reason && (
                      <p className="mt-2 text-xs text-gray-600">
                        {attachment.category_reason}
                      </p>
                    )}
                    {attachment.content_preview && (
                      <p className="mt-2 text-xs text-primary-600">
                        Click to preview
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No attachments</p>
            )}
          </div>

          {/* Related Emails */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Related Emails ({caseData.emails?.length || 0})
            </h2>
            {caseData.emails && caseData.emails.length > 0 ? (
              <div className="space-y-3">
                {caseData.emails.map((email) => (
                  <div
                    key={email.id}
                    onClick={() => setPreviewEmail(email)}
                    className="border border-gray-200 rounded-lg p-3 cursor-pointer hover:bg-gray-50 transition-colors"
                  >
                    <p className="text-sm font-medium text-gray-900 mb-1">
                      {email.subject}
                    </p>
                    <p className="text-xs text-gray-600 mb-1">
                      From: {email.sender}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(email.received_at).toLocaleString()}
                    </p>
                    {email.processing_status && (
                      <span
                        className={`mt-2 inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                          email.processing_status === 'processed'
                            ? 'bg-green-100 text-green-800'
                            : email.processing_status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {email.processing_status}
                      </span>
                    )}
                    <p className="mt-2 text-xs text-primary-600">
                      Click to view full email
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No related emails</p>
            )}
          </div>

          {/* Metadata */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h2>
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-gray-500">Created:</span>
                <p className="text-gray-900">
                  {new Date(caseData.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-gray-500">Last Updated:</span>
                <p className="text-gray-900">
                  {new Date(caseData.updated_at).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Attachment Preview Modal */}
      {previewAttachment && (
        <AttachmentPreviewModal
          attachment={previewAttachment}
          onClose={() => setPreviewAttachment(null)}
        />
      )}

      {/* Email Preview Modal */}
      {previewEmail && (
        <EmailPreviewModal
          email={previewEmail}
          onClose={() => setPreviewEmail(null)}
        />
      )}
    </div>
  );
}
