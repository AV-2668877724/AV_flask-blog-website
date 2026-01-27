from website import create_app
from dotenv import load_dotenv
import os

# Load the secrets from .env file
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' makes the server publicly available on your local network
    app.run(host='0.0.0.0', port=5000, debug=True)