from flask_socketio import SocketIO, emit
from flask import Flask, render_template, session, request

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
    return render_template('transport.html')  # Serve the HTML page


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

@socketio.on('vehicleTypeSelected')
def handle_vehicle_type(data: str):
    print(f"Vehicle Type Selected: {data}")
    # emit('vehicleTypeSelected', data, broadcast=True)

    # TODO: handle vehicle type and send response to client


@socketio.on('startLocation')
def handle_start_location(data: str):
    print(f"Start Location: {data}")
    # emit('currentLocation', data, broadcast=True)

    # TODO: handle current location and send response to client


@socketio.on('endLocation')
def handle_end_location(data: str):
    print(f"End Location: {data}")
    # emit('endLocation', data, broadcast=True)

    # TODO: handle end location and send response to client



if __name__ == '__main__':
    # Run the Flask-SocketIO server on port 8899
    socketio.run(app, host="0.0.0.0", port=8899, allow_unsafe_werkzeug=True)
