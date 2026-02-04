import { useState, useEffect } from 'react';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { Workspace } from './api';

export function Workspaces() {
  const { canMakeRequests } = useApiGuard();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [message, setMessage] = useState('');

  function load() {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.workspaces.list().then(({ data, status }) => {
      if (status === 200) setWorkspaces(Array.isArray(data) ? data : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  useEffect(() => load(), [canMakeRequests]);

  async function createWorkspace(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setMessage('');
    const { status } = await api.workspaces.create(newName.trim());
    setCreating(false);
    if (status === 201) {
      setNewName('');
      load();
      setMessage('Workspace created.');
    } else setMessage('Failed to create workspace.');
  }

  async function switchTo(workspaceId: number) {
    const { status } = await api.workspaces.switch(workspaceId);
    if (status === 200) setMessage('Switched workspace.');
    else setMessage('Failed to switch.');
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Workspaces</h1>
        <p className="page-subtitle">Teams and workspaces</p>
      </header>
      {message && <p className="muted" style={{ marginBottom: '1rem' }}>{message}</p>}
      <form onSubmit={createWorkspace} className="form-inline" style={{ marginBottom: '1.5rem' }}>
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New workspace name"
        />
        <button type="submit" className="btn btn-primary" disabled={creating}>
          {creating ? 'Creating…' : 'Create'}
        </button>
      </form>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : workspaces.length === 0 ? (
        <p className="muted">No workspaces yet. Create one above.</p>
      ) : (
        <ul className="list-card">
          {workspaces.map((ws) => (
            <li key={ws.id} className="list-card-item">
              <div>
                <strong>{ws.name}</strong>
                {ws.description && <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.9rem' }}>{ws.description}</p>}
              </div>
              <button type="button" className="btn btn-sm" onClick={() => switchTo(ws.id)}>Switch</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
