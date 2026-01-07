import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emailsApi, queueApi } from '../api/client';
import { Email } from '../types';

export function QueueManagement() {
  const queryClient = useQueryClient();
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);

  // Fetch failed emails
  const { data: failedEmails = [], isLoading: loadingEmails, refetch: refetchEmails } = useQuery({
    queryKey: ['emails', 'failed'],
    queryFn: () => emailsApi.getAll('failed'),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  });

  // Fetch queue status
  const { data: queueStatus, isLoading: loadingQueue } = useQuery({
    queryKey: ['queue', 'status'],
    queryFn: () => queueApi.getStatus(),
    refetchInterval: 3000, // Auto-refresh every 3 seconds
  });

  // Fetch queue health
  const { data: queueHealth } = useQuery({
    queryKey: ['queue', 'health'],
    queryFn: () => queueApi.getHealth(),
    refetchInterval: 5000,
  });

  // Retry single email mutation
  const retryMutation = useMutation({
    mutationFn: (emailId: string) => emailsApi.retry(emailId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails', 'failed'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      setSelectedEmail(null);
    },
  });

  // Retry all emails mutation
  const retryAllMutation = useMutation({
    mutationFn: () => emailsApi.retryAll(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails', 'failed'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
  });

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-50';
      case 'degraded':
        return 'text-yellow-600 bg-yellow-50';
      case 'unhealthy':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Queue Management</h1>
          <p className="mt-2 text-gray-600">
            Monitor queue status and retry failed emails
          </p>
        </div>

        {/* Queue Health Status */}
        {queueHealth && (
          <div className={`mb-6 p-4 rounded-lg border ${getHealthColor(queueHealth.status)}`}>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">
                  Queue Health: {queueHealth.status.toUpperCase()}
                </h3>
                <p className="text-sm mt-1">{queueHealth.message}</p>
                {queueHealth.error && (
                  <p className="text-sm mt-1 font-mono">{queueHealth.error}</p>
                )}
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">{queueHealth.worker_count}</div>
                <div className="text-sm">Active Workers</div>
              </div>
            </div>
          </div>
        )}

        {/* Queue Statistics */}
        {queueStatus && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <StatCard
              label="Queued"
              value={queueStatus.counts.queued}
              color="blue"
            />
            <StatCard
              label="Processing"
              value={queueStatus.counts.started}
              color="purple"
            />
            <StatCard
              label="Scheduled"
              value={queueStatus.counts.scheduled}
              color="yellow"
            />
            <StatCard
              label="Finished"
              value={queueStatus.counts.finished}
              color="green"
            />
            <StatCard
              label="Failed"
              value={queueStatus.counts.failed}
              color="red"
            />
            <StatCard
              label="Total Jobs"
              value={queueStatus.total_jobs}
              color="gray"
            />
          </div>
        )}

        {/* Failed Emails Section */}
        <div className="bg-white shadow-sm rounded-lg border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Failed Emails</h2>
              <p className="text-sm text-gray-600 mt-1">
                {failedEmails.length} email{failedEmails.length !== 1 ? 's' : ''} failed processing
              </p>
            </div>
            {failedEmails.length > 0 && (
              <button
                onClick={() => retryAllMutation.mutate()}
                disabled={retryAllMutation.isPending}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {retryAllMutation.isPending ? 'Retrying...' : 'Retry All Failed'}
              </button>
            )}
          </div>

          <div className="divide-y divide-gray-200">
            {loadingEmails ? (
              <div className="px-6 py-12 text-center text-gray-500">
                Loading failed emails...
              </div>
            ) : failedEmails.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                No failed emails! All emails processed successfully.
              </div>
            ) : (
              failedEmails.map((email) => (
                <div
                  key={email.id}
                  className="px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-medium text-gray-900 truncate">
                          {email.subject}
                        </h3>
                        <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded">
                          FAILED
                        </span>
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        <p>
                          <span className="font-medium">From:</span> {email.sender}
                        </p>
                        <p>
                          <span className="font-medium">Received:</span>{' '}
                          {new Date(email.received_at).toLocaleString()}
                        </p>
                        {email.processed_at && (
                          <p>
                            <span className="font-medium">Failed at:</span>{' '}
                            {new Date(email.processed_at).toLocaleString()}
                          </p>
                        )}
                        {email.error_message && (
                          <div className="mt-2 p-3 bg-red-50 rounded border border-red-200">
                            <p className="font-medium text-red-900 text-xs mb-1">Error:</p>
                            <p className="text-xs text-red-700 font-mono">
                              {email.error_message}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0 flex gap-2">
                      <button
                        onClick={() => setSelectedEmail(email)}
                        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        View Details
                      </button>
                      <button
                        onClick={() => retryMutation.mutate(email.id)}
                        disabled={retryMutation.isPending}
                        className="px-3 py-1.5 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {retryMutation.isPending ? 'Retrying...' : 'Retry'}
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Email Detail Modal */}
        {selectedEmail && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h3 className="text-xl font-semibold text-gray-900">Email Details</h3>
                <button
                  onClick={() => setSelectedEmail(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="px-6 py-4 overflow-y-auto max-h-[calc(80vh-8rem)]">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Subject</label>
                    <p className="mt-1 text-gray-900">{selectedEmail.subject}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">From</label>
                    <p className="mt-1 text-gray-900">{selectedEmail.sender}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">To</label>
                    <p className="mt-1 text-gray-900">{selectedEmail.recipients.join(', ')}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Body</label>
                    <div className="mt-1 p-3 bg-gray-50 rounded border border-gray-200 max-h-64 overflow-y-auto">
                      <pre className="whitespace-pre-wrap text-sm text-gray-900 font-sans">
                        {selectedEmail.body}
                      </pre>
                    </div>
                  </div>
                  {selectedEmail.error_message && (
                    <div>
                      <label className="block text-sm font-medium text-red-700">Error Message</label>
                      <div className="mt-1 p-3 bg-red-50 rounded border border-red-200">
                        <pre className="whitespace-pre-wrap text-sm text-red-700 font-mono">
                          {selectedEmail.error_message}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  onClick={() => setSelectedEmail(null)}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    retryMutation.mutate(selectedEmail.id);
                    setSelectedEmail(null);
                  }}
                  disabled={retryMutation.isPending}
                  className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors"
                >
                  Retry This Email
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    gray: 'bg-gray-50 text-gray-700 border-gray-200',
  };

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color as keyof typeof colorClasses]}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm mt-1">{label}</div>
    </div>
  );
}
