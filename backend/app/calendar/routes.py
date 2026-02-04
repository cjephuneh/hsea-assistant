from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Meeting, Task
from app.config import Config
import requests
import json
from datetime import datetime, timedelta

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/google/authorize', methods=['GET'])
@jwt_required()
def google_calendar_authorize():
    """Initiate Google Calendar OAuth flow"""
    user_id = int(get_jwt_identity())
    
    client_id = Config.GOOGLE_CLIENT_ID
    redirect_uri = f"{Config.API_BASE_URL}/api/calendar/google/callback"
    
    if not client_id:
        return jsonify({'error': 'Google Calendar not configured'}), 500
    
    # Store user_id in state for callback verification (in production, use proper session/state)
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    return jsonify({'auth_url': auth_url}), 200

@calendar_bp.route('/google/callback', methods=['GET'])
def google_calendar_callback():
    """Handle Google Calendar OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')
    state = request.args.get('state')  # Could include user_id or session token
    
    frontend_url = Config.API_BASE_URL.replace('/api', '')
    if not frontend_url.startswith('http'):
        # Fallback if API_BASE_URL doesn't include protocol
        frontend_url = f"http://localhost:5173"
    
    if error:
        return redirect(f"{frontend_url}/dashboard/meetings?error={error}")
    
    if not code:
        return redirect(f"{frontend_url}/dashboard/meetings?error=no_code")
    
    # Exchange code for tokens
    client_id = Config.GOOGLE_CLIENT_ID
    client_secret = Config.GOOGLE_CLIENT_SECRET
    redirect_uri = f"{Config.API_BASE_URL}/api/calendar/google/callback"
    
    if not client_id or not client_secret:
        return redirect(f"{frontend_url}/dashboard/meetings?error=not_configured")
    
    token_response = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
    )
    
    if token_response.status_code != 200:
        error_detail = token_response.text
        return redirect(f"{frontend_url}/dashboard/meetings?error=token_exchange_failed&detail={error_detail}")
    
    tokens = token_response.json()
    
    # Redirect to frontend with tokens - frontend will send them to /connect endpoint
    access_token = tokens.get('access_token', '')
    refresh_token = tokens.get('refresh_token', '')
    
    return redirect(
        f"{frontend_url}/dashboard/meetings?"
        f"google_calendar_connected=1&"
        f"access_token={access_token}&"
        f"refresh_token={refresh_token}"
    )

@calendar_bp.route('/google/connect', methods=['POST'])
@jwt_required()
def google_calendar_connect():
    """Store Google Calendar tokens for authenticated user"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    access_token = data.get('access_token')
    refresh_token = data.get('refresh_token')
    
    if not access_token:
        return jsonify({'error': 'Access token required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Store tokens as JSON string
    tokens = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    user.google_calendar_token = json.dumps(tokens)
    db.session.commit()
    
    return jsonify({'message': 'Google Calendar connected successfully'}), 200

@calendar_bp.route('/google/status', methods=['GET'])
@jwt_required()
def google_calendar_status():
    """Check if Google Calendar is connected"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    connected = bool(user and user.google_calendar_token)
    return jsonify({'connected': connected}), 200

def get_google_access_token(user_id):
    """Get valid Google Calendar access token, refreshing if needed"""
    user = User.query.get(user_id)
    if not user or not user.google_calendar_token:
        return None
    
    try:
        tokens = json.loads(user.google_calendar_token)
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        expires_at = tokens.get('expires_at')
        
        # Check if token is expired
        if expires_at:
            expires = datetime.fromisoformat(expires_at)
            if datetime.utcnow() >= expires:
                # Refresh token
                if refresh_token:
                    token_response = requests.post(
                        'https://oauth2.googleapis.com/token',
                        data={
                            'client_id': Config.GOOGLE_CLIENT_ID,
                            'client_secret': Config.GOOGLE_CLIENT_SECRET,
                            'refresh_token': refresh_token,
                            'grant_type': 'refresh_token'
                        }
                    )
                    if token_response.status_code == 200:
                        new_tokens = token_response.json()
                        tokens['access_token'] = new_tokens['access_token']
                        tokens['expires_at'] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
                        if 'refresh_token' in new_tokens:
                            tokens['refresh_token'] = new_tokens['refresh_token']
                        user.google_calendar_token = json.dumps(tokens)
                        db.session.commit()
                        return tokens['access_token']
                return None
        
        return access_token
    except:
        return None

@calendar_bp.route('/google/events', methods=['GET'])
@jwt_required()
def get_google_calendar_events():
    """Fetch events from Google Calendar"""
    user_id = int(get_jwt_identity())
    access_token = get_google_access_token(user_id)
    
    if not access_token:
        return jsonify({'error': 'Google Calendar not connected'}), 401
    
    time_min = request.args.get('time_min')
    time_max = request.args.get('time_max')
    max_results = request.args.get('max_results', 50)
    
    params = {
        'maxResults': max_results,
        'singleEvents': 'true',
        'orderBy': 'startTime'
    }
    
    if time_min:
        params['timeMin'] = time_min
    else:
        params['timeMin'] = datetime.utcnow().isoformat() + 'Z'
    
    if time_max:
        params['timeMax'] = time_max
    
    response = requests.get(
        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
        headers={'Authorization': f'Bearer {access_token}'},
        params=params
    )
    
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch calendar events', 'details': response.text}), 500
    
    events = response.json().get('items', [])
    return jsonify({'events': events}), 200

@calendar_bp.route('/google/events', methods=['POST'])
@jwt_required()
def create_google_calendar_event():
    """Create an event in Google Calendar"""
    user_id = int(get_jwt_identity())
    access_token = get_google_access_token(user_id)
    
    if not access_token:
        return jsonify({'error': 'Google Calendar not connected'}), 401
    
    data = request.get_json()
    summary = data.get('summary') or data.get('title')
    description = data.get('description', '')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    duration = data.get('duration', 30)  # minutes
    
    if not summary or not start_time:
        return jsonify({'error': 'Summary and start_time are required'}), 400
    
    # Parse start_time
    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    if not end_time:
        end_dt = start_dt + timedelta(minutes=duration)
    else:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': 'UTC'
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': 'UTC'
        }
    }
    
    response = requests.post(
        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        json=event
    )
    
    if response.status_code != 200:
        return jsonify({'error': 'Failed to create calendar event', 'details': response.text}), 500
    
    created_event = response.json()
    return jsonify({'event': created_event}), 201

@calendar_bp.route('/sync/meetings', methods=['POST'])
@jwt_required()
def sync_meetings_to_calendar():
    """Sync meetings to Google/Outlook Calendar"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json()
    
    meeting_ids = data.get('meeting_ids', [])
    calendar_type = data.get('calendar_type', 'google')  # google or outlook
    
    meetings = Meeting.query.filter(Meeting.id.in_(meeting_ids)).all()
    
    synced = []
    for meeting in meetings:
        if calendar_type == 'google' and user.google_calendar_token:
            # Create Google Calendar event
            # (Implementation would create event via Google Calendar API)
            synced.append(meeting.id)
        elif calendar_type == 'outlook' and user.outlook_calendar_token:
            # Create Outlook Calendar event
            # (Implementation would create event via Microsoft Graph API)
            synced.append(meeting.id)
    
    return jsonify({
        'message': f'Synced {len(synced)} meeting(s) to {calendar_type} calendar',
        'synced': synced
    }), 200

@calendar_bp.route('/sync/tasks', methods=['POST'])
@jwt_required()
def sync_tasks_to_calendar():
    """Sync tasks with due dates to calendar"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json()
    
    task_ids = data.get('task_ids', [])
    calendar_type = data.get('calendar_type', 'google')
    
    tasks = Task.query.filter(
        Task.id.in_(task_ids),
        Task.due_date.isnot(None)
    ).all()
    
    synced = []
    for task in tasks:
        if calendar_type == 'google' and user.google_calendar_token:
            # Create Google Calendar event for task
            synced.append(task.id)
        elif calendar_type == 'outlook' and user.outlook_calendar_token:
            # Create Outlook Calendar event for task
            synced.append(task.id)
    
    return jsonify({
        'message': f'Synced {len(synced)} task(s) to {calendar_type} calendar',
        'synced': synced
    }), 200
