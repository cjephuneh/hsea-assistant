import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext';
import { Login } from './Login';
import { Register } from './Register';
import { Layout } from './Layout';
import { Dashboard } from './Dashboard';
import { Tasks } from './Tasks';
import { TaskDetail } from './TaskDetail';
import { CreateTask } from './CreateTask';
import { Voice } from './Voice';
import { Meetings } from './Meetings';
import { Reports } from './Reports';
import { Profile } from './Profile';
import { Workspaces } from './Workspaces';
import { Templates } from './Templates';
import { Notifications } from './Notifications';
import { TodoList } from './TodoList';
import { FileStore } from './FileStore';
import { SendEmail } from './SendEmail';
import { Whiteboard } from './Whiteboard';
import './index.css';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <p>Loading…</p>
        </div>
      </div>
    );
  }
  if (!user) {
    // Ensure token is cleared
    if (localStorage.getItem('access_token')) {
      localStorage.removeItem('access_token');
    }
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={
        <ProtectedRoute><Layout /></ProtectedRoute>
      }>
        <Route index element={<Dashboard />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="tasks/new" element={<CreateTask />} />
        <Route path="tasks/:id" element={<TaskDetail />} />
        <Route path="todo" element={<TodoList />} />
        <Route path="voice" element={<Voice />} />
        <Route path="meetings" element={<Meetings />} />
        <Route path="reports" element={<Reports />} />
        <Route path="workspaces" element={<Workspaces />} />
        <Route path="templates" element={<Templates />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="files" element={<FileStore />} />
        <Route path="whiteboard" element={<Whiteboard />} />
        <Route path="whiteboard/:id" element={<Whiteboard />} />
        <Route path="mail" element={<SendEmail />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
