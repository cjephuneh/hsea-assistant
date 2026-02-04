import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const navGroups = [
  {
    label: 'Work',
    items: [
      { to: '/dashboard', label: 'Home', icon: '◆' },
      { to: '/dashboard/todo', label: 'Todo', icon: '◇' },
      { to: '/dashboard/tasks', label: 'Tasks', icon: '✓' },
      { to: '/dashboard/voice', label: 'Voice', icon: '◉' },
    ],
  },
  {
    label: 'Collaborate',
    items: [
      { to: '/dashboard/meetings', label: 'Meetings', icon: '▣' },
      { to: '/dashboard/whiteboard', label: 'Whiteboard', icon: '▤' },
      { to: '/dashboard/workspaces', label: 'Workspaces', icon: '◈' },
    ],
  },
  {
    label: 'Tools',
    items: [
      { to: '/dashboard/reports', label: 'Reports', icon: '▥' },
      { to: '/dashboard/templates', label: 'Templates', icon: '▦' },
      { to: '/dashboard/files', label: 'Files', icon: '▧' },
    ],
  },
  {
    label: 'Account',
    items: [
      { to: '/dashboard/notifications', label: 'Alerts', icon: '◐' },
      { to: '/dashboard/mail', label: 'Email', icon: '✉' },
      { to: '/dashboard/profile', label: 'Profile', icon: '○' },
    ],
  },
];

const flatNavItems = navGroups.flatMap((g) => g.items);

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.4rem' }}>
            <span className="sidebar-logo">HSEA</span>
            <span style={{
              fontSize: '0.7rem',
              padding: '0.2rem 0.45rem',
              background: 'var(--primary-light)',
              borderRadius: 6,
              color: 'var(--primary)',
              fontWeight: 700,
              letterSpacing: '0.04em',
            }}>
              Assistant
            </span>
          </div>
          <span className="sidebar-user">{user?.name || user?.email}</span>
        </div>
        <nav className="sidebar-nav">
          {navGroups.map((group) => (
            <div key={group.label}>
              <div className="nav-group-label">{group.label}</div>
              {group.items.map(({ to, label, icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                >
                  <span className="nav-icon">{icon}</span>
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <button type="button" className="sidebar-logout" onClick={handleLogout}>
          Sign out
        </button>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
      <nav className="bottom-nav" aria-label="Main">
        {flatNavItems.slice(0, 6).map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `bottom-nav-link ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{icon}</span>
            <span className="nav-label">{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
