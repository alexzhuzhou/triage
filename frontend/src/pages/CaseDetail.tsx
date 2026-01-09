import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { useCase, useUpdateCase } from '../hooks/useCases';
import { casesApi } from '../api/client';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { StatusBadge } from '../components/StatusBadge';
import { CategoryBadge } from '../components/CategoryBadge';
import { AttachmentPreviewModal } from '../components/AttachmentPreviewModal';
import { EmailPreviewModal } from '../components/EmailPreviewModal';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { formatDateOnly } from '../utils/dateUtils';
import type { Attachment, Email } from '../types';

export function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: caseData, isLoading, error } = useCase(id!);
  const updateCase = useUpdateCase();

  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Delete mutation
  const deleteCase = useMutation({
    mutationFn: () => casesApi.delete(id!),
    onSuccess: (data) => {
      toast.success(`Case ${data.case_number} deleted successfully`);
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      navigate('/');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to delete case');
    },
  });

  const [editForm, setEditForm] = useState({
    patient_name: '',
    exam_type: '',
    exam_date: '',
    exam_time: '',
    exam_location: '',
    referring_party: '',
    referring_email: '',
    report_due_date: '',
    status: '',
    notes: '',
  });
  const [previewAttachment, setPreviewAttachment] = useState<Attachment | null>(null);
  const [previewEmail, setPreviewEmail] = useState<Email | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    // Required fields
    if (!editForm.patient_name.trim()) {
      errors.patient_name = 'Patient name is required';
    }

    if (!editForm.exam_type.trim()) {
      errors.exam_type = 'Exam type is required';
    }

    // Email format validation
    if (editForm.referring_email && editForm.referring_email.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(editForm.referring_email)) {
        errors.referring_email = 'Please enter a valid email address';
      }
    }

    // Date logic validation
    if (editForm.exam_date && editForm.report_due_date) {
      const examDate = new Date(editForm.exam_date);
      const dueDate = new Date(editForm.report_due_date);

      if (dueDate < examDate) {
        errors.report_due_date = 'Report due date must be after exam date';
      }
    }

    // Exam date shouldn't be too far in the past (more than 2 years)
    if (editForm.exam_date) {
      const examDate = new Date(editForm.exam_date);
      const twoYearsAgo = new Date();
      twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);

      if (examDate < twoYearsAgo) {
        errors.exam_date = 'Exam date seems unusually old. Please verify.';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleEdit = () => {
    if (caseData) {
      setEditForm({
        patient_name: caseData.patient_name,
        exam_type: caseData.exam_type,
        exam_date: caseData.exam_date || '',
        exam_time: caseData.exam_time ? caseData.exam_time.substring(0, 5) : '', // Strip seconds for HTML5 time input
        exam_location: caseData.exam_location || '',
        referring_party: caseData.referring_party || '',
        referring_email: caseData.referring_email || '',
        report_due_date: caseData.report_due_date || '',
        status: caseData.status,
        notes: caseData.notes || '',
      });
      setValidationErrors({});
      setIsEditing(true);
    }
  };

  const handleSave = async () => {
    if (!id) return;

    // Validate form before saving
    if (!validateForm()) {
      toast.error('Please fix the validation errors before saving');
      return;
    }

    // Clean empty strings to null for nullable fields
    const cleanedUpdates = {
      ...editForm,
      exam_date: editForm.exam_date || null,
      exam_time: editForm.exam_time || null,
      exam_location: editForm.exam_location || null,
      referring_party: editForm.referring_party || null,
      referring_email: editForm.referring_email || null,
      report_due_date: editForm.report_due_date || null,
      notes: editForm.notes || null,
    };

    try {
      await updateCase.mutateAsync({
        id,
        updates: cleanedUpdates,
      });

      toast.success('Case updated successfully');
      setIsEditing(false);
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to update case';
      toast.error(errorMessage);
      console.error('Failed to update case:', error);
    }
  };

  const handleDelete = () => {
    setShowDeleteDialog(true);
  };

  const confirmDelete = () => {
    deleteCase.mutate();
    setShowDeleteDialog(false);
  };

  const cancelDelete = () => {
    setShowDeleteDialog(false);
  };

  if (isLoading) return <LoadingSpinner />;

  if (error || !caseData) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-800">
        Case not found or error loading case.
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-10">
        <Link
          to="/"
          className="text-base text-orange-600 hover:text-orange-700 mb-6 inline-flex items-center gap-2 font-semibold group"
        >
          <svg className="w-5 h-5 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Dashboard
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 tracking-tight">
              {caseData.case_number}
            </h1>
            {isEditing ? (
              <div className="mt-3">
                <input
                  type="text"
                  value={editForm.patient_name}
                  onChange={(e) =>
                    setEditForm({ ...editForm, patient_name: e.target.value })
                  }
                  required
                  placeholder="Patient Name"
                  className={`px-4 py-2 text-lg border rounded-xl focus:ring-2 focus:ring-orange-500 transition-all font-medium ${
                    validationErrors.patient_name
                      ? 'border-red-300 bg-red-50'
                      : 'border-gray-300'
                  }`}
                />
                {validationErrors.patient_name && (
                  <p className="mt-1 text-sm text-red-600 font-medium">
                    {validationErrors.patient_name}
                  </p>
                )}
              </div>
            ) : (
              <p className="mt-3 text-lg text-gray-600 font-medium">{caseData.patient_name}</p>
            )}
          </div>
          {!isEditing && (
            <div className="flex items-center gap-3">
              <button
                onClick={handleDelete}
                className="px-7 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-all shadow-md font-semibold text-base flex items-center gap-2 group"
                disabled={deleteCase.isPending}
              >
                <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                {deleteCase.isPending ? 'Deleting...' : 'Delete'}
              </button>
              <button
                onClick={handleEdit}
                className="px-7 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-all shadow-md font-semibold text-base flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit Case
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Case Information */}
          <div className="bg-white rounded-2xl shadow-lg p-8 border-2 border-gray-100">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Case Information
            </h2>
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Status</label>
                  {isEditing ? (
                    <select
                      value={editForm.status}
                      onChange={(e) =>
                        setEditForm({ ...editForm, status: e.target.value })
                      }
                      className="mt-2 w-full px-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 transition-all"
                    >
                      <option value="pending">Pending</option>
                      <option value="confirmed">Confirmed</option>
                      <option value="completed">Completed</option>
                    </select>
                  ) : (
                    <div className="mt-2">
                      <StatusBadge status={caseData.status} />
                    </div>
                  )}
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                    Extraction Confidence
                  </label>
                  <div className="mt-2">
                    <ConfidenceBadge confidence={caseData.extraction_confidence} />
                  </div>
                </div>
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Exam Type</label>
                {isEditing ? (
                  <div>
                    <input
                      type="text"
                      value={editForm.exam_type}
                      onChange={(e) =>
                        setEditForm({ ...editForm, exam_type: e.target.value })
                      }
                      required
                      placeholder="e.g., Orthopedic, Psychiatric, Cardiology"
                      className={`mt-2 w-full px-4 py-3 text-base border rounded-xl focus:ring-2 focus:ring-orange-500 transition-all ${
                        validationErrors.exam_type
                          ? 'border-red-300 bg-red-50'
                          : 'border-gray-300'
                      }`}
                    />
                    {validationErrors.exam_type && (
                      <p className="mt-1 text-sm text-red-600 font-medium">
                        {validationErrors.exam_type}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="mt-2 text-base text-gray-900 font-medium">{caseData.exam_type}</p>
                )}
              </div>

              {isEditing ? (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                      Exam Date
                    </label>
                    <input
                      type="date"
                      value={editForm.exam_date}
                      onChange={(e) =>
                        setEditForm({ ...editForm, exam_date: e.target.value })
                      }
                      className={`mt-2 w-full px-4 py-3 text-base border rounded-xl focus:ring-2 focus:ring-orange-500 transition-all ${
                        validationErrors.exam_date
                          ? 'border-red-300 bg-red-50'
                          : 'border-gray-300'
                      }`}
                    />
                    {validationErrors.exam_date && (
                      <p className="mt-1 text-sm text-red-600 font-medium">
                        {validationErrors.exam_date}
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                      Exam Time
                    </label>
                    <input
                      type="time"
                      value={editForm.exam_time}
                      onChange={(e) =>
                        setEditForm({ ...editForm, exam_time: e.target.value })
                      }
                      className="mt-2 w-full px-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 transition-all"
                    />
                  </div>
                </div>
              ) : (
                caseData.exam_date && (
                  <div>
                    <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                      Exam Date & Time
                    </label>
                    <p className="mt-2 text-base text-gray-900 font-medium">
                      {formatDateOnly(caseData.exam_date)}
                      {caseData.exam_time && ` at ${caseData.exam_time}`}
                    </p>
                  </div>
                )
              )}

              {isEditing ? (
                <div>
                  <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Location</label>
                  <input
                    type="text"
                    value={editForm.exam_location}
                    onChange={(e) =>
                      setEditForm({ ...editForm, exam_location: e.target.value })
                    }
                    placeholder="e.g., Main Clinic, Room 201"
                    className="mt-2 w-full px-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 transition-all"
                  />
                </div>
              ) : (
                caseData.exam_location && (
                  <div>
                    <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Location</label>
                    <p className="mt-2 text-base text-gray-900 font-medium">{caseData.exam_location}</p>
                  </div>
                )
              )}

              {isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                      Referring Party
                    </label>
                    <input
                      type="text"
                      value={editForm.referring_party}
                      onChange={(e) =>
                        setEditForm({ ...editForm, referring_party: e.target.value })
                      }
                      placeholder="e.g., Dr. Smith, ABC Law Firm"
                      className="mt-2 w-full px-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 transition-all"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                      Referring Email
                    </label>
                    <input
                      type="email"
                      value={editForm.referring_email}
                      onChange={(e) =>
                        setEditForm({ ...editForm, referring_email: e.target.value })
                      }
                      placeholder="email@example.com"
                      className={`mt-2 w-full px-4 py-3 text-base border rounded-xl focus:ring-2 focus:ring-orange-500 transition-all ${
                        validationErrors.referring_email
                          ? 'border-red-300 bg-red-50'
                          : 'border-gray-300'
                      }`}
                    />
                    {validationErrors.referring_email && (
                      <p className="mt-1 text-sm text-red-600 font-medium">
                        {validationErrors.referring_email}
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                caseData.referring_party && (
                  <div>
                    <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                      Referring Party
                    </label>
                    <p className="mt-2 text-base text-gray-900 font-medium">{caseData.referring_party}</p>
                    {caseData.referring_email && (
                      <p className="mt-1.5 text-sm text-gray-600 font-medium">
                        {caseData.referring_email}
                      </p>
                    )}
                  </div>
                )
              )}

              {isEditing ? (
                <div>
                  <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                    Report Due Date
                  </label>
                  <input
                    type="date"
                    value={editForm.report_due_date}
                    onChange={(e) =>
                      setEditForm({ ...editForm, report_due_date: e.target.value })
                    }
                    className={`mt-2 w-full px-4 py-3 text-base border rounded-xl focus:ring-2 focus:ring-orange-500 transition-all ${
                      validationErrors.report_due_date
                        ? 'border-red-300 bg-red-50'
                        : 'border-gray-300'
                    }`}
                  />
                  {validationErrors.report_due_date && (
                    <p className="mt-1 text-sm text-red-600 font-medium">
                      {validationErrors.report_due_date}
                    </p>
                  )}
                </div>
              ) : (
                caseData.report_due_date && (
                  <div>
                    <label className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                      Report Due Date
                    </label>
                    <p className="mt-2 text-base text-gray-900 font-medium">
                      {formatDateOnly(caseData.report_due_date)}
                    </p>
                  </div>
                )
              )}
            </div>
          </div>

          {/* Notes */}
          <div className="bg-white rounded-2xl shadow-lg p-8 border-2 border-gray-100">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Notes</h2>
            {isEditing ? (
              <textarea
                value={editForm.notes}
                onChange={(e) =>
                  setEditForm({ ...editForm, notes: e.target.value })
                }
                rows={5}
                className="w-full px-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 transition-all"
                placeholder="Add notes about this case..."
              />
            ) : (
              <p className="text-base text-gray-700 whitespace-pre-wrap leading-relaxed">
                {caseData.notes || 'No notes available.'}
              </p>
            )}
          </div>

          {isEditing && (
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => setIsEditing(false)}
                className="px-7 py-3 border-2 border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition-all font-semibold text-base"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateCase.isPending || Object.keys(validationErrors).length > 0}
                className="px-7 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md font-semibold text-base flex items-center gap-2"
              >
                {updateCase.isPending ? (
                  <>
                    <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Saving...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Save Changes
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Attachments */}
          <div className="bg-white rounded-2xl shadow-lg p-6 border-2 border-gray-100">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-gray-900">
                Attachments
              </h2>
              <span className="px-3 py-1 bg-orange-100 text-orange-700 rounded-lg text-sm font-semibold">
                {caseData.attachments?.length || 0}
              </span>
            </div>
            {caseData.attachments && caseData.attachments.length > 0 ? (
              <div className="space-y-3">
                {caseData.attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    onClick={() => setPreviewAttachment(attachment)}
                    className="border border-gray-200 rounded-xl p-3 cursor-pointer hover:bg-orange-50 hover:border-orange-200 transition-all"
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
                      <p className="mt-2 text-xs text-orange-600">
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
          <div className="bg-white rounded-2xl shadow-lg p-6 border-2 border-gray-100">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-gray-900">
                Related Emails
              </h2>
              <span className="px-3 py-1 bg-orange-100 text-orange-700 rounded-lg text-sm font-semibold">
                {caseData.emails?.length || 0}
              </span>
            </div>
            {caseData.emails && caseData.emails.length > 0 ? (
              <div className="space-y-3">
                {caseData.emails.map((email) => (
                  <div
                    key={email.id}
                    onClick={() => setPreviewEmail(email)}
                    className="border border-gray-200 rounded-xl p-3 cursor-pointer hover:bg-orange-50 hover:border-orange-200 transition-all"
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
                    <p className="mt-2 text-xs text-orange-600">
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
          <div className="bg-white rounded-2xl shadow-lg p-6 border-2 border-gray-100">
            <h2 className="text-xl font-bold text-gray-900 mb-5">Metadata</h2>
            <div className="space-y-4">
              <div>
                <span className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Created</span>
                <p className="mt-1 text-base text-gray-900 font-medium">
                  {new Date(caseData.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Last Updated</span>
                <p className="mt-1 text-base text-gray-900 font-medium">
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

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteDialog}
        title="Delete Case?"
        message={`Are you sure you want to delete case ${caseData.case_number}? This action cannot be undone. All associated emails and attachments will be permanently deleted.`}
        confirmText="Delete Case"
        cancelText="Cancel"
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
        isDestructive={true}
      />
    </div>
  );
}
