import { useState, useEffect, useRef } from 'react';
import { useApiGuard } from './hooks/useApiGuard';
import { api, type StoredFileMeta, type User } from './api';

export function FileStore() {
  const { canMakeRequests } = useApiGuard();
  const [files, setFiles] = useState<StoredFileMeta[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [sendingId, setSendingId] = useState<number | null>(null);
  const [sendToUserId, setSendToUserId] = useState<number | ''>('');
  const [sendMessage, setSendMessage] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  function load() {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.files.list().then(({ data, status }) => {
      if (status === 200) setFiles(Array.isArray(data) ? data : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  useEffect(() => {
    if (!canMakeRequests) return;
    load();
    api.tasks.users().then(({ data, status }) => {
      if (status === 200) setUsers(Array.isArray(data) ? data : []);
    });
  }, [canMakeRequests]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    const { data, status } = await api.files.upload(file);
    setUploading(false);
    e.target.value = '';
    if (status === 201) {
      setFiles((prev) => [data, ...prev]);
      setSuccess(`Uploaded ${file.name}`);
    } else setError((data as { error?: string })?.error || 'Upload failed');
  }

  function downloadFile(id: number, name: string) {
    const token = localStorage.getItem('access_token');
    const base = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'http://localhost:5001');
    const url = base ? `${base}/api/files/${id}` : `/api/files/${id}`;
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        a.click();
        URL.revokeObjectURL(url);
      });
  }

  async function sendFileByEmail(f: StoredFileMeta) {
    const toId = sendToUserId === '' ? users[0]?.id : sendToUserId;
    if (toId == null) {
      setError('Select a recipient');
      return;
    }
    setSendingId(f.id);
    setError('');
    setSuccess('');
    const { data, status } = await api.files.sendEmail(f.id, {
      to_user_id: toId,
      subject: `File: ${f.original_filename}`,
      message: sendMessage || 'Please find the attached file.',
    });
    setSendingId(null);
    if (status === 200) {
      setSuccess((data as { message: string }).message);
    } else setError((data as { error?: string })?.error || 'Failed to send email');
  }

  return (
    <div className="page">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h1>File store</h1>
          <p className="page-subtitle">Store files and send them by email</p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            style={{ display: 'none' }}
            onChange={handleUpload}
          />
          <button
            type="button"
            className="btn btn-primary"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? 'Uploading…' : 'Upload file'}
          </button>
        </div>
      </header>
      {error && <p className="form-error">{error}</p>}
      {success && <p className="muted" style={{ color: 'var(--accent)' }}>{success}</p>}
      {loading ? (
        <p className="muted">Loading…</p>
      ) : files.length === 0 ? (
        <p className="muted">No files yet. Upload a file to get started.</p>
      ) : (
        <ul className="list-card">
          {files.map((f) => (
            <li key={f.id} className="list-card-item">
              <div>
                <strong>{f.original_filename}</strong>
                <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.9rem' }}>
                  {(f.file_size / 1024).toFixed(1)} KB · {new Date(f.created_at).toLocaleString()}
                </p>
              </div>
              <div className="file-actions">
                <button type="button" className="btn btn-sm" onClick={() => downloadFile(f.id, f.original_filename)}>
                  Download
                </button>
                <div className="send-email-inline">
                  <select
                    value={sendToUserId === '' ? '' : String(sendToUserId)}
                    onChange={(e) => setSendToUserId(e.target.value ? Number(e.target.value) : '')}
                    className="select-user"
                  >
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={sendingId !== null}
                    onClick={() => sendFileByEmail(f)}
                  >
                    {sendingId === f.id ? 'Sending…' : 'Send by email'}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      {files.length > 0 && users.length > 0 && (
        <div className="form-card" style={{ marginTop: '1.5rem' }}>
          <p className="muted" style={{ marginBottom: '0.5rem' }}>Optional message when sending a file:</p>
          <input
            type="text"
            placeholder="e.g. Please check the report"
            value={sendMessage}
            onChange={(e) => setSendMessage(e.target.value)}
            style={{ width: '100%', padding: '0.65rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'var(--bg)', color: 'var(--text)' }}
          />
        </div>
      )}
    </div>
  );
}
