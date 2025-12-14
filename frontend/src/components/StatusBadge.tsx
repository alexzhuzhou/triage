import clsx from 'clsx';

interface StatusBadgeProps {
  status: 'pending' | 'confirmed' | 'completed';
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        {
          'bg-gray-100 text-gray-800': status === 'pending',
          'bg-blue-100 text-blue-800': status === 'confirmed',
          'bg-green-100 text-green-800': status === 'completed',
        }
      )}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
