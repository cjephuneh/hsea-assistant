from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User
from app.config import Config
import requests
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

gmail_bp = Blueprint('gmail', __name__)

@gmail_bp.route('/authorize', methods=['GET'])
@jwt_required()
def gmail_authorize():
    """Initiate Gmail OAuth flow"""
    client_id = Config.GOOGLE_CLIENT_ID
    redirect_uri = f"{Config.API_BASE_URL}/api/gmail/callback"
    
    if not client_id:
        return jsonify({'error': 'Gmail not configured'}), 500
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=https://www.googleapis.com/auth/gmail.send&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    return jsonify({'auth_url': auth_url}), 200

@gmail_bp.route('/callback', methods=['GET'])
def gmail_callback():
    """Handle Gmail OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    frontend_url = Config.API_BASE_URL.replace('/api', '')
    if not frontend_url.startswith('http'):
        frontend_url = f"http://localhost:5173"
    
    if error:
        return redirect(f"{frontend_url}/dashboard/voice?gmail_error={error}")
    
    if not code:
        return redirect(f"{frontend_url}/dashboard/voice?gmail_error=no_code")
    
    # Exchange code for tokens
    client_id = Config.GOOGLE_CLIENT_ID
    client_secret = Config.GOOGLE_CLIENT_SECRET
    redirect_uri = f"{Config.API_BASE_URL}/api/gmail/callback"
    
    if not client_id or not client_secret:
        return redirect(f"{frontend_url}/dashboard/voice?gmail_error=not_configured")
    
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
        return redirect(f"{frontend_url}/dashboard/voice?gmail_error=token_exchange_failed&detail={error_detail}")
    
    tokens = token_response.json()
    access_token = tokens.get('access_token', '')
    refresh_token = tokens.get('refresh_token', '')
    
    return redirect(
        f"{frontend_url}/dashboard/voice?"
        f"gmail_connected=1&"
        f"access_token={access_token}&"
        f"refresh_token={refresh_token}"
    )

@gmail_bp.route('/connect', methods=['POST'])
@jwt_required()
def gmail_connect():
    """Store Gmail tokens for authenticated user"""
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
        'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    user.gmail_token = json.dumps(tokens)
    db.session.commit()
    
    return jsonify({'message': 'Gmail connected successfully'}), 200

@gmail_bp.route('/status', methods=['GET'])
@jwt_required()
def gmail_status():
    """Check if Gmail is connected"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    connected = bool(user and user.gmail_token)
    return jsonify({'connected': connected}), 200

def get_gmail_access_token(user_id):
    """Get valid Gmail access token, refreshing if needed"""
    user = User.query.get(user_id)
    if not user or not user.gmail_token:
        return None
    
    try:
        tokens = json.loads(user.gmail_token)
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
                        user.gmail_token = json.dumps(tokens)
                        db.session.commit()
                        return tokens['access_token']
                return None
        
        return access_token
    except:
        return None

@gmail_bp.route('/send', methods=['POST'])
@jwt_required()
def send_gmail():
    """Send email via Gmail API"""
    user_id = int(get_jwt_identity())
    access_token = get_gmail_access_token(user_id)
    
    if not access_token:
        return jsonify({'error': 'Gmail not connected'}), 401
    
    data = request.get_json()
    to_email = data.get('to_email')
    subject = data.get('subject', '')
    body = data.get('body', '')
    
    if not to_email:
        return jsonify({'error': 'Recipient email is required'}), 400
    
    # Get sender email from user
    user = User.query.get(user_id)
    from_email = user.email if user else None
    
    if not from_email:
        return jsonify({'error': 'User email not found'}), 400
    
    # Create email message
    message = MIMEMultipart()
    message['to'] = to_email
    message['from'] = from_email
    message['subject'] = subject
    
    message.attach(MIMEText(body, 'plain'))
    
    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    # Send via Gmail API
    response = requests.post(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        json={
            'raw': raw_message
        }
    )
    
    if response.status_code != 200:
        return jsonify({
            'error': 'Failed to send email',
            'details': response.text
        }), 500
    
    return jsonify({
        'message': f'Email sent to {to_email}',
        'message_id': response.json().get('id')
    }), 200
