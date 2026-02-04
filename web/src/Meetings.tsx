import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApiGuard } from './hooks/useApiGuard';
import { api } from './api';
import type { Meeting } from './api';

interface GoogleCalendarEvent {
  id: string;
  summary: string;
  description?: string;
  start: { dateTime: string; timeZone: string };
  end: { dateTime: string; timeZone: string };
  htmlLink?: string;
}

export function Meetings() {
  const { canMakeRequests } = useApiGuard();
  const [searchParams, setSearchParams] = useSearchParams();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [googleEvents, setGoogleEvents] = useState<GoogleCalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [googleConnected, setGoogleConnected] = useState(false);
  const [zoomConnected, setZoomConnected] = useState(false);
  const [connectingGoogle, setConnectingGoogle] = useState(false);
  const [connectingZoom, setConnectingZoom] = useState(false);
  const [loadingGoogleEvents, setLoadingGoogleEvents] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creatingMeeting, setCreatingMeeting] = useState(false);
  const [formData, setFormData] = useState({
    topic: '',
    start_time: '',
    duration: '30',
  });

  // Handle OAuth callbacks
  useEffect(() => {
    // Google Calendar callback
    const googleAccessToken = searchParams.get('access_token');
    const googleRefreshToken = searchParams.get('refresh_token');
    const googleConnected = searchParams.get('google_calendar_connected');
    
    if (googleConnected === '1' && googleAccessToken && googleRefreshToken) {
      setConnectingGoogle(true);
      api.calendar.google.connect(googleAccessToken, googleRefreshToken).then(({ status }) => {
        if (status === 200) {
          setGoogleConnected(true);
          setSearchParams({});
          loadGoogleEvents();
        }
        setConnectingGoogle(false);
      }).catch(() => {
        setConnectingGoogle(false);
      });
    }

    // Zoom callback
    const zoomAccessToken = searchParams.get('access_token');
    const zoomRefreshToken = searchParams.get('refresh_token');
    const zoomConnected = searchParams.get('zoom_connected');
    
    if (zoomConnected === '1' && zoomAccessToken && zoomRefreshToken) {
      setConnectingZoom(true);
      api.meetings.zoom.connect(zoomAccessToken, zoomRefreshToken).then(({ status }) => {
        if (status === 200) {
          setZoomConnected(true);
          setSearchParams({});
          loadMeetings();
        }
        setConnectingZoom(false);
      }).catch(() => {
        setConnectingZoom(false);
      });
    }

    const error = searchParams.get('error') || searchParams.get('zoom_error');
    if (error) {
      console.error('Connection error:', error);
      setSearchParams({});
    }
  }, [searchParams, setSearchParams]);

  // Check connection statuses and load data
  useEffect(() => {
    if (!canMakeRequests) {
      setLoading(false);
      return;
    }
    
    Promise.all([
      api.calendar.google.status().then(({ data, status }) => {
        if (status === 200) {
          setGoogleConnected(data.connected);
          if (data.connected) loadGoogleEvents();
        }
      }).catch(() => {}),
      api.meetings.zoom.status().then(({ data, status }) => {
        if (status === 200) {
          setZoomConnected(data.connected);
        }
      }).catch(() => {}),
      loadMeetings()
    ]).finally(() => setLoading(false));
  }, [canMakeRequests]);

  const loadMeetings = async () => {
    try {
      const { data, status } = await api.meetings.list(zoomConnected);
      if (status === 200) setMeetings(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to load meetings:', e);
    }
  };

  const loadGoogleEvents = () => {
    setLoadingGoogleEvents(true);
    const timeMin = new Date().toISOString();
    const timeMax = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();
    
    api.calendar.google.events(timeMin, timeMax, 50).then(({ data, status }) => {
      if (status === 200 && data.events) {
        setGoogleEvents(data.events);
      }
      setLoadingGoogleEvents(false);
    }).catch(() => {
      setLoadingGoogleEvents(false);
    });
  };

  const handleConnectGoogle = async () => {
    setConnectingGoogle(true);
    try {
      const { data, status } = await api.calendar.google.authorize();
      if (status === 200 && data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (error) {
      console.error('Failed to initiate Google Calendar connection:', error);
      setConnectingGoogle(false);
    }
  };

  const handleConnectZoom = async () => {
    setConnectingZoom(true);
    try {
      const { data, status } = await api.meetings.zoom.authorize();
      if (status === 200 && data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (error) {
      console.error('Failed to initiate Zoom connection:', error);
      setConnectingZoom(false);
    }
  };

  const handleCreateMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.topic.trim() || !formData.start_time) {
      return;
    }

    if (!zoomConnected) {
      alert('Please connect Zoom first to create meetings');
      return;
    }

    setCreatingMeeting(true);
    try {
      const { status } = await api.meetings.create({
        topic: formData.topic.trim(),
        start_time: new Date(formData.start_time).toISOString(),
        duration: parseInt(formData.duration),
      });
      if (status === 201) {
        setShowCreateForm(false);
        setFormData({ topic: '', start_time: '', duration: '30' });
        loadMeetings();
      }
    } catch (error) {
      console.error('Failed to create meeting:', error);
    } finally {
      setCreatingMeeting(false);
    }
  };

  const handleDeleteMeeting = async (id: number) => {
    if (!confirm('Are you sure you want to cancel this meeting?')) return;
    try {
      const { status } = await api.meetings.delete(id);
      if (status === 200) {
        loadMeetings();
      }
    } catch (error) {
      console.error('Failed to delete meeting:', error);
    }
  };

  const allMeetings = [
    ...meetings.filter(m => m.source === 'local' || !m.source),
    ...meetings.filter(m => m.source === 'zoom'),
  ].sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

  return (
    <div className="page meetings-page">
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <h1>Meetings</h1>
            <p className="page-subtitle">Manage your Zoom meetings and calendar events</p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {zoomConnected && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setShowCreateForm(!showCreateForm)}
              >
                {showCreateForm ? 'Cancel' : '+ New Meeting'}
              </button>
            )}
            {!zoomConnected && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConnectZoom}
                disabled={connectingZoom}
              >
                {connectingZoom ? 'Connecting...' : 'Connect Zoom'}
              </button>
            )}
            {!googleConnected && (
              <button
                type="button"
                className="btn"
                onClick={handleConnectGoogle}
                disabled={connectingGoogle}
              >
                {connectingGoogle ? 'Connecting...' : 'Connect Google Calendar'}
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Connection Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {zoomConnected && (
          <div style={{
            padding: '1rem',
            background: 'var(--bg-card)',
            border: '1.5px solid var(--border)',
            borderRadius: 'var(--radius)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <strong style={{ color: '#22c55e' }}>✓ Zoom Connected</strong>
              <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.85rem' }}>
                Create and manage meetings
              </p>
            </div>
          </div>
        )}
        {googleConnected && (
          <div style={{
            padding: '1rem',
            background: 'var(--bg-card)',
            border: '1.5px solid var(--border)',
            borderRadius: 'var(--radius)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <strong style={{ color: '#22c55e' }}>✓ Google Calendar Connected</strong>
              <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.85rem' }}>
                Calendar events synced
              </p>
            </div>
            <button
              type="button"
              className="btn btn-sm"
              onClick={loadGoogleEvents}
              disabled={loadingGoogleEvents}
            >
              {loadingGoogleEvents ? '...' : 'Refresh'}
            </button>
          </div>
        )}
      </div>

      {/* Create Meeting Form */}
      {showCreateForm && zoomConnected && (
        <div style={{
          padding: '1.5rem',
          background: 'var(--bg-card)',
          border: '1.5px solid var(--border)',
          borderRadius: 'var(--radius)',
          marginBottom: '1.5rem'
        }}>
          <h2 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.25rem', fontWeight: 600 }}>Create New Meeting</h2>
          <form onSubmit={handleCreateMeeting}>
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label htmlFor="meeting-topic" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                Meeting Topic *
              </label>
              <input
                id="meeting-topic"
                type="text"
                value={formData.topic}
                onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                placeholder="e.g., Team Standup"
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
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group">
                <label htmlFor="meeting-time" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                  Start Time *
                </label>
                <input
                  id="meeting-time"
                  type="datetime-local"
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
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
                <label htmlFor="meeting-duration" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                  Duration (minutes)
                </label>
                <input
                  id="meeting-duration"
                  type="number"
                  min="15"
                  step="15"
                  value={formData.duration}
                  onChange={(e) => setFormData({ ...formData, duration: e.target.value })}
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
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={creatingMeeting}
              >
                {creatingMeeting ? 'Creating...' : 'Create Meeting'}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setShowCreateForm(false);
                  setFormData({ topic: '', start_time: '', duration: '30' });
                }}
                disabled={creatingMeeting}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          {/* Zoom Meetings */}
          {allMeetings.length > 0 && (
            <div style={{ marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem', fontWeight: 600 }}>
                Upcoming Meetings
              </h2>
              <div style={{ display: 'grid', gap: '0.75rem' }}>
                {allMeetings.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      padding: '1rem',
                      background: 'var(--bg-card)',
                      border: '1.5px solid var(--border)',
                      borderRadius: 'var(--radius)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '1rem'
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <strong>{m.topic}</strong>
                        {m.source === 'zoom' && (
                          <span style={{
                            fontSize: '0.75rem',
                            padding: '0.125rem 0.5rem',
                            background: 'rgba(99, 102, 241, 0.2)',
                            color: '#818cf8',
                            borderRadius: 'var(--radius-sm)'
                          }}>
                            Zoom
                          </span>
                        )}
                      </div>
                      <p className="muted" style={{ margin: 0, fontSize: '0.9rem' }}>
                        {new Date(m.start_time).toLocaleString()} • {m.duration || 30} min
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {m.join_url && (
                        <a
                          href={m.join_url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-primary btn-sm"
                        >
                          Join
                        </a>
                      )}
                      {m.source !== 'zoom' && typeof m.id === 'number' && (
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => handleDeleteMeeting(m.id as number)}
                          style={{ color: 'var(--danger)' }}
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Google Calendar Events */}
          {googleConnected && (
            <div>
              <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem', fontWeight: 600 }}>
                Google Calendar Events
              </h2>
              {loadingGoogleEvents ? (
                <p className="muted">Loading calendar events…</p>
              ) : googleEvents.length === 0 ? (
                <p className="muted">No upcoming events in the next 30 days.</p>
              ) : (
                <div style={{ display: 'grid', gap: '0.75rem' }}>
                  {googleEvents.map((event) => (
                    <div
                      key={event.id}
                      style={{
                        padding: '1rem',
                        background: 'var(--bg-card)',
                        border: '1.5px solid var(--border)',
                        borderRadius: 'var(--radius)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '1rem'
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <strong>{event.summary}</strong>
                        {event.description && (
                          <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.85rem' }}>
                            {event.description.substring(0, 100)}{event.description.length > 100 ? '...' : ''}
                          </p>
                        )}
                        <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.9rem' }}>
                          {new Date(event.start.dateTime).toLocaleString()} - {new Date(event.end.dateTime).toLocaleTimeString()}
                        </p>
                      </div>
                      {event.htmlLink && (
                        <a
                          href={event.htmlLink}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-sm"
                        >
                          View
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Empty State */}
          {allMeetings.length === 0 && (!googleConnected || googleEvents.length === 0) && (
            <div style={{
              padding: '3rem 1.5rem',
              textAlign: 'center',
              background: 'var(--bg-card)',
              border: '1.5px solid var(--border)',
              borderRadius: 'var(--radius)'
            }}>
              <p className="muted" style={{ fontSize: '1rem', marginBottom: '1rem' }}>
                {!zoomConnected && !googleConnected
                  ? 'Connect Zoom or Google Calendar to get started'
                  : 'No meetings or events scheduled'}
              </p>
              {!zoomConnected && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleConnectZoom}
                  disabled={connectingZoom}
                >
                  {connectingZoom ? 'Connecting...' : 'Connect Zoom'}
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
