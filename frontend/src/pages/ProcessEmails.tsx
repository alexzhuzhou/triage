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
      <div className="mb-10">
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Process Emails</h1>
        <p className="mt-3 text-lg text-gray-600">
          Process sample emails from the backend
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-8 mb-10 border-2 border-gray-100">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 bg-orange-100 rounded-xl">
            <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900">
            Batch Processing
          </h2>
        </div>
        <p className="text-base text-gray-600 mb-7 leading-relaxed">
          Click the button below to process all sample emails in the{' '}
          <code className="px-2.5 py-1 bg-orange-50 border border-orange-200 rounded-lg text-sm font-mono text-orange-700">
            backend/sample_emails/
          </code>{' '}
          directory. The system will extract case data using OpenAI and create or
          update cases accordingly.
        </p>

        <button
          onClick={handleProcess}
          disabled={processBatch.isPending}
          className="px-8 py-4 bg-orange-500 text-white rounded-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md font-semibold text-base flex items-center gap-3"
        >
          {processBatch.isPending ? (
            <>
              <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Process Sample Emails
            </>
          )}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="bg-white rounded-2xl shadow-lg p-8 border-2 border-gray-100">
          <h2 className="text-2xl font-bold text-gray-900 mb-7">Results</h2>

          {/* Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-green-700 uppercase tracking-wide">Processed</div>
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="text-4xl font-bold text-green-900">
                {result.processed}
              </div>
            </div>
            <div className="bg-gradient-to-br from-red-50 to-rose-50 border border-red-200 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-red-700 uppercase tracking-wide">Failed</div>
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="text-4xl font-bold text-red-900">
                {result.failed}
              </div>
            </div>
            <div className="bg-gradient-to-br from-orange-50 to-amber-50 border border-orange-200 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-orange-700 uppercase tracking-wide">Total</div>
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="text-4xl font-bold text-orange-900">
                {result.emails?.length || 0}
              </div>
            </div>
          </div>

          {/* Email Details */}
          {result.emails && result.emails.length > 0 && (
            <div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">
                Email Details
              </h3>
              <div className="space-y-3">
                {result.emails.map((email: any, index: number) => (
                  <div
                    key={index}
                    className={`border rounded-xl p-4 ${
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
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-800">
          Failed to process emails. Please check that the backend is running and
          try again.
        </div>
      )}
    </div>
  );
}
