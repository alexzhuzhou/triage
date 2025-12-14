import clsx from 'clsx';

interface ConfidenceBadgeProps {
  confidence: number | null;
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (confidence === null || confidence === undefined) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
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
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        {
          'bg-green-100 text-green-800': variant === 'high',
          'bg-yellow-100 text-yellow-800': variant === 'medium',
          'bg-red-100 text-red-800': variant === 'low',
        }
      )}
    >
      {percentage}%
    </span>
  );
}
