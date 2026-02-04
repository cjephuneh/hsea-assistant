import { useState, useEffect } from 'react';
import { useApiGuard } from './hooks/useApiGuard';
import { api, type User, type StoredFileMeta } from './api';

export function SendEmail() {
  const { canMakeRequests } = useApiGuard();
  const [users, setUsers] = useState<User[]>([]);
  const [files, setFiles] = useState<StoredFileMeta[]>([]);
  const [toUserId, setToUserId] = useState<number | ''>('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [attachIds, setAttachIds] = useState<number[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!canMakeRequests) return;
    api.tasks.users().then(({ data, status }) => {
      if (status === 200) setUsers(Array.isArray(data) ? data : []);
    });
    api.files.list().then(({ data, status }) => {
      if (status === 200) setFiles(Array.isArray(data) ? data : []);
    });
  }, [canMakeRequests]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const toId = toUserId === '' ? users[0]?.id : toUserId;
    if (toId == null) {
      setError('Select a recipient');
      return;
    }
    if (!subject.trim()) {
      setError('Subject is required');
      return;
    }
    setSending(true);
    setError('');
    setSuccess('');
    const { data, status } = await api.mail.send({
      to_user_id: toId,
      subject: subject.trim(),
      body: body.trim() || '',
      file_ids: attachIds.length ? attachIds : undefined,
    });
    setSending(false);
    if (status === 200) {
      setSuccess((data as { message: string }).message);
      setSubject('');
      setBody('');
      setAttachIds([]);
    } else setError((data as { error?: string })?.error || 'Failed to send email');
  }

  function toggleAttachment(id: number) {
    setAttachIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Send email</h1>
        <p className="page-subtitle">e.g. Tell Scott to check the report</p>
      </header>
      {error && <p className="form-error">{error}</p>}
      {success && <p className="muted" style={{ color: 'var(--accent)', marginBottom: '1rem' }}>{success}</p>}
      <form onSubmit={handleSubmit} className="form-card">
        <label>
          To
          <select
            value={toUserId === '' ? '' : String(toUserId)}
            onChange={(e) => setToUserId(e.target.value ? Number(e.target.value) : '')}
          >
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
            ))}
          </select>
        </label>
        <label>
          Subject *
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Please check the report"
            required
          />
        </label>
        <label>
          Message
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="e.g. Hi Scott, please review the attached report and let me know your feedback."
            rows={4}
          />
        </label>
        {files.length > 0 && (
          <label>
            Attach from file store
            <div className="attach-list">
              {files.map((f) => (
                <label key={f.id} className="attach-item">
                  <input
                    type="checkbox"
                    checked={attachIds.includes(f.id)}
                    onChange={() => toggleAttachment(f.id)}
                  />
                  <span>{f.original_filename}</span>
                </label>
              ))}
            </div>
          </label>
        )}
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={sending}>
            {sending ? 'Sending…' : 'Send email'}
          </button>
        </div>
      </form>
      <p className="muted" style={{ marginTop: '1rem', fontSize: '0.85rem' }}>
        Configure MAIL_USERNAME and MAIL_PASSWORD in backend .env (e.g. Gmail App Password) for emails to send.
      </p>
    </div>
  );
}
