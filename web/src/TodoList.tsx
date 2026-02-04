import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { Task } from './api';

type TodoFilter = 'all' | 'today' | 'week' | 'incomplete';

function isToday(dateStr: string | undefined): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  const today = new Date();
  return d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth() && d.getDate() === today.getDate();
}

function isThisWeek(dateStr: string | undefined): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  const now = new Date();
  const start = new Date(now);
  start.setDate(now.getDate() - now.getDay());
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(start.getDate() + 7);
  return d >= start && d < end;
}

export function TodoList() {
  const { canMakeRequests } = useApiGuard();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<TodoFilter>('incomplete');
  const [togglingId, setTogglingId] = useState<number | null>(null);

  function load() {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.tasks.list().then(({ data, status }) => {
      if (status === 200) setTasks(Array.isArray(data) ? data : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  useEffect(() => load(), [canMakeRequests]);

  const filtered = tasks.filter((t) => {
    if (filter === 'incomplete') return t.status !== 'completed';
    if (filter === 'today') return isToday(t.due_date);
    if (filter === 'week') return isThisWeek(t.due_date);
    return true; // all
  });

  const sorted = [...filtered].sort((a, b) => {
    const aDone = a.status === 'completed' ? 1 : 0;
    const bDone = b.status === 'completed' ? 1 : 0;
    if (aDone !== bDone) return aDone - bDone;
    const aDate = a.due_date ? new Date(a.due_date).getTime() : 0;
    const bDate = b.due_date ? new Date(b.due_date).getTime() : 0;
    return aDate - bDate;
  });

  async function toggleComplete(t: Task) {
    const next = t.status === 'completed' ? 'pending' : 'completed';
    setTogglingId(t.id);
    const { status } = await api.tasks.update(t.id, { status: next });
    setTogglingId(null);
    if (status === 200) setTasks((prev) => prev.map((x) => (x.id === t.id ? { ...x, status: next } : x)));
  }

  return (
    <div className="page todo-page">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h1>Todo list</h1>
          <p className="page-subtitle">Your checklist — tap to mark done</p>
        </div>
        <Link to="/dashboard/tasks/new" className="btn btn-primary">Add item</Link>
      </header>
      <div className="todo-filters">
        {(['incomplete', 'today', 'week', 'all'] as const).map((f) => (
          <button
            key={f}
            type="button"
            className={`filter-tab ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'incomplete' ? 'To do' : f === 'today' ? 'Today' : f === 'week' ? 'This week' : 'All'}
          </button>
        ))}
      </div>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : sorted.length === 0 ? (
        <p className="muted">No items. Add a task or use voice to create one.</p>
      ) : (
        <ul className="todo-list">
          {sorted.map((t) => (
            <li key={t.id} className={`todo-item ${t.status === 'completed' ? 'done' : ''}`}>
              <label className="todo-label">
                <input
                  type="checkbox"
                  checked={t.status === 'completed'}
                  disabled={togglingId === t.id}
                  onChange={() => toggleComplete(t)}
                  className="todo-checkbox"
                />
                <span className="todo-title">{t.title}</span>
              </label>
              <div className="todo-meta">
                {t.due_date && (
                  <span className="todo-due">{new Date(t.due_date).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                )}
                {t.assignee && t.assignee.name && <span className="todo-assignee">{t.assignee.name}</span>}
                <Link to={`/dashboard/tasks/${t.id}`} className="todo-link">Open</Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
