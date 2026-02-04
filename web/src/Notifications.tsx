import { useState, useEffect } from 'react';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { Notification } from './api';

export function Notifications() {
  const { canMakeRequests } = useApiGuard();
  const [list, setList] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  function load() {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.notifications.list().then(({ data, status }) => {
      if (status === 200) setList(Array.isArray(data) ? data : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  useEffect(() => load(), [canMakeRequests]);

  async function markRead(id: number) {
    await api.notifications.markRead(id);
    setList((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }

  async function markAllRead() {
    await api.notifications.markAllRead();
    setList((prev) => prev.map((n) => ({ ...n, read: true })));
  }

  const unreadCount = list.filter((n) => !n.read).length;

  return (
    <div className="page">
      <header className="page-header" style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h1>Notifications</h1>
          <p className="page-subtitle">{unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}</p>
        </div>
        {unreadCount > 0 && (
          <button type="button" className="btn btn-sm" onClick={markAllRead}>Mark all read</button>
        )}
      </header>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : list.length === 0 ? (
        <p className="muted">No notifications.</p>
      ) : (
        <ul className="list-card">
          {list.map((n) => (
            <li key={n.id} className={`list-card-item ${n.read ? '' : 'unread'}`}>
              <div>
                <strong>{n.title}</strong>
                <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.9rem' }}>{n.message}</p>
                <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.8rem' }}>{new Date(n.created_at).toLocaleString()}</p>
              </div>
              {!n.read && (
                <button type="button" className="btn btn-sm" onClick={() => markRead(n.id)}>Mark read</button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
