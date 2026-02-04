import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { Task, TaskAttachmentMeta, TaskCollaboratorMeta, TaskSubtaskMeta, User } from './api';

const statusConfig: Record<string, { label: string; color: string }> = {
  pending: { label: 'To do', color: 'var(--task-pending)' },
  in_progress: { label: 'In progress', color: 'var(--task-progress)' },
  completed: { label: 'Done', color: 'var(--task-done)' },
};

export function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const { canMakeRequests } = useApiGuard();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [notesDraft, setNotesDraft] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [addingSubtask, setAddingSubtask] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [addingCollaboratorId, setAddingCollaboratorId] = useState<number | ''>('');
  const [uploadingFile, setUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function loadTask() {
    if (!id || !canMakeRequests) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.tasks.get(Number(id)).then(({ data, status }) => {
      if (status === 200) setTask(data as Task);
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  useEffect(() => {
    loadTask();
  }, [id, canMakeRequests]);

  useEffect(() => {
    if (task?.notes !== undefined) setNotesDraft(task.notes ?? '');
  }, [task?.notes]);

  useEffect(() => {
    if (!canMakeRequests) return;
    api.tasks.users().then(({ data, status }) => {
      if (status === 200) setUsers(Array.isArray(data) ? data : []);
    });
  }, [canMakeRequests]);

  async function updateStatus(status: string) {
    if (!task) return;
    setUpdating(true);
    const { status: s } = await api.tasks.update(task.id, { status });
    setUpdating(false);
    if (s === 200) setTask((t) => t ? { ...t, status } : null);
  }

  async function saveNotes() {
    if (!task) return;
    setSavingNotes(true);
    const { status } = await api.tasks.update(task.id, { notes: notesDraft });
    setSavingNotes(false);
    if (status === 200) setTask((t) => t ? { ...t, notes: notesDraft } : null);
  }

  async function updateDueDate(dueDate: string | null) {
    if (!task) return;
    setUpdating(true);
    const { status } = await api.tasks.update(task.id, { due_date: dueDate || undefined });
    setUpdating(false);
    if (status === 200) setTask((t) => t ? { ...t, due_date: dueDate ?? undefined } : null);
  }

  async function addSubtask() {
    if (!task || !newSubtaskTitle.trim()) return;
    setAddingSubtask(true);
    const { status } = await api.tasks.create({
      title: newSubtaskTitle.trim(),
      assignee_id: task.assignee?.id ?? 0,
      parent_task_id: task.id,
    });
    setAddingSubtask(false);
    if (status === 201 || status === 200) {
      setNewSubtaskTitle('');
      loadTask();
    }
  }

  async function addCollaborator() {
    if (!task || addingCollaboratorId === '') return;
    const { status } = await api.tasks.collaborators.add(task.id, addingCollaboratorId);
    if (status === 201) {
      setAddingCollaboratorId('');
      loadTask();
    }
  }

  async function removeCollaborator(userId: number) {
    if (!task) return;
    const { status } = await api.tasks.collaborators.remove(task.id, userId);
    if (status === 200) loadTask();
  }

  async function attachFile(fileId: number) {
    if (!task) return;
    const { status } = await api.tasks.attachments.add(task.id, fileId);
    if (status === 201) loadTask();
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !task) return;
    setUploadingFile(true);
    const { data, status } = await api.files.upload(file);
    setUploadingFile(false);
    e.target.value = '';
    if (status === 201 && data?.id) {
      await attachFile(data.id);
    }
  }

  async function removeAttachment(attId: number) {
    if (!task) return;
    const { status } = await api.tasks.attachments.remove(task.id, attId);
    if (status === 200) loadTask();
  }

  function downloadAttachment(fileId: number, name: string) {
    const token = localStorage.getItem('access_token');
    const base = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://hsea-evcfc7bwh7fvaefr.canadacentral-01.azurewebsites.net');
    const url = base ? `${base.replace(/\/api\/?$/, '')}/api/files/${fileId}` : `/api/files/${fileId}`;
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = name;
        a.click();
        URL.revokeObjectURL(a.href);
      });
  }

  if (loading) {
    return (
      <div className="task-detail-page">
        <div className="task-detail-loading">
          <div className="task-detail-spinner" />
          <p>Loading task…</p>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="task-detail-page">
        <div className="task-detail-empty">
          <p className="task-detail-empty__title">Task not found</p>
          <p className="task-detail-empty__sub">It may have been removed or the link is invalid.</p>
          <button type="button" className="task-detail-back" onClick={() => navigate('/dashboard/tasks')}>
            ← Back to tasks
          </button>
        </div>
      </div>
    );
  }

  const subtasks = task.subtasks ?? [];
  const attachments = task.attachments ?? [];
  const collaborators = task.collaborators ?? [];
  const availableCollaborators = users.filter((u) => u.id !== task.assignee?.id && !collaborators.some((c) => c.id === u.id));
  const statusStyle = statusConfig[task.status] ?? statusConfig.pending;

  return (
    <div className="task-detail-page">
      <div className="task-detail-hero" style={{ ['--task-accent' as string]: statusStyle.color }}>
        <div className="task-detail-hero__strip" />
        <div className="task-detail-hero__inner">
          <button
            type="button"
            className="task-detail-back"
            onClick={() => navigate(-1)}
            aria-label="Back"
          >
            ← Back
          </button>
          <h1 className="task-detail-hero__title">{task.title}</h1>
          <div className="task-detail-hero__meta">
            <span className="task-detail-hero__status" style={{ color: statusStyle.color }}>
              {statusStyle.label}
            </span>
            {task.priority && (
              <span className="task-detail-hero__priority">{task.priority}</span>
            )}
            <span className="task-detail-hero__assignee">
              <span className="task-detail-hero__avatar">
                {task.assignee ? task.assignee.name.charAt(0).toUpperCase() : '?'}
              </span>
              {task.assignee ? task.assignee.name : 'Unassigned'}
            </span>
            {task.due_date && (
              <span className="task-detail-hero__due">
                Due {new Date(task.due_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            )}
            {task.created_by && (
              <span className="task-detail-hero__created">Created by {task.created_by.name}</span>
            )}
          </div>
        </div>
      </div>

      <div className="task-detail-status">
        <span className="task-detail-status__label">Status</span>
        <div className="task-detail-status__pills">
          {(['pending', 'in_progress', 'completed'] as const).map((s) => {
            const cfg = statusConfig[s];
            const isActive = task.status === s;
            return (
              <button
                key={s}
                type="button"
                className={`task-detail-pill ${isActive ? 'task-detail-pill--active' : ''}`}
                style={isActive ? { background: cfg.color, borderColor: cfg.color } : undefined}
                disabled={updating}
                onClick={() => updateStatus(s)}
              >
                {cfg.label}
              </button>
            );
          })}
        </div>
      </div>

      <section className="task-detail-card task-detail-card--main">
        <h2 className="task-detail-card__title">Description</h2>
        <p className="task-detail-card__desc">
          {task.description || <span className="task-detail-muted">No description yet.</span>}
        </p>
      </section>

      <div className="task-detail-grid">
        <div className="task-detail-col">
          <section className="task-detail-card">
            <h2 className="task-detail-card__title">Due date</h2>
            <div className="task-detail-due">
              <input
                type="date"
                className="task-detail-input"
                value={task.due_date ? new Date(task.due_date).toISOString().slice(0, 10) : ''}
                onChange={(e) => updateDueDate(e.target.value ? new Date(e.target.value).toISOString() : null)}
              />
              {!task.due_date && <span className="task-detail-muted">No due date set</span>}
            </div>
          </section>

          <section className="task-detail-card">
            <h2 className="task-detail-card__title">Notes</h2>
            <textarea
              className="task-detail-textarea"
              value={notesDraft}
              onChange={(e) => setNotesDraft(e.target.value)}
              onBlur={saveNotes}
              placeholder="Add notes, context, or follow-ups…"
              rows={4}
            />
            <button
              type="button"
              className="task-detail-btn task-detail-btn--primary"
              disabled={savingNotes}
              onClick={saveNotes}
            >
              {savingNotes ? 'Saving…' : 'Save notes'}
            </button>
          </section>
        </div>

        <div className="task-detail-col">
          <section className="task-detail-card">
            <h2 className="task-detail-card__title">Subtasks {subtasks.length > 0 && `(${subtasks.length})`}</h2>
            <ul className="task-detail-list">
              {subtasks.map((st: TaskSubtaskMeta) => (
                <li key={st.id} className="task-detail-list-item">
                  <span className="task-detail-list-item__text">{st.title}</span>
                  <span className="task-detail-list-item__badge" data-status={st.status}>
                    {st.status.replace('_', ' ')}
                  </span>
                  <Link to={`/dashboard/tasks/${st.id}`} className="task-detail-list-item__link">
                    Open →
                  </Link>
                </li>
              ))}
            </ul>
            <div className="task-detail-add">
              <input
                type="text"
                className="task-detail-input task-detail-input--full"
                value={newSubtaskTitle}
                onChange={(e) => setNewSubtaskTitle(e.target.value)}
                placeholder="New subtask title"
              />
              <button
                type="button"
                className="task-detail-btn task-detail-btn--primary"
                disabled={addingSubtask || !newSubtaskTitle.trim()}
                onClick={addSubtask}
              >
                {addingSubtask ? 'Adding…' : 'Add subtask'}
              </button>
            </div>
          </section>

          <section className="task-detail-card">
            <h2 className="task-detail-card__title">Attachments {attachments.length > 0 && `(${attachments.length})`}</h2>
            <ul className="task-detail-list">
              {attachments.map((att: TaskAttachmentMeta) => (
                <li key={att.id} className="task-detail-file">
                  <span className="task-detail-file__name">{att.original_filename}</span>
                  {att.file_size != null && (
                    <span className="task-detail-muted">{(att.file_size / 1024).toFixed(1)} KB</span>
                  )}
                  <div className="task-detail-file__actions">
                    <button type="button" className="task-detail-btn task-detail-btn--ghost" onClick={() => downloadAttachment(att.file_id, att.original_filename)}>
                      Download
                    </button>
                    <button type="button" className="task-detail-btn task-detail-btn--ghost" onClick={() => removeAttachment(att.id)}>
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf,application/pdf,image/*,.doc,.docx"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
            />
            <button
              type="button"
              className="task-detail-btn task-detail-btn--primary"
              disabled={uploadingFile}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploadingFile ? 'Uploading…' : '+ Attach file'}
            </button>
          </section>

          <section className="task-detail-card">
            <h2 className="task-detail-card__title">People</h2>
            <div className="task-detail-people">
              {task.assignee && (
                <div className="task-detail-person task-detail-person--assignee">
                  <span className="task-detail-person__avatar">{task.assignee.name.charAt(0).toUpperCase()}</span>
                  <div>
                    <span className="task-detail-person__name">{task.assignee.name}</span>
                    <span className="task-detail-person__role">Assignee</span>
                  </div>
                </div>
              )}
              {collaborators.map((c: TaskCollaboratorMeta) => (
                <div key={c.id} className="task-detail-person">
                  <span className="task-detail-person__avatar">{c.name.charAt(0).toUpperCase()}</span>
                  <div className="task-detail-person__info">
                    <span className="task-detail-person__name">{c.name}</span>
                    <span className="task-detail-muted">{c.email}</span>
                  </div>
                  <button type="button" className="task-detail-btn task-detail-btn--ghost task-detail-btn--sm" onClick={() => removeCollaborator(c.id)}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
            {availableCollaborators.length > 0 && (
              <div className="task-detail-add-person">
                <select
                  className="task-detail-select"
                  value={addingCollaboratorId === '' ? '' : String(addingCollaboratorId)}
                  onChange={(e) => setAddingCollaboratorId(e.target.value ? Number(e.target.value) : '')}
                >
                  <option value="">Add person…</option>
                  {availableCollaborators.map((u) => (
                    <option key={u.id} value={u.id}>{u.name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  className="task-detail-btn task-detail-btn--primary"
                  disabled={addingCollaboratorId === ''}
                  onClick={addCollaborator}
                >
                  Add
                </button>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
