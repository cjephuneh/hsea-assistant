import { useState, useEffect } from 'react';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { ReportData } from './api';

export function Reports() {
  const { canMakeRequests } = useApiGuard();
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    api.reports.taskCompletion().then(({ data, status }) => {
      if (status === 200) setReport(data as ReportData);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [canMakeRequests]);

  if (loading) return <div className="page"><p className="muted">Loading…</p></div>;
  if (!report) return <div className="page"><p className="muted">No report data.</p></div>;

  const total = report.total_tasks ?? report.total ?? 0;
  const pct = total ? Math.round((report.completed / total) * 100) : (report.completion_rate ?? 0);
  const byStatus = report.by_status ?? (report.pending !== undefined
    ? { pending: report.pending, in_progress: report.in_progress ?? 0, completed: report.completed }
    : undefined);

  return (
    <div className="page reports-page">
      <header className="page-header">
        <h1>Reports</h1>
        <p className="page-subtitle">Task completion overview</p>
      </header>
      <div className="report-cards">
        <div className="report-card">
          <span className="report-value">{total}</span>
          <span className="report-label">Total tasks</span>
        </div>
        <div className="report-card">
          <span className="report-value">{report.completed}</span>
          <span className="report-label">Completed</span>
        </div>
        <div className="report-card highlight">
          <span className="report-value">{pct}%</span>
          <span className="report-label">Completion rate</span>
        </div>
      </div>
      {byStatus && Object.keys(byStatus).length > 0 && (
        <section className="report-by-status">
          <h2>By status</h2>
          <ul>
            {Object.entries(byStatus).map(([status, count]) => (
              <li key={status}>
                <span className="status-name">{status}</span>
                <span className="status-count">{count}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
