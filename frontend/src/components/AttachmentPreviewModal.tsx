import { Attachment } from '../types';

interface AttachmentPreviewModalProps {
  attachment: Attachment;
  onClose: () => void;
}

export function AttachmentPreviewModal({
  attachment,
  onClose,
}: AttachmentPreviewModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-semibold text-gray-900 truncate">
              {attachment.filename}
            </h2>
            {attachment.content_type && (
              <p className="text-sm text-gray-500 mt-1">
                {attachment.content_type}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* AI Summary Section */}
          {attachment.summary && (
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
              <div className="flex items-start space-x-2">
                <svg
                  className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-blue-900 mb-1">
                    AI-Generated Summary
                  </h3>
                  <p className="text-sm text-blue-800 leading-relaxed">
                    {attachment.summary}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Content Preview Section */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Content Preview (First 500 characters)
            </h3>
            {attachment.content_preview ? (
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                  {attachment.content_preview}
                </p>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg p-8 text-center border border-gray-200">
                <p className="text-gray-500">No text preview available for this attachment.</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t">
          <div className="flex items-center space-x-3">
            {attachment.file_path ? (
              <button
                onClick={() => {
                  // TODO: Implement cloud storage PDF viewing
                  alert('Cloud storage integration coming soon! This will open the full PDF document.');
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span>View Full PDF</span>
              </button>
            ) : (
              <div className="text-sm text-gray-500 italic">
                Full document will be available when cloud storage is configured
              </div>
            )}
          </div>
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
