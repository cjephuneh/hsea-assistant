from app import db
from datetime import datetime
from sqlalchemy import Enum
import enum

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationType(enum.Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_REMINDER = "meeting_reminder"
    MENTION = "mention"
    COMMENT_ADDED = "comment_added"

class RecurrenceType(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class TaskShareType(enum.Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    WORKSPACE = "workspace"

class Workspace(db.Model):
    __tablename__ = 'workspaces'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = db.relationship('WorkspaceMember', backref='workspace', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='workspace', lazy='dynamic')
    templates = db.relationship('TaskTemplate', backref='workspace', lazy='dynamic')
    
    def __repr__(self):
        return f'<Workspace {self.name}>'

class WorkspaceMember(db.Model):
    __tablename__ = 'workspace_members'
    
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # owner, admin, member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('workspace_id', 'user_id'),)
    
    def __repr__(self):
        return f'<WorkspaceMember {self.workspace_id}-{self.user_id}>'

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    fcm_token = db.Column(db.Text)
    current_workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True)
    google_calendar_token = db.Column(db.Text)
    outlook_calendar_token = db.Column(db.Text)
    zoom_token = db.Column(db.Text)
    gmail_token = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks_assigned = db.relationship('Task', foreign_keys='Task.assignee_id', backref='assignee', lazy='dynamic')
    tasks_created = db.relationship('Task', foreign_keys='Task.created_by_id', backref='creator', lazy='dynamic')
    comments = db.relationship('Comment', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    meetings = db.relationship('Meeting', backref='user', lazy='dynamic')
    workspace_memberships = db.relationship('WorkspaceMember', backref='user', lazy='dynamic')
    owned_workspaces = db.relationship('Workspace', foreign_keys='Workspace.owner_id', backref='owner', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.email}>'

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey('task_templates.id'), nullable=True)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)  # For dependencies
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    category = db.Column(db.String(50))
    due_date = db.Column(db.DateTime)
    share_type = db.Column(db.Enum(TaskShareType), default=TaskShareType.PRIVATE)
    share_token = db.Column(db.String(100), unique=True, nullable=True)  # For public sharing
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_type = db.Column(db.Enum(RecurrenceType), nullable=True)
    recurrence_config = db.Column(db.Text)  # JSON config for recurrence
    next_occurrence = db.Column(db.DateTime, nullable=True)
    estimated_hours = db.Column(db.Float, nullable=True)
    actual_hours = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)  # Free-form notes on the task
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='task', lazy='dynamic', cascade='all, delete-orphan', order_by='Comment.created_at')
    meetings = db.relationship('Meeting', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('TaskActivity', backref='task', lazy='dynamic', order_by='TaskActivity.created_at.desc()')
    dependencies = db.relationship('TaskDependency', foreign_keys='TaskDependency.task_id', backref='task', lazy='dynamic')
    dependents = db.relationship('TaskDependency', foreign_keys='TaskDependency.depends_on_id', backref='depends_on_task', lazy='dynamic')
    subtasks = db.relationship('Task', remote_side=[id], backref='parent_task', lazy='select')
    
    def __repr__(self):
        return f'<Task {self.title}>'

class TaskTemplate(db.Model):
    __tablename__ = 'task_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title_template = db.Column(db.String(200), nullable=False)
    description_template = db.Column(db.Text)
    default_priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    default_category = db.Column(db.String(50))
    estimated_hours = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TaskTemplate {self.name}>'

class TaskDependency(db.Model):
    __tablename__ = 'task_dependencies'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    depends_on_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('task_id', 'depends_on_id'),)
    
    def __repr__(self):
        return f'<TaskDependency {self.task_id}->{self.depends_on_id}>'

class TaskActivity(db.Model):
    __tablename__ = 'task_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # created, updated, status_changed, commented, etc.
    description = db.Column(db.Text, nullable=False)
    activity_metadata = db.Column(db.Text)  # JSON for additional data (renamed from metadata - reserved keyword)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TaskActivity {self.activity_type}>'

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)  # For threading
    content = db.Column(db.Text, nullable=False)
    mentions = db.Column(db.Text)  # JSON array of mentioned user IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    replies = db.relationship('Comment', backref=db.backref('parent_comment', remote_side=[id]), lazy='dynamic')
    
    def __repr__(self):
        return f'<Comment {self.id}>'

class Meeting(db.Model):
    __tablename__ = 'meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True)
    zoom_meeting_id = db.Column(db.String(100), unique=True)
    topic = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=30)  # minutes
    join_url = db.Column(db.Text)
    source = db.Column(db.String(50), nullable=True)  # 'Local', 'Zoom', 'Google Calendar'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Meeting {self.topic}>'

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.Enum(NotificationType), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.title}>'


class TaskAttachment(db.Model):
    __tablename__ = 'task_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    stored_file_id = db.Column(db.Integer, db.ForeignKey('stored_files.id'), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    task = db.relationship('Task', backref=db.backref('attachments', lazy='dynamic', cascade='all, delete-orphan'))
    stored_file = db.relationship('StoredFile', backref=db.backref('task_attachments', lazy='dynamic'))
    uploaded_by = db.relationship('User', backref=db.backref('task_uploads', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TaskAttachment task={self.task_id} file={self.stored_file_id}>'


class TaskCollaborator(db.Model):
    __tablename__ = 'task_collaborators'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('task_id', 'user_id'),)
    
    task = db.relationship('Task', backref=db.backref('collaborators', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('task_collaborations', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TaskCollaborator task={self.task_id} user={self.user_id}>'


class StoredFile(db.Model):
    __tablename__ = 'stored_files'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(100), unique=True, nullable=False)  # uuid on disk
    content_type = db.Column(db.String(100), nullable=True)
    file_size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('stored_files', lazy='dynamic'))
    
    def __repr__(self):
        return f'<StoredFile {self.original_filename}>'


class Whiteboard(db.Model):
    __tablename__ = 'whiteboards'
    
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False, default='Untitled Whiteboard')
    content = db.Column(db.Text, nullable=True)  # JSON canvas state
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('whiteboards', lazy='dynamic'))
    workspace = db.relationship('Workspace', backref=db.backref('whiteboards', lazy='dynamic'))
    documents = db.relationship('WhiteboardDocument', backref='whiteboard', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Whiteboard {self.title}>'


class WhiteboardDocument(db.Model):
    __tablename__ = 'whiteboard_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    whiteboard_id = db.Column(db.Integer, db.ForeignKey('whiteboards.id'), nullable=False)
    stored_file_id = db.Column(db.Integer, db.ForeignKey('stored_files.id'), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    stored_file = db.relationship('StoredFile', backref=db.backref('whiteboard_docs', lazy='dynamic'))
    uploaded_by = db.relationship('User', backref=db.backref('whiteboard_uploads', lazy='dynamic'))
    
    def __repr__(self):
        return f'<WhiteboardDocument whiteboard={self.whiteboard_id} file={self.stored_file_id}>'
