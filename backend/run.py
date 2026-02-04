import os
from app import create_app, socketio
from app.config import Config

app = create_app(Config)

if __name__ == '__main__':
    # Use PORT from environment or default to 5001 (5000 is often used by AirPlay on macOS)
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
