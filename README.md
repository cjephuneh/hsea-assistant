# HSEA Assistant

A comprehensive task management application with voice assistant, meeting scheduling, and team collaboration features.

## Features

### Core Features
- ✅ Task Management (CRUD operations)
- ✅ User Authentication (Email/Password)
- ✅ Voice Assistant (Azure Voice Live integration)
- ✅ Zoom Meeting Integration
- ✅ Push Notifications (FCM)
- ✅ SMS Notifications (Twilio)
- ✅ Reports & Analytics

### Advanced Features
- ✅ Team Workspaces (Multiple teams/organizations)
- ✅ Task Comments & Mentions (@mentions with notifications)
- ✅ Task Sharing (Public/Private sharing via links)
- ✅ Voice Task Updates ("Mark task 5 as completed")
- ✅ Voice Meeting Scheduling ("Schedule meeting with Caleb tomorrow at 2pm")
- ✅ Voice Reports ("Show me my task completion rate")
- ✅ Calendar Sync (Google Calendar & Outlook)
- ✅ Task Templates (Pre-defined templates for quick task creation)
- ✅ Recurring Tasks
- ✅ Task Dependencies
- ✅ Activity Feed (Track all task changes)
- ✅ Advanced Analytics

## Tech Stack

### Backend
- Flask (Python)
- PostgreSQL
- SQLAlchemy (ORM)
- JWT Authentication
- Flask-SocketIO (WebSockets)

### Frontend
- Flutter (Dart)
- Provider (State Management)
- Firebase Cloud Messaging
- Azure Speech Services

### Integrations
- Azure Voice Live
- Zoom API
- Twilio SMS
- Firebase Cloud Messaging
- Google Calendar API
- Microsoft Outlook API

## Setup Instructions

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database:**
   ```bash
   createdb hsea_assistant
   ```

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys:
   - Database URL
   - Azure Speech Services key
   - Zoom API credentials
   - Twilio credentials
   - Firebase credentials
   - Google Calendar credentials (optional)
   - Outlook Calendar credentials (optional)

6. **Run database migrations:**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

7. **Start the server:**
   ```bash
   python run.py
   ```
   The backend will run on `http://localhost:5001` (port 5001 to avoid AirPlay conflict on macOS)

### Flutter Setup

1. **Navigate to Flutter directory:**
   ```bash
   cd flutter
   ```

2. **Install dependencies:**
   ```bash
   flutter pub get
   ```

3. **Configure Firebase:**
   - Create a Firebase project
   - Download `google-services.json` for Android
   - Place it in `android/app/`
   - Download `GoogleService-Info.plist` for iOS
   - Place it in `ios/Runner/`

4. **Update API base URL:**
   Edit `lib/services/api_service.dart` and update the `baseUrl` if needed:
   ```dart
   static const String baseUrl = 'http://localhost:5001/api';
   ```
   For Android emulator, use: `http://10.0.2.2:5001/api`
   For iOS simulator, use: `http://localhost:5001/api`
   For physical device, use your computer's IP: `http://YOUR_IP:5000/api`

5. **Run the app:**
   ```bash
   flutter run
   ```

## Running the Application

### Start Backend
```bash
cd backend
source venv/bin/activate
python run.py
```

### Start Flutter App
```bash
cd flutter
flutter run
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Tasks
- `GET /api/tasks` - Get tasks (supports filters: status, workspace_id, search, due_today)
- `POST /api/tasks` - Create task
- `GET /api/tasks/:id` - Get task details
- `PUT /api/tasks/:id` - Update task
- `DELETE /api/tasks/:id` - Delete task
- `POST /api/tasks/:id/comments` - Add comment
- `GET /api/tasks/:id/activities` - Get activity feed
- `POST /api/tasks/:id/share` - Share task
- `GET /api/tasks/shared/:token` - Get shared task
- `GET /api/tasks/due-today` - Get tasks due today

### Voice Commands
- `POST /api/voice/command` - Process voice command
  - "Create task for [name]"
  - "Mark task 5 as completed"
  - "What tasks are due today?"
  - "Schedule meeting with Caleb tomorrow at 2pm"
  - "Show me my task completion rate"

### Workspaces
- `GET /api/workspaces` - Get user's workspaces
- `POST /api/workspaces` - Create workspace
- `POST /api/workspaces/switch` - Switch workspace
- `POST /api/workspaces/:id/members` - Add member

### Templates
- `GET /api/templates` - Get task templates
- `POST /api/templates` - Create template
- `POST /api/templates/:id/create-task` - Create task from template

### Meetings
- `GET /api/meetings` - Get meetings
- `POST /api/meetings` - Create meeting
- `POST /api/meetings/task/:id` - Create meeting for task

### Calendar
- `GET /api/calendar/google/authorize` - Google Calendar OAuth
- `POST /api/calendar/sync/meetings` - Sync meetings to calendar
- `POST /api/calendar/sync/tasks` - Sync tasks to calendar

### Reports
- `GET /api/reports/task-completion` - Task completion report
- `GET /api/reports/user-activity` - User activity report
- `GET /api/reports/export/csv` - Export tasks as CSV
- `GET /api/reports/export/pdf` - Export tasks as PDF

## Voice Commands Examples

- **Create Task:** "Create task for Caleb to review the proposal"
- **Update Status:** "Mark task 5 as completed"
- **Query Tasks:** "What tasks are due today?"
- **Status Check:** "Where are we with task 3?"
- **Schedule Meeting:** "Schedule a meeting with Caleb tomorrow at 2pm"
- **Create Zoom Meeting:** "Create a Zoom meeting for task 3"
- **Reports:** "Show me my task completion rate"
- **Weekly Report:** "How many tasks did I complete this week?"

## Project Structure

```
hsea-assistant/
├── backend/
│   ├── app/
│   │   ├── auth/          # Authentication routes
│   │   ├── tasks/         # Task management routes
│   │   ├── voice/         # Voice assistant routes
│   │   ├── meetings/      # Meeting management routes
│   │   ├── notifications/ # Notification services
│   │   ├── reports/       # Report generation
│   │   ├── workspaces/    # Workspace management
│   │   ├── templates/     # Task templates
│   │   ├── calendar/      # Calendar sync
│   │   ├── models.py      # Database models
│   │   └── config.py       # Configuration
│   ├── requirements.txt
│   └── run.py
├── flutter/
│   ├── lib/
│   │   ├── screens/       # UI screens
│   │   ├── services/       # API services
│   │   ├── models/         # Data models
│   │   ├── widgets/        # Reusable widgets
│   │   └── theme/          # App theme
│   └── pubspec.yaml
└── realtimeapi/            # Azure Voice Live integration
```

## Environment Variables

See `backend/.env.example` for all required environment variables.

## License

MIT License
