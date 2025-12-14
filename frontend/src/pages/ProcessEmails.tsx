import { useState } from 'react';
import { useProcessBatch } from '../hooks/useEmails';

export function ProcessEmails() {
  const processBatch = useProcessBatch();
  const [result, setResult] = useState<any>(null);

  const handleProcess = async () => {
    try {
      const data = await processBatch.mutateAsync();
      setResult(data);
    } catch (error) {
      console.error('Failed to process emails:', error);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Process Emails</h1>
        <p className="mt-2 text-gray-600">
          Process sample emails from the backend
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Batch Processing
        </h2>
        <p className="text-gray-600 mb-6">
          Click the button below to process all sample emails in the{' '}
          <code className="px-2 py-1 bg-gray-100 rounded text-sm">
            backend/sample_emails/
          </code>{' '}
          directory. The system will extract case data using OpenAI and create or
          update cases accordingly.
        </p>

        <button
          onClick={handleProcess}
          disabled={processBatch.isPending}
          className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {processBatch.isPending ? 'Processing...' : 'Process Sample Emails'}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Results</h2>

          {/* Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="text-sm font-medium text-green-800">Processed</div>
              <div className="mt-1 text-2xl font-bold text-green-900">
                {result.processed}
              </div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="text-sm font-medium text-red-800">Failed</div>
              <div className="mt-1 text-2xl font-bold text-red-900">
                {result.failed}
              </div>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="text-sm font-medium text-blue-800">Total</div>
              <div className="mt-1 text-2xl font-bold text-blue-900">
                {result.emails?.length || 0}
              </div>
            </div>
          </div>

          {/* Email Details */}
          {result.emails && result.emails.length > 0 && (
            <div>
              <h3 className="text-md font-semibold text-gray-900 mb-3">
                Email Details
              </h3>
              <div className="space-y-3">
                {result.emails.map((email: any, index: number) => (
                  <div
                    key={index}
                    className={`border rounded-lg p-4 ${
                      email.error
                        ? 'border-red-200 bg-red-50'
                        : 'border-green-200 bg-green-50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">
                          {email.filename}
                        </p>
                        {email.case_id && (
                          <p className="mt-1 text-sm text-gray-600">
                            Case ID: {email.case_id}
                          </p>
                        )}
                        {email.email_id && (
                          <p className="mt-1 text-sm text-gray-600">
                            Email ID: {email.email_id}
                          </p>
                        )}
                        {email.error && (
                          <p className="mt-2 text-sm text-red-700">
                            Error: {email.error}
                          </p>
                        )}
                      </div>
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          email.error
                            ? 'bg-red-100 text-red-800'
                            : 'bg-green-100 text-green-800'
                        }`}
                      >
                        {email.status || (email.error ? 'failed' : 'success')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {processBatch.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          Failed to process emails. Please check that the backend is running and
          try again.
        </div>
      )}
    </div>
  );
}
