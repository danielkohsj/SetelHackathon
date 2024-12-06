let socket;

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
    });

    socket.on('error', (error) => {
        console.error("WebSocket error:", error);
    });

    socket.on('disconnect', () => {
        console.log("WebSocket connection closed.");
    });

    socket.on('reconnect_attempt', () => {
        console.log("WebSocket reconnected.");
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

        socket.emit('startLocation', `${latitude}, ${longitude}`);
    }, (error) => {
        console.error("Error getting current location:", error);
    });
});

document.getElementById('send-start-location').addEventListener('click', () => {
    const startLocation = document.getElementById('start-location').value;
    console.log(`Start location: ${startLocation}`);
    socket.emit('startLocation', startLocation);
});

document.getElementById('send-end-location').addEventListener('click', () => {
    const endLocation = document.getElementById('end-location').value;
    console.log(`End location: ${endLocation}`);
    socket.emit('endLocation', endLocation);
});

document.getElementById("publicTransportButton").addEventListener("click", () => {
    console.log("Public Transport button clicked");
    // Redirect to transport.html when the button is clicked
    window.location.href = "transport.html";
});


// Initialize WebSocket on page load
window.addEventListener('load', () => {
    initializeWebSocket();
});
