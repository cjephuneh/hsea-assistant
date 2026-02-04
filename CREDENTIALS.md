# HSEA Assistant - Required Credentials

## Backend Configuration (.env file)

Create a `.env` file in the `backend/` directory with the following credentials:

### Required for Basic Functionality

```bash
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production

# Database (use SQLite for development, PostgreSQL for production)
DATABASE_URL=sqlite:///hsea_assistant.db
# OR for PostgreSQL:
# DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/hsea_assistant
```

### Optional - For Full Features

#### Azure Speech Services (for Voice Assistant)
```bash
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=your-azure-region
```
**How to get:**
1. Go to https://portal.azure.com
2. Create a Speech Services resource
3. Copy the Key and Region

#### Zoom API (for Meeting Scheduling)
```bash
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret
ZOOM_ACCOUNT_ID=your-zoom-account-id
```
**How to get:**
1. Go to https://marketplace.zoom.us/
2. Create a Server-to-Server OAuth app
3. Copy Client ID, Client Secret, and Account ID

#### Twilio (for SMS Notifications)
```bash
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number
```
**How to get:**
1. Sign up at https://www.twilio.com/
2. Get Account SID and Auth Token from dashboard
3. Purchase a phone number

#### Firebase Cloud Messaging (for Push Notifications)
```bash
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json
```
**How to get:**
1. Go to https://console.firebase.google.com/
2. Create a project
3. Download `google-services.json` (Android) or `GoogleService-Info.plist` (iOS)
4. For backend, create a service account and download JSON credentials

#### Google Calendar (Optional)
```bash
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```
**How to get:**
1. Go to https://console.cloud.google.com/
2. Create OAuth 2.0 credentials
3. Enable Google Calendar API

#### Outlook Calendar (Optional)
```bash
OUTLOOK_CLIENT_ID=your-outlook-client-id
OUTLOOK_CLIENT_SECRET=your-outlook-client-secret
```
**How to get:**
1. Go to https://portal.azure.com
2. Register an app in Azure Active Directory
3. Create client secret

## Quick Start (Minimal Setup)

For development, you only need:

```bash
# backend/.env
SECRET_KEY=dev-secret-key-12345
JWT_SECRET_KEY=dev-jwt-secret-12345
FLASK_ENV=development
FLASK_APP=run.py
```

The app will work with:
- ✅ SQLite database (no setup needed)
- ✅ All core features (tasks, voice commands, workspaces, etc.)
- ❌ Voice transcription (needs Azure Speech)
- ❌ Zoom meetings (needs Zoom API)
- ❌ SMS notifications (needs Twilio)
- ❌ Push notifications (needs Firebase)

## Flutter Configuration

### API Base URL

Edit `flutter/lib/services/api_service.dart`:

```dart
static const String baseUrl = 'http://localhost:5001/api';
```

- **iOS Simulator**: `http://localhost:5001/api`
- **Android Emulator**: `http://10.0.2.2:5001/api`
- **Physical Device**: `http://YOUR_COMPUTER_IP:5001/api`

Find your IP:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

## Testing Without Credentials

You can test the app with minimal setup:

1. **Backend**: Just set `SECRET_KEY` and `JWT_SECRET_KEY` in `.env`
2. **Database**: Uses SQLite automatically (no setup)
3. **Features that work**:
   - User registration/login
   - Task management
   - Workspaces
   - Comments
   - Voice commands (text-based, no transcription)
   - Reports

4. **Features that need credentials**:
   - Voice transcription (Azure Speech)
   - Zoom meetings (Zoom API)
   - SMS notifications (Twilio)
   - Push notifications (Firebase)

## Production Setup

For production, you should:
1. Use PostgreSQL instead of SQLite
2. Set strong, random `SECRET_KEY` and `JWT_SECRET_KEY`
3. Configure all API keys
4. Set up proper CORS origins
5. Use environment-specific configurations
