let recorder;
let audioStream;
let isRecording = false;
let socket;
let ttsReadSpeed = 1.0;
let selectedLanguage = 'en'; // Default language
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
        console.log("WebSocket connection established.");
        speechSynthesis.cancel();   // Cancel any ongoing TTS
        document.getElementById('transcription').innerText = translations[selectedLanguage].initialPrompt;

        // Emit language selection to the server
        if (socket && socket.connected) {
            socket.emit('language_selected', selectedLanguage);
            console.log(`Language selected (on connect): ${selectedLanguage}`);
        }
    });

    socket.on('error', (error) => {
        console.error("WebSocket error:", error);
        alert("Error with WebSocket connection. Check server status.");

        const micIcon = document.getElementById('micIcon');
        micIcon.src = micIcon.getAttribute('neutral-src');document.getElementById('micIcon').src
    });

    socket.on('disconnect', () => {
        console.log("WebSocket connection closed.");
        speechSynthesis.cancel();   // Cancel any ongoing TTS
        const micIcon = document.getElementById('micIcon');
        micIcon.src = micIcon.getAttribute('neutral-src');
    });

    socket.on('reconnect_attempt', () => {
        console.log("WebSocket reconnected.");
        document.getElementById('transcription').innerText = "Reconnecting...";
    });

    socket.on('transcription', (data) => {
        if (data.text) {
            console.log("Received transcription:", data.text);
            document.getElementById('transcription').innerText = data.text;
        } else {
            console.log("Error in transcription:", data);
            document.getElementById('transcription').innerText = "Error processing audio data.";
        }
    });

    socket.on('prefs', (data) => {
        console.log("Received preferences:", data);

        // update language select
        const languageSelect = document.getElementById('languageSelect');
        languageSelect.value = data.language || 'en';
        selectedLanguage = data.language || 'en';

        // update tts speed
        if (data.speed === 'fast') {
            ttsReadSpeed = 1.25;
        } else if (data.speed === 'slow') {
            ttsReadSpeed = 0.75;
        } else {
            ttsReadSpeed = 1.0;
        }

        console.log("Updated preferences:", selectedLanguage, ttsReadSpeed);
        saveData(selectedLanguage, ttsReadSpeed);
    });

    socket.on('response_llm', (data) => {
        console.log(data.time_llm);
    });

    socket.on('response_db', (data) => {
        console.log(data.time_db);
    });

    socket.on('response_time_llm', (data) => {
        console.log(data.time);
    });

    socket.on('transcription_time', (data) => {
        console.log(data.time);
    });
    
    // Receive response chunks and display them incrementally
    socket.on('stream_start', (data) => {
        console.log("Streaming started:", data.message);
        const responseElement = document.getElementById('response');
        // responseElement.style.display = "none";
        responseElement.innerText = ""; // Clear old content
    });

    socket.on('streamed_output', (data) => {
        const responseElement = document.getElementById('response');
        responseElement.style.display = "block";

        // Clear content if this is the start of a new response
        // if (isRecording) {
        //     responseElement.innerText = "none"; // Clear old content
        // }

        // Append each chunk to the response text
        responseElement.innerText += data.chunk;
        console.log("Streaming chunk received:", data.chunk);
    });

    // Notify when streaming is complete
    socket.on('stream_complete', (data) => {
        console.log("Streaming complete:", data.message);
        const responseElement = document.getElementById('response');
        responseElement.style.display = "block";
    });

    // Handle streaming errors
    socket.on('stream_error', (data) => {
        console.error("Streaming error:", data.error);
        alert("There was an error processing the response. Please try again.");
    });



    socket.on('response', (data) => {
        const responseElement = document.getElementById('response');
        responseElement.innerText = data.text;
        responseElement.style.display = "block";

        const micIcon = document.getElementById('micIcon');
        micIcon.src = micIcon.getAttribute('neutral-src');
    });

    // Handling TTS for iOS and other platforms
    socket.on('tts', (data) => {
        // use polly
        // if (data.audio) {
        //     const audioBlob = new Blob([data.audio], { type: 'audio/mp3' });
        //     const audioUrl = URL.createObjectURL(audioBlob);
        //     const audio = new Audio(audioUrl);
        //     audio.play();
        // } else if (data.error) {
        //     console.error('TTS Error:', data.error);
        //     alert(data.error);
        // }

        if (data.text) {
            const utterance = new SpeechSynthesisUtterance(data.text);
            let langCode = languageMapping[selectedLanguage] || 'en';
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
                    if (langCode === 'en-GB') {
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
    });
}

// Initialize WebSocket on page load
window.addEventListener('load', () => {
    initializeWebSocket();
});
