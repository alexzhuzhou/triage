import { Link } from 'react-router-dom';
import type { Case } from '../types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { StatusBadge } from './StatusBadge';

interface CaseCardProps {
  case: Case;
}

export function CaseCard({ case: caseData }: CaseCardProps) {
  return (
    <Link
      to={`/cases/${caseData.id}`}
      className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6"
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {caseData.case_number}
          </h3>
          <p className="text-sm text-gray-600">{caseData.patient_name}</p>
        </div>
        <StatusBadge status={caseData.status} />
      </div>

      <div className="space-y-2 mb-4">
        <div className="flex items-center text-sm">
          <span className="text-gray-500 w-24">Exam Type:</span>
          <span className="text-gray-900">{caseData.exam_type}</span>
        </div>

        {caseData.exam_date && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Exam Date:</span>
            <span className="text-gray-900">
              {new Date(caseData.exam_date).toLocaleDateString()}
              {caseData.exam_time && ` at ${caseData.exam_time}`}
            </span>
          </div>
        )}

        {caseData.exam_location && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Location:</span>
            <span className="text-gray-900">{caseData.exam_location}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-4 border-t">
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">Confidence:</span>
          <ConfidenceBadge confidence={caseData.extraction_confidence} />
        </div>

        {caseData.attachments && caseData.attachments.length > 0 && (
          <span className="text-xs text-gray-500">
            {caseData.attachments.length} attachment
            {caseData.attachments.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
    </Link>
  );
}
