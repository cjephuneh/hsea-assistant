const API_BASE = 'https://hsea-evcfc7bwh7fvaefr.canadacentral-01.azurewebsites.net/api';

function getToken(): string | null {
  const token = localStorage.getItem('access_token');
  // Remove any whitespace that might have been accidentally added
  return token ? token.trim() : null;
}

async function request<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<{ data: T; status: number }> {
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else if (!path.startsWith('/auth/register') && !path.startsWith('/auth/login')) {
    console.warn(`[API] No token found for request to ${path}`);
  }

  const url = `${API_BASE}${path}`;
  if (import.meta.env.DEV) {
    console.log(`[API] ${options.method || 'GET'} ${url}`, token ? `with token (${token.substring(0, 20)}...)` : 'no token');
  }
  
  const res = await fetch(url, { ...options, headers });
  let data: unknown = {};
  try {
    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('json')) {
      data = await res.json();
    }
  } catch (e) {
    // Response is not JSON or failed to parse
    console.warn('Failed to parse response as JSON:', e);
  }
  
  // 401 = missing/expired token, 422 = invalid token (Flask-JWT-Extended)
  if (res.status === 401 || res.status === 422) {
    if (import.meta.env.DEV) {
      console.error(`[API] Auth error ${res.status} on ${path}:`, data);
    }
    const hadToken = !!localStorage.getItem('access_token');
    localStorage.removeItem('access_token');
    if (hadToken) {
      // Only dispatch if we actually had a token (to avoid loops)
      window.dispatchEvent(new CustomEvent('auth:session-invalid'));
    }
  }
  return { data: data as T, status: res.status };
}

export const auth = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (name: string, email: string, password: string, phone?: string) => {
    const body: { name: string; email: string; password: string; phone?: string } = {
      name,
      email,
      password,
    };
    if (phone && phone.trim()) {
      body.phone = phone.trim();
    }
    return request<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
  me: () => request<User>('/auth/me'),
};

