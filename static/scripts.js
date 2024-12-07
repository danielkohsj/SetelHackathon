let socket;
let recorder;
let isRecording = false;
let audioStream;
let speechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let isSpeechRecognitionAvilable = !!speechRecognition;
let clientTrascription = false;
let finalTranscript = '';
let ttsReadSpeed = 1.0;
let voices = [];


// Function to initialize WebSocket connection
function initializeWebSocket() {
    socket = io.connect('http://localhost:8899', {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 500,
        reconnectionAttempts: 10
    });

    socket.on('connect', () => {
        speechSynthesis.cancel(); // Cancel any ongoing TTS
        console.log("WebSocket connection established.");
    });

    socket.on('error', (error) => {
        console.error("WebSocket error:", error);
    });

    socket.on('disconnect', () => {
        speechSynthesis.cancel(); // Cancel any ongoing TTS
        console.log("WebSocket connection closed.");
    });

    socket.on('reconnect_attempt', () => {
        console.log("WebSocket reconnected.");
    });

    socket.on('stt-location', (data) => {
        console.log("Location from STT:", data);
        document.getElementById('start-location').value = data.start;
        document.getElementById('end-location').value = data.end;

        // click the send-location button
        document.getElementById('send-location').click();
        // tts("You are going from " + data.start + " to " + data.end);
    });

    socket.on('response', (data) => {
        speechSynthesis.cancel(); // Cancel any ongoing TTS
        console.log("Response from server:", data);
        document.getElementById("bot-response-text-content").textContent = data.message;
        tts(data.message);
    });

    socket.on('vehicle-type', (data) => {
        console.log("Vehicle type selected:", data.vehicle);
        // document.getElementById('vehicle-type').textContent = data;
    });

    socket.on('map-updated', (data) => {
        document.getElementById('map-container').innerHTML = data.html;
    });

    socket.on('train-details', (data) => {
        console.log("Train details:", data);
        // document.getElementById('bot-response-text-content').textContent += data;
    });
}

// Get all dropdown item buttons
document.querySelectorAll('.dropdown-item').forEach(button => {
    button.addEventListener('click', (event) => {
        // Get the vehicle type from the data attribute
        const vehicleType = event.target.getAttribute('data-type');
        
        // Handle the selected vehicle type (example: send to server, update UI)
        console.log(`Selected vehicle type: ${vehicleType}`);
        socket.emit('vehicleTypeSelected', vehicleType);
    });
});

document.getElementById('current-loc-button').addEventListener('click', () => {
    // Get the current location of the user
    navigator.geolocation.getCurrentPosition((position) => {
        const { latitude, longitude } = position.coords;
        console.log(`Current location: ${latitude}, ${longitude}`);
        document.getElementById('start-location').value = `${latitude}, ${longitude}`;
        socket.emit('startLocation', `${latitude}, ${longitude}`);
    }, (error) => {
        console.error("Error getting current location:", error);
    });
});


document.getElementById('send-location').addEventListener('click', () => {
    const startLocation = document.getElementById('start-location').value;
    const endLocation = document.getElementById('end-location').value;
    console.log(`End location: ${endLocation}`);
    socket.emit('location', { start: startLocation, end: endLocation });

    if (startLocation && endLocation) {
        fetch('/map', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start: startLocation, end: endLocation })
        })
        .then(response => response.text())
        .then(htmlFragment => {
            document.getElementById('map-container').innerHTML = htmlFragment;
        })
        .catch(error => console.error('Error updating map:', error));
    } else {
        alert("Please enter both start and end locations.");
    }
});


// Function to populate voice list
function populateVoiceList() {
    voices = speechSynthesis.getVoices();
    console.log("Available voices:", voices);
}

if (typeof speechSynthesis !== 'undefined') {
    populateVoiceList();
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = populateVoiceList;
    }
}


