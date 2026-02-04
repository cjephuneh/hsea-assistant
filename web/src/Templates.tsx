import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { Template, WorkspaceDetail, User } from './api';

export function Templates() {
  const { user } = useAuth();
  const { canMakeRequests } = useApiGuard();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [members, setMembers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState<number | null>(null);
  const [assigneeId, setAssigneeId] = useState<number | ''>('');
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creatingTemplate, setCreatingTemplate] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    title_template: '',
    description_template: '',
    default_priority: 'MEDIUM',
    default_category: '',
    estimated_hours: '',
  });

  useEffect(() => {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    api.templates.list().then(({ data, status }) => {
      if (status === 200) setTemplates(Array.isArray(data) ? data : []);
      setLoading(false);
    }).catch(() => setLoading(false));
    api.workspaces.list().then(({ data: workspaces, status }) => {
      if (status !== 200 || !Array.isArray(workspaces) || workspaces.length === 0) {
        if (user) setMembers([{ id: user.id, name: user.name, email: user.email }]);
        return;
      }
      api.workspaces.get((workspaces as { id: number }[])[0].id).then(({ data: ws, status: s }) => {
        if (s === 200 && ws && 'members' in ws)
          setMembers((ws as WorkspaceDetail).members.map((x) => ({ id: x.id, name: x.name, email: x.email })));
        else if (user) setMembers([{ id: user.id, name: user.name, email: user.email }]);
      }).catch(() => {
        if (user) setMembers([{ id: user.id, name: user.name, email: user.email }]);
      });
    }).catch(() => {
      if (user) setMembers([{ id: user.id, name: user.name, email: user.email }]);
    });
  }, [user, canMakeRequests]);

  async function createFromTemplate(templateId: number) {
    const aid = assigneeId === '' ? members[0]?.id : assigneeId;
    if (aid == null) {
      setError('Select an assignee first');
      return;
    }
    setCreating(templateId);
    setError('');
    const { status } = await api.templates.createTask(templateId, aid);
    setCreating(null);
    if (status === 200 || status === 201) {
      navigate('/dashboard/tasks');
      return;
    }
    setError('Failed to create task from template');
  }

  async function handleCreateTemplate(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.name.trim() || !formData.title_template.trim()) {
      setError('Name and title template are required');
      return;
    }
    setCreatingTemplate(true);
    setError('');
    try {
      const { status, data } = await api.templates.create({
        name: formData.name.trim(),
        title_template: formData.title_template.trim(),
        description_template: formData.description_template.trim() || undefined,
        default_priority: formData.default_priority,
        default_category: formData.default_category.trim() || undefined,
        estimated_hours: formData.estimated_hours ? parseFloat(formData.estimated_hours) : undefined,
      });
      if (status === 201 && data) {
        setTemplates([...templates, data]);
        setShowCreateForm(false);
        setFormData({
          name: '',
          title_template: '',
          description_template: '',
          default_priority: 'MEDIUM',
          default_category: '',
          estimated_hours: '',
        });
      } else {
        setError('Failed to create template');
      }
    } catch (err) {
      setError('Failed to create template');
    } finally {
      setCreatingTemplate(false);
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
          <div>
            <h1>Task templates</h1>
            <p className="page-subtitle">Create tasks quickly from templates</p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              console.log('Toggle form, current state:', showCreateForm);
              setShowCreateForm(!showCreateForm);
            }}
          >
            {showCreateForm ? 'Cancel' : '+ New Template'}
          </button>
        </div>
      </header>
      {members.length > 0 && (
        <div className="form-inline" style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            Assign to:
            <select
              value={assigneeId === '' ? '' : String(assigneeId)}
              onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : '')}
            >
              {members.map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </label>
        </div>
      )}
      {showCreateForm && (
        <div style={{ 
          marginBottom: '1.5rem', 
          padding: '1.5rem', 
          background: 'var(--bg-card)', 
          border: '1.5px solid var(--border)', 
          borderRadius: 'var(--radius)',
          display: 'block',
          visibility: 'visible'
        }}>
          <h2 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.25rem', fontWeight: 600 }}>Create New Template</h2>
          <form onSubmit={handleCreateTemplate}>
            <div className="form-group">
              <label htmlFor="template-name">Template Name *</label>
              <input
                id="template-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Weekly Review"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1.5px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
            </div>
            <div className="form-group">
              <label htmlFor="template-title">Task Title Template *</label>
              <input
                id="template-title"
                type="text"
                value={formData.title_template}
                onChange={(e) => setFormData({ ...formData, title_template: e.target.value })}
                placeholder="e.g., Weekly review for {assignee}"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1.5px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
            </div>
            <div className="form-group">
              <label htmlFor="template-description">Task Description Template</label>
              <textarea
                id="template-description"
                value={formData.description_template}
                onChange={(e) => setFormData({ ...formData, description_template: e.target.value })}
                placeholder="Optional description for tasks created from this template"
                rows={3}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1.5px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                  fontFamily: 'inherit',
                  resize: 'vertical',
                }}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label htmlFor="template-priority">Default Priority</label>
                <select
                  id="template-priority"
                  value={formData.default_priority}
                  onChange={(e) => setFormData({ ...formData, default_priority: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1.5px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg)',
                    color: 'var(--text)',
                  }}
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="template-category">Category</label>
                <input
                  id="template-category"
                  type="text"
                  value={formData.default_category}
                  onChange={(e) => setFormData({ ...formData, default_category: e.target.value })}
                  placeholder="e.g., Review, Meeting"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1.5px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg)',
                    color: 'var(--text)',
                  }}
                />
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="template-hours">Estimated Hours</label>
              <input
                id="template-hours"
                type="number"
                step="0.5"
                min="0"
                value={formData.estimated_hours}
                onChange={(e) => setFormData({ ...formData, estimated_hours: e.target.value })}
                placeholder="e.g., 2.5"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1.5px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg)',
                  color: 'var(--text)',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={creatingTemplate}
              >
                {creatingTemplate ? 'Creating…' : 'Create Template'}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setShowCreateForm(false);
                  setFormData({
                    name: '',
                    title_template: '',
                    description_template: '',
                    default_priority: 'MEDIUM',
                    default_category: '',
                    estimated_hours: '',
                  });
                }}
                disabled={creatingTemplate}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <p className="muted">Loading…</p>
      ) : templates.length === 0 && !showCreateForm ? (
        <p className="muted">No templates yet. Click "New Template" to create one.</p>
      ) : templates.length > 0 ? (
        <ul className="list-card">
          {templates.map((t) => (
            <li key={t.id} className="list-card-item">
              <div>
                <strong>{t.name}</strong>
                <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.9rem' }}>{t.title_template}</p>
              </div>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={creating !== null}
                onClick={() => createFromTemplate(t.id)}
              >
                {creating === t.id ? 'Creating…' : 'Use template'}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
