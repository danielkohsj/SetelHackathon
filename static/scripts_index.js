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


document.getElementById("publicTransportButton").addEventListener("click", () => {
    console.log("Navigating to transport page");
    window.location.href = "/transport"; 
});

document.getElementById("homeButton").addEventListener("click", () => {
    console.log("Navigating to home page");
    window.location.href = "/index"; 
});


// Initialize WebSocket on page load
window.addEventListener('load', () => {
    initializeWebSocket();
});
