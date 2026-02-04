import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { WhiteboardMeta, WhiteboardDocMeta } from './api';

export function Whiteboard() {
  const { id } = useParams<{ id?: string }>();
  const { canMakeRequests } = useApiGuard();
  const navigate = useNavigate();
  const [boards, setBoards] = useState<WhiteboardMeta[]>([]);
  const [current, setCurrent] = useState<WhiteboardMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [boardLoading, setBoardLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [contentDraft, setContentDraft] = useState('');
  const [titleDraft, setTitleDraft] = useState('');
  const [uploadingFile, setUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function loadList() {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.whiteboards.list().then(({ data, status }) => {
      if (status === 200) setBoards(Array.isArray(data) ? data : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  function loadBoard(boardId: number) {
    setBoardLoading(true);
    api.whiteboards.get(boardId).then(({ data, status }) => {
      setBoardLoading(false);
      if (status === 200 && data) {
        setCurrent(data as WhiteboardMeta);
        setTitleDraft((data as WhiteboardMeta).title);
        setContentDraft((data as WhiteboardMeta).content ?? '');
      }
    }).catch(() => setBoardLoading(false));
  }

  useEffect(() => {
    loadList();
  }, [canMakeRequests]);

  useEffect(() => {
    if (id && canMakeRequests) {
      const n = Number(id);
      if (!Number.isNaN(n)) loadBoard(n);
      else setCurrent(null);
    } else {
      setCurrent(null);
    }
  }, [id, canMakeRequests]);

  useEffect(() => {
    if (current) {
      setTitleDraft(current.title);
      setContentDraft(current.content ?? '');
    }
  }, [current?.id, current?.title, current?.content]);

  async function createNew() {
    setCreating(true);
    const { data, status } = await api.whiteboards.create({ title: 'Untitled Whiteboard' });
    setCreating(false);
    if (status === 201 && data && 'id' in data) {
      loadList();
      navigate(`/dashboard/whiteboard/${(data as WhiteboardMeta).id}`);
    }
  }

  async function saveContent() {
    if (!current) return;
    setSaving(true);
    await api.whiteboards.update(current.id, { title: titleDraft, content: contentDraft });
    setSaving(false);
    setCurrent((c) => c ? { ...c, title: titleDraft, content: contentDraft } : null);
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !current) return;
    setUploadingFile(true);
    const { data: fileData, status: uploadStatus } = await api.files.upload(file);
    setUploadingFile(false);
    e.target.value = '';
    if (uploadStatus === 201 && fileData?.id) {
      const { status } = await api.whiteboards.documents.add(current.id, fileData.id);
      if (status === 201) loadBoard(current.id);
    }
  }

  async function removeDocument(docId: number) {
    if (!current) return;
    const { status } = await api.whiteboards.documents.remove(current.id, docId);
    if (status === 200) loadBoard(current.id);
  }

  function downloadDoc(fileId: number, name: string) {
    const token = localStorage.getItem('access_token');
    const base = 'https://hsea-evcfc7bwh7fvaefr.canadacentral-01.azurewebsites.net';
    const url = `${base}/api/files/${fileId}`;
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

  if (id && current === null && !boardLoading && !loading) {
    return (
      <div className="page">
        <p className="muted">Whiteboard not found.</p>
        <button type="button" className="btn" onClick={() => navigate('/dashboard/whiteboard')}>Back to whiteboards</button>
      </div>
    );
  }
  if (id && current === null && boardLoading) {
    return <div className="page"><p className="muted">Loading whiteboard…</p></div>;
  }

  if (id && current) {
    const documents = current.documents ?? [];
    return (
      <div className="page">
        <header className="page-header" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-sm" onClick={() => navigate('/dashboard/whiteboard')} aria-label="Back">←</button>
          <input
            type="text"
            value={titleDraft}
            onChange={(e) => setTitleDraft(e.target.value)}
            onBlur={saveContent}
            style={{ flex: 1, minWidth: 160, fontSize: '1.25rem', fontWeight: 600, border: '1px solid var(--border)', borderRadius: 6, padding: '0.5rem' }}
          />
          <button type="button" className="btn btn-primary" disabled={saving} onClick={saveContent}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </header>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '1rem', marginTop: '1rem', minHeight: 400 }}>
          <div className="detail-card" style={{ minHeight: 360 }}>
            <h3 className="section-title" style={{ marginTop: 0, marginBottom: '0.75rem' }}>Canvas / Notes</h3>
            <textarea
              value={contentDraft}
              onChange={(e) => setContentDraft(e.target.value)}
              onBlur={saveContent}
              placeholder="Add notes, ideas, or paste content…"
              style={{ width: '100%', minHeight: 300, resize: 'vertical', fontFamily: 'inherit' }}
            />
          </div>
          <div className="detail-card" style={{ minHeight: 360 }}>
            <h3 className="section-title" style={{ marginTop: 0, marginBottom: '0.75rem' }}>Documents</h3>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              onChange={handleFileUpload}
            />
            <button type="button" className="btn btn-primary" style={{ marginBottom: '0.75rem' }} disabled={uploadingFile} onClick={() => fileInputRef.current?.click()}>
              {uploadingFile ? 'Uploading…' : 'Upload document'}
            </button>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {documents.map((doc: WhiteboardDocMeta) => (
                <li key={doc.id} style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.original_filename}</span>
                  <button type="button" className="btn btn-sm" onClick={() => downloadDoc(doc.file_id, doc.original_filename)}>Download</button>
                  <button type="button" className="btn btn-sm" onClick={() => removeDocument(doc.id)}>Remove</button>
                </li>
              ))}
            </ul>
            {documents.length === 0 && <p className="muted">No documents. Upload PDFs or other files.</p>}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>Whiteboards</h1>
          <p className="page-subtitle">Create whiteboards and attach documents</p>
        </div>
        <button type="button" className="btn btn-primary" disabled={creating} onClick={createNew}>
          {creating ? 'Creating…' : '+ New whiteboard'}
        </button>
      </header>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : boards.length === 0 ? (
        <div className="empty-state">
          <p>No whiteboards yet</p>
          <p>Click &quot;New whiteboard&quot; to create one and attach documents</p>
          <button type="button" className="btn btn-primary" style={{ marginTop: '1rem' }} disabled={creating} onClick={createNew}>
            {creating ? 'Creating…' : 'New whiteboard'}
          </button>
        </div>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '1rem' }}>
          {boards.map((w) => (
            <li key={w.id}>
              <button
                type="button"
                className="detail-card"
                style={{ width: '100%', textAlign: 'left', cursor: 'pointer', border: '1px solid var(--border)' }}
                onClick={() => navigate(`/dashboard/whiteboard/${w.id}`)}
              >
                <strong>{w.title}</strong>
                <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.875rem' }}>
                  Updated {w.updated_at ? new Date(w.updated_at).toLocaleDateString() : '—'}
                  {w.documents_count != null && w.documents_count > 0 && ` · ${w.documents_count} doc(s)`}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
