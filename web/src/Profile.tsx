import { Link } from 'react-router-dom';
import { useAuth } from './AuthContext';

export function Profile() {
  const { user } = useAuth();

  return (
    <div className="page profile-page">
      <header className="page-header">
        <h1>Profile</h1>
        <p className="page-subtitle">Your account</p>
      </header>
      <div className="profile-card">
        <div className="profile-avatar">{user?.name?.charAt(0)?.toUpperCase() || '?'}</div>
        <h2>{user?.name || 'User'}</h2>
        <p className="profile-email">{user?.email}</p>
        {user?.phone && <p className="profile-phone">{user.phone}</p>}
      </div>
      <nav className="profile-links">
        <Link to="/dashboard/workspaces" className="profile-link">Workspaces</Link>
        <Link to="/dashboard/templates" className="profile-link">Task templates</Link>
        <Link to="/dashboard/files" className="profile-link">File store</Link>
        <Link to="/dashboard/mail" className="profile-link">Send email</Link>
        <Link to="/dashboard/notifications" className="profile-link">Notifications</Link>
      </nav>
      <p className="muted" style={{ marginTop: '1rem' }}>
        HSEA Assistant — same experience on web and mobile.
      </p>
    </div>
  );
}
