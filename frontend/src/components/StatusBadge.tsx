import clsx from 'clsx';

interface StatusBadgeProps {
  status: 'pending' | 'confirmed' | 'completed';
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-semibold',
        {
          'bg-amber-100 text-amber-800 border border-amber-200': status === 'pending',
          'bg-orange-100 text-orange-800 border border-orange-200': status === 'confirmed',
          'bg-green-100 text-green-800 border border-green-200': status === 'completed',
        }
      )}
    >
      <span className={clsx(
        'w-2 h-2 rounded-full',
        {
          'bg-amber-500': status === 'pending',
          'bg-orange-500': status === 'confirmed',
          'bg-green-500': status === 'completed',
        }
      )} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
