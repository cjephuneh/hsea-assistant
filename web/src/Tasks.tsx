import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { Task } from './api';

const statusConfig: Record<string, { label: string; color: string; dot: string }> = {
  pending: { label: 'To do', color: 'var(--task-pending)', dot: '●' },
  in_progress: { label: 'In progress', color: 'var(--task-progress)', dot: '◐' },
  completed: { label: 'Done', color: 'var(--task-done)', dot: '✓' },
};

function TaskCard({ task }: { task: Task }) {
  const config = statusConfig[task.status] ?? statusConfig.pending;
  const assigneeInitial = task.assignee?.name?.charAt(0)?.toUpperCase() ?? '?';
  const assigneeName = task.assignee?.name ?? 'Unassigned';
  const dueLabel = task.due_date
    ? new Date(task.due_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: task.due_date.includes('-') ? undefined : 'numeric' })
    : null;

  return (
    <Link
      to={`/dashboard/tasks/${task.id}`}
      className="tasks-card"
      style={{ ['--task-accent' as string]: config.color }}
    >
      <div className="tasks-card__strip" />
      <div className="tasks-card__body">
        <div className="tasks-card__top">
          <h3 className="tasks-card__title">{task.title}</h3>
          <span className="tasks-card__status" style={{ color: config.color }}>
            {config.dot} {config.label}
          </span>
        </div>
        {task.description && (
          <p className="tasks-card__desc">{task.description}</p>
        )}
        <div className="tasks-card__meta">
          <span className="tasks-card__assignee" title={assigneeName}>
            <span className="tasks-card__avatar">{assigneeInitial}</span>
            {assigneeName}
          </span>
          {dueLabel && (
            <span className="tasks-card__due">
              <span className="tasks-card__due-icon">▢</span> {dueLabel}
            </span>
          )}
        </div>
      </div>
      <span className="tasks-card__arrow">→</span>
    </Link>
  );
}

export function Tasks() {
  const { canMakeRequests } = useApiGuard();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'completed'>('all');

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

  const filtered = tasks.filter((t) => filter === 'all' || t.status === filter);
  const counts = {
    all: tasks.length,
    pending: tasks.filter((t) => t.status === 'pending').length,
    in_progress: tasks.filter((t) => t.status === 'in_progress').length,
    completed: tasks.filter((t) => t.status === 'completed').length,
  };

  const filters: { key: typeof filter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'pending', label: 'To do' },
    { key: 'in_progress', label: 'In progress' },
    { key: 'completed', label: 'Done' },
  ];

  return (
    <div className="page tasks-page">
      <div className="tasks-hero">
        <div className="tasks-hero__content">
          <h1 className="tasks-hero__title">Tasks</h1>
          <p className="tasks-hero__subtitle">Track and ship work in one place</p>
        </div>
        <Link to="/dashboard/tasks/new" className="tasks-hero__cta">
          <span className="tasks-hero__cta-icon">+</span>
          New task
        </Link>
      </div>

      <div className="tasks-filters">
        {filters.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={`tasks-filter ${filter === key ? 'tasks-filter--active' : ''}`}
            onClick={() => setFilter(key)}
          >
            <span className="tasks-filter__label">{label}</span>
            <span className="tasks-filter__count">{counts[key]}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="tasks-empty">
          <div className="tasks-empty__spinner" />
          <p className="tasks-empty__title">Loading tasks…</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="tasks-empty">
          <div className="tasks-empty__visual" aria-hidden>
            <span className="tasks-empty__circle" />
            <span className="tasks-empty__check" />
          </div>
          <p className="tasks-empty__title">
            {filter === 'all' ? 'No tasks yet' : `No ${filters.find((f) => f.key === filter)?.label.toLowerCase()} tasks`}
          </p>
          <p className="tasks-empty__sub">
            {filter === 'all'
              ? 'Create your first task or use the voice assistant to add one.'
              : 'Try another filter or create a new task.'}
          </p>
          <Link to="/dashboard/tasks/new" className="tasks-empty__btn">
            New task
          </Link>
        </div>
      ) : (
        <div className="tasks-grid">
          {filtered.map((t) => (
            <TaskCard key={t.id} task={t} />
          ))}
        </div>
      )}
    </div>
  );
}
