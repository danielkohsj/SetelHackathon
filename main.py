from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_aws.chat_models import ChatBedrock
from langchain.chains.retrieval import create_retrieval_chain
from flask import Flask, render_template, session, request
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from flask_socketio import SocketIO, emit
# from dotenv import load_dotenv
# from openai import AzureOpenAI

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
    # Reset chat history for a new session
    session['chat_history'] = []  # Initialize empty chat history
    session['language'] = 'en'  # Default language is English
    return render_template('index.html')  # Serve the HTML page


@app.route('/chat')
def chat():
    """
    can create separate layout here
    """
    # Reset chat history for a new session
    session['chat_history'] = []
    session['language'] = 'en'  # Default language is English
    return render_template('index_chat.html')  # Serve the chat UI HTML page


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")




if __name__ == '__main__':
    # Run the Flask-SocketIO server on port 8899
    socketio.run(app, host="0.0.0.0", port=8899, allow_unsafe_werkzeug=True)