export const tasks = {
  list: (params?: { status?: string; assignee?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return request<Task[]>(`/tasks${q ? `?${q}` : ''}`);
  },
  get: (id: number) => request<Task>(`/tasks/${id}`),
  create: (body: Partial<Task> & { assignee_id?: number; parent_task_id?: number; collaborator_ids?: number[]; due_date?: string }) =>
    request<Task>('/tasks', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: number, body: Partial<Task> & { notes?: string; due_date?: string | null }) =>
    request<Task>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  users: () => request<User[]>('/tasks/users'),
  attachments: {
    list: (taskId: number) => request<TaskAttachmentMeta[]>(`/tasks/${taskId}/attachments`),
    add: (taskId: number, fileId: number) =>
      request<TaskAttachmentMeta>(`/tasks/${taskId}/attachments`, {
        method: 'POST',
        body: JSON.stringify({ file_id: fileId }),
      }),
    remove: (taskId: number, attId: number) =>
      request<{ message: string }>(`/tasks/${taskId}/attachments/${attId}`, { method: 'DELETE' }),
  },
  collaborators: {
    add: (taskId: number, userId: number) =>
      request<TaskCollaboratorMeta>(`/tasks/${taskId}/collaborators`, {
        method: 'POST',
        body: JSON.stringify({ user_id: userId }),
      }),
    remove: (taskId: number, userId: number) =>
      request<{ message: string }>(`/tasks/${taskId}/collaborators/${userId}`, { method: 'DELETE' }),
  },
};

export const voice = {
  command: (text: string) =>
    request<{ message: string; task?: Task; tasks?: Task[] }>('/voice/command', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
};

export const meetings = {
  list: (includeZoom?: boolean) =>
    request<Meeting[]>(`/meetings${includeZoom ? '?include_zoom=true' : ''}`),
  create: (data: {
    topic: string;
    start_time: string;
    duration?: number;
    task_id?: number;
  }) =>
    request<Meeting>('/meetings', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    request<{ message: string }>(`/meetings/${id}`, { method: 'DELETE' }),
  zoom: {
    authorize: () => request<{ auth_url: string }>('/meetings/zoom/authorize'),
    connect: (accessToken: string, refreshToken: string) =>
      request<{ message: string }>('/meetings/zoom/connect', {
        method: 'POST',
        body: JSON.stringify({ access_token: accessToken, refresh_token: refreshToken }),
      }),
    status: () => request<{ connected: boolean }>('/meetings/zoom/status'),
  },
};

export const calendar = {
  google: {
    authorize: () => request<{ auth_url: string }>('/calendar/google/authorize'),
    connect: (accessToken: string, refreshToken: string) =>
      request<{ message: string }>('/calendar/google/connect', {
        method: 'POST',
        body: JSON.stringify({ access_token: accessToken, refresh_token: refreshToken }),
      }),
    status: () => request<{ connected: boolean }>('/calendar/google/status'),
    events: (timeMin?: string, timeMax?: string, maxResults?: number) => {
      const params = new URLSearchParams();
      if (timeMin) params.append('time_min', timeMin);
      if (timeMax) params.append('time_max', timeMax);
      if (maxResults) params.append('max_results', String(maxResults));
      return request<{ events: any[] }>(`/calendar/google/events?${params.toString()}`);
    },
    createEvent: (data: {
      summary: string;
      description?: string;
      start_time: string;
      end_time?: string;
      duration?: number;
    }) =>
      request<{ event: any }>('/calendar/google/events', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
};

export const reports = {
  taskCompletion: () => request<ReportData>('/reports/task-completion'),
};

export const workspaces = {
  list: () => request<Workspace[]>('/workspaces'),
  create: (name: string, description?: string) =>
    request<Workspace>('/workspaces', { method: 'POST', body: JSON.stringify({ name, description: description || '' }) }),
  get: (id: number) => request<WorkspaceDetail>(`/workspaces/${id}`),
  switch: (workspaceId: number) =>
    request<{ message: string }>('/workspaces/switch', { method: 'POST', body: JSON.stringify({ workspace_id: workspaceId }) }),
};

export const templates = {
  list: (workspaceId?: number) =>
    request<Template[]>(`/templates${workspaceId != null ? `?workspace_id=${workspaceId}` : ''}`),
  create: (data: {
    name: string;
    title_template: string;
    description?: string;
    description_template?: string;
    default_priority?: string;
    default_category?: string;
    estimated_hours?: number;
    workspace_id?: number;
  }) =>
    request<Template>('/templates', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  createTask: (templateId: number, assigneeId: number, title?: string) =>
    request<Task>(`/templates/${templateId}/create-task`, {
      method: 'POST',
      body: JSON.stringify({ assignee_id: assigneeId, title: title || undefined }),
    }),
};

export const notifications = {
  list: (unreadOnly?: boolean) =>
    request<Notification[]>(`/notifications${unreadOnly ? '?unread_only=true' : ''}`),
  markRead: (id: number) =>
    request<{ message: string }>(`/notifications/${id}/read`, { method: 'PUT' }),
  markAllRead: () =>
    request<{ message: string }>('/notifications/read-all', { method: 'PUT' }),
  unreadCount: () => request<{ count: number }>('/notifications/unread-count'),
};

export const files = {
  list: () => request<StoredFileMeta[]>('/files'),
  upload: async (file: File): Promise<{ data: StoredFileMeta; status: number }> => {
    const token = localStorage.getItem('access_token');
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE}/files`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const data = res.headers.get('content-type')?.includes('json') ? await res.json().catch(() => ({})) : {};
    if (res.status === 401) localStorage.removeItem('access_token');
    return { data: data as StoredFileMeta, status: res.status };
  },
  download: (id: number) => `${API_BASE}/files/${id}`,
  delete: (id: number) =>
    request<{ message: string }>(`/files/${id}`, { method: 'DELETE' }),
  sendEmail: (fileId: number, opts: { to_user_id?: number; to_email?: string; subject?: string; message?: string }) =>
    request<{ message: string }>(`/files/${fileId}/send-email`, {
      method: 'POST',
      body: JSON.stringify(opts),
    }),
};

export const mail = {
  send: (opts: { to_user_id?: number; to_email?: string; subject: string; body: string; file_ids?: number[] }) =>
    request<{ message: string }>('/mail/send', {
      method: 'POST',
      body: JSON.stringify(opts),
    }),
};

export const gmail = {
  authorize: () => request<{ auth_url: string }>('/gmail/authorize'),
  connect: (accessToken: string, refreshToken: string) =>
    request<{ message: string }>('/gmail/connect', {
      method: 'POST',
      body: JSON.stringify({ access_token: accessToken, refresh_token: refreshToken }),
    }),
  status: () => request<{ connected: boolean }>('/gmail/status'),
  send: (toEmail: string, subject: string, body: string) =>
    request<{ message: string; email?: unknown }>('/gmail/send', {
      method: 'POST',
      body: JSON.stringify({ to_email: toEmail, subject, body }),
    }),
};

export interface WhiteboardDocMeta {
  id: number;
  file_id: number;
  original_filename: string;
  content_type?: string;
  file_size?: number;
  uploaded_by?: { id: number; name: string };
  created_at?: string;
}

export interface WhiteboardMeta {
  id: number;
  title: string;
  workspace_id?: number;
  content?: string;
  created_at?: string;
  updated_at?: string;
  documents?: WhiteboardDocMeta[];
  documents_count?: number;
}

export const whiteboards = {
  list: (workspaceId?: number) =>
    request<WhiteboardMeta[]>(`/whiteboards${workspaceId != null ? `?workspace_id=${workspaceId}` : ''}`),
  create: (data: { title?: string; workspace_id?: number; content?: string }) =>
    request<WhiteboardMeta>('/whiteboards', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: number) => request<WhiteboardMeta>(`/whiteboards/${id}`),
  update: (id: number, data: { title?: string; content?: string; workspace_id?: number }) =>
    request<WhiteboardMeta>(`/whiteboards/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: number) => request<{ message: string }>(`/whiteboards/${id}`, { method: 'DELETE' }),
  documents: {
    add: (whiteboardId: number, fileId: number) =>
      request<WhiteboardDocMeta>(`/whiteboards/${whiteboardId}/documents`, {
        method: 'POST',
        body: JSON.stringify({ file_id: fileId }),
      }),
    remove: (whiteboardId: number, docId: number) =>
      request<{ message: string }>(`/whiteboards/${whiteboardId}/documents/${docId}`, { method: 'DELETE' }),
  },
};

/** Single API object used by AuthContext and other components. */
export const api = {
  auth,
  tasks,
  voice,
  meetings,
  calendar,
  reports,
  workspaces,
  templates,
  notifications,
  files,
  mail,
  gmail,
  whiteboards,
};

export interface StoredFileMeta {
  id: number;
  original_filename: string;
  content_type?: string;
  file_size: number;
  created_at: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  phone?: string;
}

export interface TaskAttachmentMeta {
  id: number;
  file_id: number;
  original_filename: string;
  content_type?: string;
  file_size?: number;
  uploaded_by?: { id: number; name: string };
  created_at?: string;
}

export interface TaskCollaboratorMeta {
  id: number;
  name: string;
  email: string;
}

export interface TaskSubtaskMeta {
  id: number;
  title: string;
  description?: string;
  status: string;
  priority: string;
  due_date?: string;
  assignee?: User;
  created_at?: string;
}

export interface Task {
  id: number;
  title: string;
  description?: string;
  notes?: string;
  status: string;
  priority: string;
  due_date?: string;
  assignee?: User;
  created_by?: User;
  created_at?: string;
  updated_at?: string;
  subtasks?: TaskSubtaskMeta[];
  attachments?: TaskAttachmentMeta[];
  collaborators?: TaskCollaboratorMeta[];
}

export interface Meeting {
  id: number | string;
  topic: string;
  start_time: string;
  duration?: number;
  join_url?: string;
  task_id?: number;
  created_at?: string;
  source?: 'local' | 'zoom';
}

export interface ReportData {
  total_tasks?: number;
  total?: number;
  completed: number;
  in_progress?: number;
  pending?: number;
  completion_rate?: number;
  by_status?: Record<string, number>;
}

export interface Workspace {
  id: number;
  name: string;
  description?: string;
  owner_id: number;
  member_count?: number;
  created_at?: string;
}

export interface WorkspaceDetail extends Workspace {
  members: { id: number; name: string; email: string; role: string }[];
}

export interface Template {
  id: number;
  name: string;
  description?: string;
  title_template: string;
  description_template?: string;
  default_priority: string;
  default_category?: string;
  estimated_hours?: number;
  workspace_id?: number;
  created_at?: string;
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
}
