import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { WorkspaceDetail, User } from './api';

export function CreateTask() {
  const { user } = useAuth();
  const { canMakeRequests } = useApiGuard();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { parent_task_id?: number } | null;
  const parentTaskId = state?.parent_task_id;
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [assigneeId, setAssigneeId] = useState<number | ''>('');
  const [dueDate, setDueDate] = useState('');
  const [collaboratorIds, setCollaboratorIds] = useState<number[]>([]);
  const [members, setMembers] = useState<User[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!canMakeRequests) return;
    api.tasks.users().then(({ data: usersList, status }) => {
      if (status === 200 && Array.isArray(usersList)) setAllUsers(usersList);
    });
    api.workspaces.list().then(({ data: workspaces, status }) => {
      if (status !== 200 || !Array.isArray(workspaces) || workspaces.length === 0) {
        if (user) setMembers([{ id: user.id, name: user.name, email: user.email }]);
        setAssigneeId(user?.id ?? '');
        return;
      }
      api.workspaces.get((workspaces as { id: number }[])[0].id).then(({ data: ws, status: s }) => {
        if (s === 200 && ws && 'members' in ws) {
          const m = (ws as WorkspaceDetail).members.map((x) => ({ id: x.id, name: x.name, email: x.email }));
          setMembers(m);
          if (m.length && !assigneeId) setAssigneeId(m[0].id);
        } else if (user) {
          setMembers([{ id: user.id, name: user.name, email: user.email }]);
          setAssigneeId(user.id);
        }
      }).catch(() => {
        if (user) {
          setMembers([{ id: user.id, name: user.name, email: user.email }]);
          setAssigneeId(user.id);
        }
      });
    }).catch(() => {
      if (user) {
        setMembers([{ id: user.id, name: user.name, email: user.email }]);
        setAssigneeId(user.id);
      }
    });
  }, [user, canMakeRequests]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    const aid = assigneeId === '' ? user?.id : assigneeId;
    if (aid == null) {
      setError('Please select an assignee');
      return;
    }
    setLoading(true);
    const { data, status } = await api.tasks.create({
      title: title.trim(),
      description: description.trim() || undefined,
      assignee_id: aid,
      parent_task_id: parentTaskId,
      due_date: dueDate || undefined,
      collaborator_ids: collaboratorIds.length ? collaboratorIds : undefined,
    });
    setLoading(false);
    if (status === 200 || status === 201) {
      if (parentTaskId) navigate(`/dashboard/tasks/${parentTaskId}`, { replace: true });
      else navigate('/dashboard/tasks', { replace: true });
      return;
    }
    setError((data as { error?: string })?.error || 'Failed to create task');
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>{parentTaskId ? 'New subtask' : 'New task'}</h1>
        <p className="page-subtitle">{parentTaskId ? 'Add a subtask' : 'Create a task and assign it'}</p>
      </header>
      <form onSubmit={handleSubmit} className="form-card">
        <label>
          Title *
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Task title"
            required
          />
        </label>
        <label>
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            rows={3}
          />
        </label>
        <label>
          Assign to
          <select
            value={assigneeId === '' ? '' : String(assigneeId)}
            onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : '')}
          >
            {members.map((m) => (
              <option key={m.id} value={m.id}>{m.name} ({m.email})</option>
            ))}
          </select>
        </label>
        <label>
          Due date
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </label>
        {allUsers.length > 0 && (
          <label>
            Also add people (collaborators)
            <select
              multiple
              value={collaboratorIds.map(String)}
              onChange={(e) => {
                const opts = Array.from(e.target.selectedOptions, (o) => Number(o.value));
                setCollaboratorIds(opts);
              }}
              style={{ minHeight: 80 }}
            >
              {allUsers.filter((m) => m.id !== assigneeId).map((m) => (
                <option key={m.id} value={m.id}>{m.name} ({m.email})</option>
              ))}
            </select>
            <small className="muted">Hold Ctrl/Cmd to select multiple</small>
          </label>
        )}
        {error && <p className="form-error">{error}</p>}
        <div className="form-actions">
          <button type="button" className="btn" onClick={() => navigate(-1)}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Creating…' : 'Create task'}
          </button>
        </div>
      </form>
    </div>
  );
}
