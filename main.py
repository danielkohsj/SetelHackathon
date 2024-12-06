from flask_socketio import SocketIO, emit
# from dotenv import load_dotenv

import os
import re
import time
import json
import requests



# Load environment variables from .env file
# load_dotenv()

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")  # Set a secret key for session management
socketio = SocketIO(app, ping_interval=25, ping_timeout=70, cors_allowed_origins="*", engineio_logger=True, logger=True, max_http_buffer_size=15000000)  # max limit 85 secs



@app.route('/')
def index():
    """
    Serve the main HTML page and reset the chat history for a new session.
    """
    return render_template('index.html')  # Serve the HTML page


@app.route('/chat')
def chat():
    """
    can create separate layout here
    """
    pass


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")




if __name__ == '__main__':
    # Run the Flask-SocketIO server on port 8899
    socketio.run(app, host="0.0.0.0", port=8899, allow_unsafe_werkzeug=True)
