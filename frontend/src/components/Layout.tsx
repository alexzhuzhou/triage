import { Link, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import logo from '../assets/logo-no-background.svg';

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
            <button className="w-full group flex items-center justify-center gap-3 px-5 py-4 text-base font-bold text-white bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 rounded-2xl transition-all duration-200 shadow-lg shadow-orange-500/30 hover:shadow-xl hover:shadow-orange-600/40 hover:-translate-y-0.5 active:translate-y-0">
              <svg className="w-6 h-6 group-hover:scale-110 group-hover:rotate-12 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>System Status</span>
            </button>
            <div className="text-center px-2 py-3 bg-white/80 rounded-xl border border-orange-100">
              <p className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                IME Case Management
              </p>
              <p className="text-xs text-gray-500 mt-1 font-medium">
                v1.0.0 • Online
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
