from website import create_app, socketio
from dotenv import load_dotenv
import os

# Load environment variables FIRST before doing anything else
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # 🚀 SECURITY FIX: Read FLASK_DEBUG from .env (Defaults to False if missing)
    # This prevents accidentally leaving debug mode ON in production!
    is_debug = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    
    # host='0.0.0.0' makes the server publicly available on our local network
    socketio.run(app, host='0.0.0.0', port=8001, debug=is_debug)