import { useState, useMemo } from 'react';
import { useCases } from '../hooks/useCases';
import { CaseCard } from '../components/CaseCard';
import { LoadingSpinner } from '../components/LoadingSpinner';
import type { CaseFilters } from '../types';

export function Dashboard() {
  const [filters, setFilters] = useState<CaseFilters>({});
  const [searchTerm, setSearchTerm] = useState('');

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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Cases Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Manage and monitor IME cases
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Total Cases</div>
          <div className="mt-2 text-3xl font-bold text-gray-900">{stats.total}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Pending</div>
          <div className="mt-2 text-3xl font-bold text-gray-600">{stats.pending}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Confirmed</div>
          <div className="mt-2 text-3xl font-bold text-blue-600">{stats.confirmed}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Completed</div>
          <div className="mt-2 text-3xl font-bold text-green-600">{stats.completed}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search
            </label>
            <input
              type="text"
              placeholder="Case number, patient name, or exam type..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filters.status || ''}
              onChange={(e) =>
                setFilters({ ...filters, status: e.target.value || undefined })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="confirmed">Confirmed</option>
              <option value="completed">Completed</option>
            </select>
          </div>

          {/* Confidence Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All</option>
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
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          Error loading cases. Please try again.
        </div>
      )}

      {filteredCases && filteredCases.length === 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-600">No cases found matching your filters.</p>
        </div>
      )}

      {filteredCases && filteredCases.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCases.map((caseData) => (
            <CaseCard key={caseData.id} case={caseData} />
          ))}
        </div>
      )}
    </div>
  );
}
