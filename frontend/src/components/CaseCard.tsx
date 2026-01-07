import { Link } from 'react-router-dom';
import type { Case } from '../types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { StatusBadge } from './StatusBadge';
import { formatDateOnly } from '../utils/dateUtils';

interface CaseCardProps {
  case: Case;
}

export function CaseCard({ case: caseData }: CaseCardProps) {
  return (
    <Link
      to={`/cases/${caseData.id}`}
      className="block bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all p-7 border-2 border-gray-100 hover:border-orange-300 group hover:-translate-y-1"
    >
      <div className="flex justify-between items-start mb-5">
        <div className="flex-1">
          <h3 className="text-xl font-bold text-gray-900 mb-1 group-hover:text-orange-600 transition-colors">
            {caseData.case_number}
          </h3>
          <p className="text-base text-gray-600 font-medium">{caseData.patient_name}</p>
        </div>
        <StatusBadge status={caseData.status} />
      </div>

      <div className="space-y-3 mb-5">
        <div className="flex items-start">
          <div className="flex items-center gap-2 min-w-[120px]">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span className="text-sm text-gray-500 font-medium">Exam Type:</span>
          </div>
          <span className="text-sm text-gray-900 font-semibold">{caseData.exam_type}</span>
        </div>

        {caseData.exam_date && (
          <div className="flex items-start">
            <div className="flex items-center gap-2 min-w-[120px]">
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span className="text-sm text-gray-500 font-medium">Exam Date:</span>
            </div>
            <span className="text-sm text-gray-900 font-semibold">
              {formatDateOnly(caseData.exam_date)}
              {caseData.exam_time && ` at ${caseData.exam_time}`}
            </span>
          </div>
        )}

        {caseData.exam_location && (
          <div className="flex items-start">
            <div className="flex items-center gap-2 min-w-[120px]">
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="text-sm text-gray-500 font-medium">Location:</span>
            </div>
            <span className="text-sm text-gray-900 font-semibold">{caseData.exam_location}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-5 border-t border-gray-100">
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 font-semibold uppercase tracking-wide">Confidence:</span>
          <ConfidenceBadge confidence={caseData.extraction_confidence} />
        </div>

        {caseData.attachments && caseData.attachments.length > 0 && (
          <div className="flex items-center gap-1.5">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
            <span className="text-sm text-gray-600 font-medium">
              {caseData.attachments.length}
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}
