import clsx from 'clsx';

interface ConfidenceBadgeProps {
  confidence: number | null;
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (confidence === null || confidence === undefined) {
    return (
      <span className="inline-flex items-center px-3.5 py-1.5 rounded-lg text-sm font-semibold bg-gray-100 text-gray-600 border border-gray-200">
        N/A
      </span>
    );
  }

  const percentage = Math.round(confidence * 100);
  const variant =
    confidence >= 0.8
      ? 'high'
      : confidence >= 0.5
      ? 'medium'
      : 'low';

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-semibold',
        {
          'bg-green-100 text-green-800 border border-green-200': variant === 'high',
          'bg-yellow-100 text-yellow-800 border border-yellow-200': variant === 'medium',
          'bg-red-100 text-red-800 border border-red-200': variant === 'low',
        }
      )}
    >
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
      </svg>
      {percentage}%
    </span>
  );
}
