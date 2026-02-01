from website import create_app, socketio
from dotenv import load_dotenv
import os


# Load the secrets from .env file
load_dotenv()

app = create_app()


if __name__ == '__main__':
    # host='0.0.0.0' makes the server publicly available on your local network
    socketio.run(app,host='0.0.0.0', port=8000, debug=True)
