from flask import Blueprint, request, jsonify, redirect
from app import db
from app.models import Meeting, Task, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import requests
import base64
import json
from app.config import Config

meetings_bp = Blueprint('meetings', __name__)

def get_zoom_access_token(user_id=None):
    """Get Zoom OAuth access token for user or fallback to server-to-server"""
    # Try user-specific token first
    if user_id:
        user = User.query.get(user_id)
        if user and user.zoom_token:
            try:
                tokens = json.loads(user.zoom_token)
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
                                'https://zoom.us/oauth/token',
                                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                data={
                                    'grant_type': 'refresh_token',
                                    'refresh_token': refresh_token,
                                    'client_id': Config.ZOOM_CLIENT_ID,
                                    'client_secret': Config.ZOOM_CLIENT_SECRET
                                }
                            )
                            if token_response.status_code == 200:
                                new_tokens = token_response.json()
                                tokens['access_token'] = new_tokens['access_token']
                                tokens['expires_at'] = (datetime.utcnow() + timedelta(seconds=new_tokens.get('expires_in', 3600))).isoformat()
                                if 'refresh_token' in new_tokens:
                                    tokens['refresh_token'] = new_tokens['refresh_token']
                                user.zoom_token = json.dumps(tokens)
                                db.session.commit()
                                return tokens['access_token']
                        return None
                
                return access_token
            except:
                pass
    
    # Fallback to Server-to-Server OAuth
    if Config.ZOOM_ACCOUNT_ID:
        auth_string = f"{Config.ZOOM_CLIENT_ID}:{Config.ZOOM_CLIENT_SECRET}"
        encoded = base64.b64encode(auth_string.encode()).decode()
        
        response = requests.post(
            'https://zoom.us/oauth/token',
            headers={
                'Authorization': f'Basic {encoded}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'grant_type': 'account_credentials',
                'account_id': Config.ZOOM_ACCOUNT_ID
            }
        )
        
        if response.status_code == 200:
            return response.json()['access_token']
    
    return None

@meetings_bp.route('/zoom/authorize', methods=['GET'])
@jwt_required()
def zoom_authorize():
    """Initiate Zoom OAuth flow"""
    client_id = Config.ZOOM_CLIENT_ID
    redirect_uri = f"{Config.API_BASE_URL}/api/meetings/zoom/callback"
    
    if not client_id:
        return jsonify({'error': 'Zoom not configured'}), 500
    
    auth_url = (
        f"https://zoom.us/oauth/authorize?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}"
    )
    
    return jsonify({'auth_url': auth_url}), 200

