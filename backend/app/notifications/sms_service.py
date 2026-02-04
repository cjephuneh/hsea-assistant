from twilio.rest import Client
from app.config import Config

def send_sms(to_phone: str, message: str):
    """Send SMS using Twilio"""
    if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN or not Config.TWILIO_PHONE_NUMBER:
        print("Twilio not configured. SMS not sent.")
        return False
    
    try:
        client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message,
            from_=Config.TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        return True
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False