function tts(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    let langCode = 'en';
    let matchingVoices = voices.filter(voice => voice.lang.startsWith(langCode));

    // Check if the browser is on an iOS device
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;

    if (isIOS) {
        if (matchingVoices.length === 0) {
            console.warn(`No voice found for language ${langCode}, defaulting to English.`);
            langCode = 'en';
            matchingVoices = voices.filter(voice => voice.lang.startsWith(langCode));
        }

        if (matchingVoices.length > 0) {
            utterance.voice = matchingVoices[0];
            console.log(`Using voice: ${utterance.voice.name} for language ${utterance.voice.lang}`);
        } else {
            console.warn(`No voice found for language ${langCode}, using default voice.`);
        }
    } else {
        if (langCode === 'zh') {
            langCode = 'zh-CN';
        } else if (langCode === 'ms') {
            langCode = 'ms-MY';
        } else {
            langCode = 'en-US';
        }
        
        matchingVoices = voices.filter(voice => voice.lang.startsWith(langCode));

        if (matchingVoices.length === 0) {
            console.warn(`No voice found for language ${langCode}, defaulting to English.`);
            langCode = 'en';
            matchingVoices = voices.filter(voice => voice.lang.startsWith(langCode));
        }

        if (matchingVoices.length > 0) {
            // If langCode is 'en-GB' and voices array is large enough, select index 10, otherwise just pick [0]
            if (langCode === 'en-GB' && matchingVoices[10]) {
                utterance.voice = matchingVoices[10];
            } else {
                utterance.voice = matchingVoices[0];
            }
            console.log(`Using voice: ${utterance.voice.name} for language ${utterance.voice.lang}`);
        } else {
            console.warn(`No voice found for language ${langCode}, using default voice.`);
        }
    }

    utterance.lang = langCode;
    utterance.rate = ttsReadSpeed;
    utterance.pitch = 1;

    if (isIOS) {
        // On iOS, require a user interaction to trigger TTS
        document.addEventListener('click', () => {
            speechSynthesis.speak(utterance);
        }, { once: true });
        console.log("Waiting for user interaction to trigger TTS on iOS.");
    } else {
        // For other platforms, play TTS automatically
        speechSynthesis.speak(utterance);
    }
}


// Function to get user media (microphone access)
const getUserMedia = async (constraints) => {
    if (navigator.mediaDevices) {
        return navigator.mediaDevices.getUserMedia(constraints);
    }
    let legacyApi = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia;
    if (legacyApi) {
        return new Promise((resolve, reject) => {
            legacyApi.bind(navigator)(constraints, resolve, reject);
        });
    } else {
        console.error("UserMedia API not supported.");
    }
};

// Handle recording button click
function toggleRecording() {
    if (!isRecording) {
        // Start recording
        startRecording();
    } else {
        // Stop recording
        stopRecording();
    }
}


function startRecording() {
    speechSynthesis.cancel(); // Cancel any ongoing TTS
    isRecording = true;
    finalTranscript = ''; // Reset transcript for the new recording

    getUserMedia({ audio: true })
        .then((stream) => {
            audioStream = stream;

            const options = {
                disableLogs: true,
                type: "audio",
                bufferSize: 16384,
                sampleRate: 44100,
                numberOfAudioChannels: 2,
            };

            if (/^((?!chrome|android).)*safari/i.test(navigator.userAgent)) {
                options.recorderType = RecordRTC.StereoAudioRecorder;
            }

            recorder = new RecordRTC(stream, options);
            recorder.startRecording();
            console.log("Recording started.");

            // Setup speech recognition if available and not using server-side transcription
            if (isSpeechRecognitionAvilable && !clientTrascription) {
                recognition = new speechRecognition();
                recognition.lang = 'en-US';
                recognition.interimResults = true;

                recognition.onresult = (event) => {
                    const result = event.results[0];
                    const transcript = result[0].transcript;
                    console.log("Transcript chunk:", transcript);
                    
                    // Accumulate the transcript without displaying it yet
                    finalTranscript = transcript;
                };

                recognition.onend = () => {
                    // If still recording, restart recognition for continuous capture
                    if (isRecording) {
                        recognition.start();
                    }
                };

                // Start listening for speech
                recognition.start();
            }
        })
        .catch((error) => {
            console.error("Error accessing microphone:", error);
        });
}

// Function to stop recording
function stopRecording() {
    if (recorder && isRecording) {
        isRecording = false;
        recorder.stopRecording(() => {
            const audioBlob = recorder.getBlob();
            console.log("Recording stopped. Audio Blob created.");

            if (socket && socket.connected) {
                socket.emit('audio_data', audioBlob);
                console.log("Audio Blob sent to the server.");
            }

            recorder.destroy();
            recorder = null;
            audioStream.getTracks().forEach(track => track.stop());

            // Stop speech recognition
            if (recognition) {
                recognition.stop();
                socket.emit('transcript', finalTranscript);
                console.log("Speech recognition stopped");
            }

            // Update the DOM with the full transcript
            document.getElementById('transcript').textContent = finalTranscript;
        });
    }
}

// Initialize WebSocket on page load
window.addEventListener('load', () => {
    initializeWebSocket();
});