@meetings_bp.route('/zoom/callback', methods=['GET'])
def zoom_callback():
    """Handle Zoom OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    frontend_url = Config.API_BASE_URL.replace('/api', '')
    if not frontend_url.startswith('http'):
        frontend_url = f"http://localhost:5173"
    
    if error:
        return redirect(f"{frontend_url}/dashboard/meetings?zoom_error={error}")
    
    if not code:
        return redirect(f"{frontend_url}/dashboard/meetings?zoom_error=no_code")
    
    # Exchange code for tokens
    token_response = requests.post(
        'https://zoom.us/oauth/token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f"{Config.API_BASE_URL}/api/meetings/zoom/callback",
            'client_id': Config.ZOOM_CLIENT_ID,
            'client_secret': Config.ZOOM_CLIENT_SECRET
        }
    )
    
    if token_response.status_code != 200:
        return redirect(f"{frontend_url}/dashboard/meetings?zoom_error=token_exchange_failed")
    
    tokens = token_response.json()
    access_token = tokens.get('access_token', '')
    refresh_token = tokens.get('refresh_token', '')
    
    return redirect(
        f"{frontend_url}/dashboard/meetings?"
        f"zoom_connected=1&"
        f"access_token={access_token}&"
        f"refresh_token={refresh_token}"
    )

@meetings_bp.route('/zoom/connect', methods=['POST'])
@jwt_required()
def zoom_connect():
    """Store Zoom tokens for authenticated user"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    access_token = data.get('access_token')
    refresh_token = data.get('refresh_token')
    
    if not access_token:
        return jsonify({'error': 'Access token required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    tokens = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_at': (datetime.utcnow() + timedelta(seconds=3600)).isoformat()
    }
    user.zoom_token = json.dumps(tokens)
    db.session.commit()
    
    return jsonify({'message': 'Zoom connected successfully'}), 200

@meetings_bp.route('/zoom/status', methods=['GET'])
@jwt_required()
def zoom_status():
    """Check if Zoom is connected"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    connected = bool(user and user.zoom_token)
    return jsonify({'connected': connected}), 200

@meetings_bp.route('', methods=['GET'])
@jwt_required()
def get_meetings():
    user_id = int(get_jwt_identity())
    task_id = request.args.get('task_id')
    include_zoom = request.args.get('include_zoom', 'false').lower() == 'true'
    
    query = Meeting.query.filter_by(user_id=user_id)
    if task_id:
        query = query.filter_by(task_id=task_id)
    
    meetings = query.order_by(Meeting.start_time.desc()).all()
    result = [{
        'id': meeting.id,
        'task_id': meeting.task_id,
        'topic': meeting.topic,
        'start_time': meeting.start_time.isoformat(),
        'duration': meeting.duration,
        'join_url': meeting.join_url,
        'created_at': meeting.created_at.isoformat(),
        'source': 'local'
    } for meeting in meetings]
    
    # Fetch Zoom meetings if requested and connected
    if include_zoom:
        access_token = get_zoom_access_token(user_id)
        if access_token:
            try:
                zoom_response = requests.get(
                    'https://api.zoom.us/v2/users/me/meetings',
                    headers={'Authorization': f'Bearer {access_token}'},
                    params={'type': 'upcoming', 'page_size': 30}
                )
                if zoom_response.status_code == 200:
                    zoom_meetings = zoom_response.json().get('meetings', [])
                    for zm in zoom_meetings:
                        result.append({
                            'id': f"zoom_{zm['id']}",
                            'topic': zm.get('topic', 'Untitled Meeting'),
                            'start_time': zm.get('start_time', ''),
                            'duration': zm.get('duration', 0),
                            'join_url': zm.get('join_url', ''),
                            'source': 'zoom'
                        })
            except:
                pass
    
    return jsonify(result), 200

@meetings_bp.route('', methods=['POST'])
@jwt_required()
def create_meeting():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or not data.get('topic') or not data.get('start_time'):
        return jsonify({'error': 'Missing required fields: topic, start_time'}), 400
    
    access_token = get_zoom_access_token(user_id)
    if not access_token:
        return jsonify({'error': 'Zoom authentication failed. Please connect your Zoom account.'}), 500
    
    # Parse start time
    start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
    duration = data.get('duration', 30)
    
    # Create Zoom meeting
    zoom_response = requests.post(
        'https://api.zoom.us/v2/users/me/meetings',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        json={
            'topic': data['topic'],
            'type': 2,  # Scheduled meeting
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'duration': duration,
            'timezone': 'UTC',
            'settings': {
                'join_before_host': True,
                'participant_video': True,
                'host_video': True
            }
        }
    )
    
    if zoom_response.status_code != 201:
        return jsonify({
            'error': 'Failed to create Zoom meeting',
            'details': zoom_response.json()
        }), 500
    
    zoom_meeting = zoom_response.json()
    
    # Save meeting to database
    meeting = Meeting(
        task_id=data.get('task_id'),
        user_id=user_id,
        zoom_meeting_id=str(zoom_meeting['id']),
        topic=data['topic'],
        start_time=start_time,
        duration=duration,
        join_url=zoom_meeting['join_url']
    )
    
    db.session.add(meeting)
    db.session.commit()
    
    # If linked to a task, notify assignee
    if meeting.task_id:
        task = Task.query.get(meeting.task_id)
        if task:
            from app.notifications.service import NotificationService
            NotificationService.create_meeting_scheduled_notification(meeting, task.assignee_id)
    
    return jsonify({
        'id': meeting.id,
        'task_id': meeting.task_id,
        'topic': meeting.topic,
        'start_time': meeting.start_time.isoformat(),
        'duration': meeting.duration,
        'join_url': meeting.join_url,
        'zoom_meeting_id': meeting.zoom_meeting_id
    }), 201

@meetings_bp.route('/<int:meeting_id>', methods=['GET'])
@jwt_required()
def get_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    
    return jsonify({
        'id': meeting.id,
        'task_id': meeting.task_id,
        'topic': meeting.topic,
        'start_time': meeting.start_time.isoformat(),
        'duration': meeting.duration,
        'join_url': meeting.join_url,
        'created_at': meeting.created_at.isoformat()
    }), 200

@meetings_bp.route('/<int:meeting_id>', methods=['DELETE'])
@jwt_required()
def cancel_meeting(meeting_id):
    user_id = int(get_jwt_identity())
    meeting = Meeting.query.get_or_404(meeting_id)
    
    if meeting.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    access_token = get_zoom_access_token()
    if access_token:
        # Cancel Zoom meeting
        requests.delete(
            f'https://api.zoom.us/v2/meetings/{meeting.zoom_meeting_id}',
            headers={'Authorization': f'Bearer {access_token}'}
        )
    
    db.session.delete(meeting)
    db.session.commit()
    
    return jsonify({'message': 'Meeting cancelled successfully'}), 200

@meetings_bp.route('/task/<int:task_id>', methods=['POST'])
@jwt_required()
def create_task_meeting(task_id):
    """Create a meeting linked to a task and invite the assignee"""
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    
    if not data or not data.get('start_time'):
        return jsonify({'error': 'Missing required field: start_time'}), 400
    
    access_token = get_zoom_access_token(user_id)
    if not access_token:
        return jsonify({'error': 'Zoom authentication failed. Please connect your Zoom account.'}), 500
    
    start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
    duration = data.get('duration', 30)
    topic = data.get('topic', f'Meeting for task: {task.title}')
    
    # Create Zoom meeting with assignee as attendee
    zoom_response = requests.post(
        'https://api.zoom.us/v2/users/me/meetings',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        json={
            'topic': topic,
            'type': 2,
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'duration': duration,
            'timezone': 'UTC',
            'settings': {
                'join_before_host': True,
                'participant_video': True,
                'host_video': True
            }
        }
    )
    
    if zoom_response.status_code != 201:
        return jsonify({
            'error': 'Failed to create Zoom meeting',
            'details': zoom_response.json()
        }), 500
    
    zoom_meeting = zoom_response.json()
    
    # Save meeting
    meeting = Meeting(
        task_id=task_id,
        user_id=user_id,
        zoom_meeting_id=str(zoom_meeting['id']),
        topic=topic,
        start_time=start_time,
        duration=duration,
        join_url=zoom_meeting['join_url']
    )
    
    db.session.add(meeting)
    db.session.commit()
    
    # Notify assignee
    from app.notifications.service import NotificationService
    NotificationService.create_meeting_scheduled_notification(meeting, task.assignee_id)
    
    return jsonify({
        'id': meeting.id,
        'task_id': meeting.task_id,
        'topic': meeting.topic,
        'start_time': meeting.start_time.isoformat(),
        'duration': meeting.duration,
        'join_url': meeting.join_url
    }), 201
