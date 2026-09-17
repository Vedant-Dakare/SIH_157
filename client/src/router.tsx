import * as React from 'react';
import { Link, Navigate, createBrowserRouter } from 'react-router-dom';

import { AppShell } from '@/components/layout/AppShell';
import { LoadingState } from '@/components/common/LoadingState';

const PortfolioPage = React.lazy(() => import('@/pages/PortfolioPage'));
const EntityListPage = React.lazy(() => import('@/pages/EntityListPage'));
const EntityDetailPage = React.lazy(() => import('@/pages/EntityDetailPage'));
const FindingDetailPage = React.lazy(() => import('@/pages/FindingDetailPage'));
const QueuePage = React.lazy(() => import('@/pages/QueuePage'));
const AuditPage = React.lazy(() => import('@/pages/AuditPage'));
const RunsPage = React.lazy(() => import('@/pages/RunsPage'));
const ValidationPage = React.lazy(() => import('@/pages/ValidationPage'));
const SettingsPage = React.lazy(() => import('@/pages/SettingsPage'));

function Suspended({ children }: { children: React.ReactNode }) {
  return <React.Suspense fallback={<LoadingState rows={4} message="Loading page…" />}>{children}</React.Suspense>;
}

function NotFound() {
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center">
      <h2 className="text-lg font-semibold text-slate-50">Page not found</h2>
      <p className="text-sm text-slate-400">The requested view does not exist.</p>
      <Link to="/portfolio" className="text-sm text-slate-50 underline underline-offset-4">
        Back to portfolio
      </Link>
    </div>
  );
}

/** All routes from Section E, lazy-loaded behind Suspense. */
export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/portfolio" replace /> },
  {
    element: <AppShell />,
    children: [
      { path: '/portfolio', element: <Suspended><PortfolioPage /></Suspended> },
      { path: '/portfolio/:runId', element: <Suspended><PortfolioPage /></Suspended> },
      { path: '/entities', element: <Suspended><EntityListPage /></Suspended> },
      { path: '/entities/:entityId', element: <Suspended><EntityDetailPage /></Suspended> },
      {
        path: '/entities/:entityId/findings',
        element: <Suspended><EntityDetailPage /></Suspended>,
      },
      { path: '/findings/:findingId', element: <Suspended><FindingDetailPage /></Suspended> },
      { path: '/queue', element: <Suspended><QueuePage /></Suspended> },
      { path: '/audit', element: <Suspended><AuditPage /></Suspended> },
      { path: '/audit/:runId', element: <Suspended><AuditPage /></Suspended> },
      { path: '/runs', element: <Suspended><RunsPage /></Suspended> },
      { path: '/validation', element: <Suspended><ValidationPage /></Suspended> },
      { path: '/settings', element: <Suspended><SettingsPage /></Suspended> },
      { path: '*', element: <NotFound /> },
    ],
  },
]);
