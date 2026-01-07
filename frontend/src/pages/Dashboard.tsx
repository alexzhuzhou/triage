import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useCases } from '../hooks/useCases';
import { CaseCard } from '../components/CaseCard';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { StatusBadge } from '../components/StatusBadge';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { formatDateOnly } from '../utils/dateUtils';
import type { CaseFilters } from '../types';

type ViewMode = 'grid' | 'table';

export function Dashboard() {
  const [filters, setFilters] = useState<CaseFilters>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  const { data: cases, isLoading, error } = useCases(filters);

  // Client-side search filtering
  const filteredCases = useMemo(() => {
    if (!cases) return [];
    if (!searchTerm) return cases;

    const search = searchTerm.toLowerCase();
    return cases.filter(
      (c) =>
        c.case_number.toLowerCase().includes(search) ||
        c.patient_name.toLowerCase().includes(search) ||
        c.exam_type.toLowerCase().includes(search)
    );
  }, [cases, searchTerm]);

  const stats = useMemo(() => {
    if (!cases) return { total: 0, pending: 0, confirmed: 0, completed: 0 };
    return {
      total: cases.length,
      pending: cases.filter((c) => c.status === 'pending').length,
      confirmed: cases.filter((c) => c.status === 'confirmed').length,
      completed: cases.filter((c) => c.status === 'completed').length,
    };
  }, [cases]);

  return (
    <div>
      <div className="mb-10 flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Cases Dashboard</h1>
          <p className="mt-3 text-lg text-gray-600">
            Manage and monitor IME cases
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-2 bg-white border border-orange-100 rounded-xl p-1.5 shadow-md">
          <button
            onClick={() => setViewMode('grid')}
            className={`px-5 py-2.5 rounded-lg transition-all flex items-center gap-2 ${
              viewMode === 'grid'
                ? 'bg-orange-500 text-white shadow-md'
                : 'text-gray-600 hover:bg-orange-50'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
            <span className="text-sm font-semibold">Grid</span>
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`px-5 py-2.5 rounded-lg transition-all flex items-center gap-2 ${
              viewMode === 'table'
                ? 'bg-orange-500 text-white shadow-md'
                : 'text-gray-600 hover:bg-orange-50'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <span className="text-sm font-semibold">Table</span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
        <div className="group bg-white rounded-2xl shadow-lg p-7 border-2 border-gray-100 hover:border-gray-200 hover:shadow-xl transition-all duration-200 hover:-translate-y-1">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-bold text-gray-600 uppercase tracking-wide">Total Cases</div>
            <div className="p-3 bg-gradient-to-br from-gray-100 to-gray-200 rounded-xl group-hover:scale-110 transition-transform">
              <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
          <div className="text-4xl font-semibold text-gray-900 mb-2">{stats.total}</div>
          <div className="text-sm text-gray-600 font-medium">All time</div>
        </div>
        <div className="group bg-white rounded-2xl shadow-lg p-7 border-2 border-amber-100 hover:border-amber-200 hover:shadow-xl transition-all duration-200 hover:-translate-y-1">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-bold text-amber-700 uppercase tracking-wide">Pending</div>
            <div className="p-3 bg-gradient-to-br from-amber-100 to-amber-200 rounded-xl group-hover:scale-110 transition-transform">
              <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="text-4xl font-semibold text-amber-700 mb-2">{stats.pending}</div>
          <div className="text-sm text-amber-700 font-medium">Awaiting review</div>
        </div>
        <div className="group bg-white rounded-2xl shadow-lg p-7 border-2 border-orange-100 hover:border-orange-200 hover:shadow-xl transition-all duration-200 hover:-translate-y-1">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-bold text-orange-700 uppercase tracking-wide">Confirmed</div>
            <div className="p-3 bg-gradient-to-br from-orange-100 to-orange-200 rounded-xl group-hover:scale-110 transition-transform">
              <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="text-4xl font-semibold text-orange-700 mb-2">{stats.confirmed}</div>
          <div className="text-sm text-orange-700 font-medium">In progress</div>
        </div>
        <div className="group bg-white rounded-2xl shadow-lg p-7 border-2 border-green-100 hover:border-green-200 hover:shadow-xl transition-all duration-200 hover:-translate-y-1">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-bold text-green-700 uppercase tracking-wide">Completed</div>
            <div className="p-3 bg-gradient-to-br from-green-100 to-green-200 rounded-xl group-hover:scale-110 transition-transform">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
          <div className="text-4xl font-semibold text-green-700 mb-2">{stats.completed}</div>
          <div className="text-sm text-green-700 font-medium">Successfully finished</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-lg p-8 mb-10 border-2 border-gray-100">
        <div className="flex items-center gap-3 mb-6">
          <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          <h2 className="text-xl font-bold text-gray-900">Filter Cases</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {/* Search */}
          <div className="md:col-span-2">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Search
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Case number, patient name, or exam type..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-11 pr-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all"
              />
            </div>
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filters.status || ''}
              onChange={(e) =>
                setFilters({ ...filters, status: e.target.value || undefined })
              }
              className="w-full px-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all appearance-none bg-white"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="confirmed">Confirmed</option>
              <option value="completed">Completed</option>
            </select>
          </div>

          {/* Confidence Filter */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Min Confidence
            </label>
            <select
              value={filters.min_confidence ?? ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  min_confidence: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              className="w-full px-4 py-3 text-base border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all appearance-none bg-white"
            >
              <option value="">All Levels</option>
              <option value="0.8">High (≥80%)</option>
              <option value="0.5">Medium (≥50%)</option>
              <option value="0">Low (All)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Cases Grid */}
      {isLoading && <LoadingSpinner />}

      {error && (
        <div className="bg-white border-2 border-red-200 rounded-2xl p-8 shadow-lg">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-red-100 rounded-xl">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-red-900 mb-1">Error Loading Cases</h3>
              <p className="text-red-700">Please try again or contact support if the issue persists.</p>
            </div>
          </div>
        </div>
      )}

      {filteredCases && filteredCases.length === 0 && (
        <div className="bg-white border-2 border-gray-100 rounded-2xl p-16 text-center shadow-lg">
          <div className="max-w-md mx-auto">
            <div className="mx-auto w-20 h-20 bg-gradient-to-br from-orange-100 to-amber-100 rounded-full flex items-center justify-center mb-6">
              <svg className="w-10 h-10 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No Cases Found</h3>
            <p className="text-gray-600">Try adjusting your filters or search terms to find what you're looking for.</p>
          </div>
        </div>
      )}

      {filteredCases && filteredCases.length > 0 && (
        <>
          {/* Grid View */}
          {viewMode === 'grid' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredCases.map((caseData) => (
                <CaseCard key={caseData.id} case={caseData} />
              ))}
            </div>
          )}

          {/* Table View */}
          {viewMode === 'table' && (
            <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-100 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gradient-to-r from-orange-50 to-amber-50 border-b-2 border-orange-100">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Case Number
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Patient
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Exam Type
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Exam Date
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Location
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Confidence
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Attachments
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {filteredCases.map((caseData) => (
                      <tr
                        key={caseData.id}
                        className="hover:bg-gradient-to-r hover:from-orange-50 hover:to-amber-50 transition-all cursor-pointer border-b border-gray-50"
                        onClick={() => window.location.href = `/cases/${caseData.id}`}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Link
                            to={`/cases/${caseData.id}`}
                            className="text-sm font-medium text-orange-600 hover:text-orange-700"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {caseData.case_number}
                          </Link>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">{caseData.patient_name}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">{caseData.exam_type}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {caseData.exam_date ? (
                              <>
                                {formatDateOnly(caseData.exam_date)}
                                {caseData.exam_time && (
                                  <div className="text-xs text-gray-500">{caseData.exam_time}</div>
                                )}
                              </>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-900 max-w-xs truncate">
                            {caseData.exam_location || <span className="text-gray-400">—</span>}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <StatusBadge status={caseData.status} />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <ConfidenceBadge confidence={caseData.extraction_confidence} />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {caseData.attachments && caseData.attachments.length > 0 ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                                {caseData.attachments.length}
                              </span>
                            ) : (
                              <span className="text-gray-400">0</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
