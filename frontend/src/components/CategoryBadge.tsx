import clsx from 'clsx';

interface CategoryBadgeProps {
  category: 'medical_records' | 'declaration' | 'cover_letter' | 'other';
}

const categoryLabels = {
  medical_records: 'Medical Records',
  declaration: 'Declaration',
  cover_letter: 'Cover Letter',
  other: 'Other',
};

export function CategoryBadge({ category }: CategoryBadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        {
          'bg-purple-100 text-purple-800': category === 'medical_records',
          'bg-blue-100 text-blue-800': category === 'declaration',
          'bg-green-100 text-green-800': category === 'cover_letter',
          'bg-gray-100 text-gray-800': category === 'other',
        }
      )}
    >
      {categoryLabels[category]}
    </span>
  );
}
