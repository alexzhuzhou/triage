import { Email } from '../types';

interface EmailPreviewModalProps {
  email: Email;
  onClose: () => void;
}

export function EmailPreviewModal({ email, onClose }: EmailPreviewModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-semibold text-gray-900">
              {email.subject}
            </h2>
            <div className="mt-2 space-y-1">
              <p className="text-sm text-gray-600">
                <span className="font-medium">From:</span> {email.sender}
              </p>
              <p className="text-sm text-gray-600">
                <span className="font-medium">To:</span>{' '}
                {email.recipients.join(', ')}
              </p>
              <p className="text-sm text-gray-600">
                <span className="font-medium">Date:</span>{' '}
                {new Date(email.received_at).toLocaleString()}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <p className="text-sm text-gray-800 whitespace-pre-wrap">
              {email.body}
            </p>
          </div>

          {/* Processing Info */}
          {(email.processing_status || email.error_message) && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">
                Processing Information
              </h3>
              <div className="space-y-2">
                {email.processing_status && (
                  <p className="text-sm text-blue-800">
                    <span className="font-medium">Status:</span>{' '}
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        email.processing_status === 'processed'
                          ? 'bg-green-100 text-green-800'
                          : email.processing_status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {email.processing_status}
                    </span>
                  </p>
                )}
                {email.processed_at && (
                  <p className="text-sm text-blue-800">
                    <span className="font-medium">Processed:</span>{' '}
                    {new Date(email.processed_at).toLocaleString()}
                  </p>
                )}
                {email.error_message && (
                  <p className="text-sm text-red-700">
                    <span className="font-medium">Error:</span>{' '}
                    {email.error_message}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-6 border-t space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
