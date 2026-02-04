import firebase_admin
from firebase_admin import credentials, messaging
from app.config import Config
import os

# Initialize Firebase Admin SDK
firebase_initialized = False

def initialize_firebase():
    global firebase_initialized
    if firebase_initialized:
        return
    
    if Config.FIREBASE_CREDENTIALS_PATH and os.path.exists(Config.FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
    else:
        print("Firebase credentials not found. Push notifications disabled.")

def send_push_notification(fcm_token: str, title: str, body: str, data: dict = None):
    """Send push notification using FCM"""
    initialize_firebase()
    
    if not firebase_initialized:
        print("Firebase not initialized. Push notification not sent.")
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            token=fcm_token
        )
        
        response = messaging.send(message)
        print(f"Successfully sent push notification: {response}")
        return True
    except Exception as e:
        print(f"Failed to send push notification: {e}")
        return False
