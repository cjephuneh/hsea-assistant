import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useApiGuard } from './hooks/useApiGuard';
import { useAuth } from './AuthContext';
import { api } from './api';
import type { Task } from './api';

export function Dashboard() {
  const { user } = useAuth();
  const { canMakeRequests } = useApiGuard();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    api.tasks.list().then(({ data, status }) => {
      if (status === 200) {
        setTasks(Array.isArray(data) ? data : []);
      } else {
        setTasks([]);
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [canMakeRequests]);

  const pending = tasks.filter((t) => t.status !== 'completed').slice(0, 5);
  const firstName = user?.name?.split(/\s+/)[0] || 'there';

  return (
    <div className="page dashboard-page">
      <header className="page-header dashboard-hero">
        <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 700, letterSpacing: '-0.03em' }}>
          Hey, {firstName}
        </h1>
        <p className="page-subtitle" style={{ margin: '0.25rem 0 0', fontSize: '0.95rem' }}>
          Here’s what’s on your plate
        </p>
      </header>

      <section className="quick-actions">
        <Link to="/dashboard/todo" className="quick-action-card">
          <span className="qa-icon">◇</span>
          <span>Todo list</span>
        </Link>
        <Link to="/dashboard/tasks/new" className="quick-action-card">
          <span className="qa-icon">+</span>
          <span>New task</span>
        </Link>
        <Link to="/dashboard/voice" className="quick-action-card highlight">
          <span className="qa-icon">◉</span>
          <span>Voice assistant</span>
        </Link>
        <Link to="/dashboard/meetings" className="quick-action-card">
          <span className="qa-icon">▣</span>
          <span>Meetings</span>
        </Link>
      </section>

      <section className="recent-tasks">
        <h2 className="section-title">Recent tasks</h2>
        {loading ? (
          <div className="empty-state" style={{ padding: '2rem' }}>
            <div className="loading" style={{ margin: '0 auto 0.75rem' }} />
            <p style={{ margin: 0 }}>Loading tasks…</p>
          </div>
        ) : pending.length === 0 ? (
          <div className="empty-state">
            <p>No tasks yet</p>
            <p>Create one or use the voice assistant to get started</p>
            <Link to="/dashboard/tasks/new" className="btn btn-primary" style={{ marginTop: '1rem', width: 'auto' }}>
              New task
            </Link>
          </div>
        ) : (
          <ul className="task-list-mini">
            {pending.map((t) => (
              <li key={t.id}>
                <Link to={`/dashboard/tasks/${t.id}`}>
                  <span className="task-title">{t.title}</span>
                  <span className={`task-badge ${t.status}`}>{t.status.replace('_', ' ')}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        {pending.length > 0 && (
          <Link to="/dashboard/tasks" className="btn btn-sm" style={{ marginTop: '1rem' }}>
            View all tasks
          </Link>
        )}
      </section>
    </div>
  );
}
