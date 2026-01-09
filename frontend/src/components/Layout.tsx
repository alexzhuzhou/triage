import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import logo from '../assets/logo-no-background.svg';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

interface LayoutProps {
  children: React.ReactNode;
}

const navigation = [
  {
    name: 'Dashboard',
    href: '/',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    )
  },
  {
    name: 'Queue Management',
    href: '/queue',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    )
  },
];

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const [isPolling, setIsPolling] = useState(false);

  const handleManualPoll = async () => {
    setIsPolling(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/email-polling/manual-poll`);
      const data = response.data;

      toast.success(
        `Poll completed! Fetched ${data.emails_fetched} emails, ${data.emails_processed} processed successfully`,
        { duration: 5000 }
      );
    } catch (error: any) {
      console.error('Manual poll error:', error);
      toast.error(
        error?.response?.data?.detail || 'Failed to poll emails. Check if email integration is enabled.',
        { duration: 6000 }
      );
    } finally {
      setIsPolling(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-72 bg-white shadow-2xl border-r border-gray-100">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-center h-28 px-6 border-b border-gray-100 bg-gradient-to-br from-orange-50/50 to-amber-50/30">
            <img
              src={logo}
              alt="Triage Logo"
              className="h-20 w-auto drop-shadow-sm"
            />
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-5 py-8 space-y-2">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={clsx(
                    'group flex items-center gap-4 px-5 py-4 text-base font-semibold rounded-2xl transition-all duration-200 relative',
                    isActive
                      ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/30'
                      : 'text-gray-700 hover:bg-gradient-to-r hover:from-orange-50 hover:to-amber-50 hover:text-orange-700'
                  )}
                >
                  {/* Icon */}
                  <div className={clsx(
                    'flex-shrink-0 transition-all duration-200',
                    isActive ? 'text-white scale-110' : 'text-orange-500 group-hover:scale-110'
                  )}>
                    {item.icon}
                  </div>

                  {/* Text */}
                  <span className="flex-1">{item.name}</span>

                  {/* Arrow indicator for active */}
                  {isActive && (
                    <svg className="w-5 h-5 text-white animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                    </svg>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="p-5 space-y-4 border-t border-gray-100 bg-gradient-to-br from-orange-50/30 to-amber-50/20">
            {/* Manual Poll Button */}
            <button
              onClick={handleManualPoll}
              disabled={isPolling}
              className={clsx(
                'w-full px-4 py-3 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2',
                isPolling
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700 hover:shadow-lg hover:shadow-orange-500/30'
              )}
            >
              {isPolling ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Polling...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76" />
                  </svg>
                  Poll Emails
                </>
              )}
            </button>

            <div className="text-center px-2 py-3 bg-white/80 rounded-xl border border-orange-100">
              <p className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Case Management
              </p>
              <p className="text-xs text-gray-500 mt-1 font-medium">
                Online
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-72 bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50 min-h-screen">
        <main className="py-10 px-12 max-w-[1600px]">{children}</main>
      </div>
    </div>
  );
}
