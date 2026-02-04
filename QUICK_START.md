# Quick Start Guide - HSEA Assistant

## ✅ Current Status

- ✅ **Backend**: Running on `http://localhost:5001` (port 5001 to avoid AirPlay conflict)
- ✅ **Flutter**: Installed and dependencies ready
- ✅ **Database**: Using SQLite (development mode)

## 🚀 Running the Application

### 1. Start Backend (if not running)

```bash
cd backend
source venv/bin/activate
python run.py
```

The backend will run on `http://localhost:5001` (using port 5001 to avoid macOS AirPlay Receiver conflict)

### 2. Run Flutter App

**Important**: Make sure Flutter is in your PATH. If you just installed it, run:

```bash
export PATH="$PATH:$HOME/flutter/bin"
source ~/.zshrc
```

Then:

```bash
cd flutter

# For iOS Simulator
flutter run -d ios

# For Android Emulator
flutter run -d android

# For Chrome (Web)
flutter run -d chrome

# Or let Flutter choose
flutter run
```

### 3. Update API URL for Your Device

Edit `flutter/lib/services/api_service.dart`:

- **iOS Simulator**: `http://localhost:5001/api`
- **Android Emulator**: `http://10.0.2.2:5001/api`
- **Physical Device**: `http://YOUR_COMPUTER_IP:5001/api` (find IP with `ifconfig` or `ipconfig`)

## 📱 First Steps

1. **Register a user** in the app
2. **Create a workspace** (or use default)
3. **Create tasks** or use voice commands
4. **Test voice assistant**: "Create task for Caleb"

## 🎤 Voice Commands

- "Create task for [name]"
- "Mark task 5 as completed"
- "What tasks are due today?"
- "Schedule meeting with Caleb tomorrow at 2pm"
- "Show me my task completion rate"

## 🔧 Troubleshooting

### Flutter not found
```bash
export PATH="$PATH:$HOME/flutter/bin"
source ~/.zshrc
```

### Backend connection issues
- Check backend is running: `curl http://localhost:5001`
- Update API URL in `api_service.dart` for your platform
- Check firewall settings

### Database issues
- Backend uses SQLite by default (no setup needed)
- For PostgreSQL, update `.env` with `DATABASE_URL`

## 📝 Next Steps

1. Configure Firebase for push notifications
2. Add API keys to `backend/.env`:
   - Azure Speech Services
   - Zoom API
   - Twilio
   - Google Calendar (optional)
   - Outlook Calendar (optional)

Enjoy your HSEA Assistant! 🎉
