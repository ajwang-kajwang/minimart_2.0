import { io } from "socket.io-client";

// Logic: If we are on localhost, look for port 5000.
// If we are on an IP (e.g., 192.168.1.50:5173), look for 192.168.1.50:5000
const URL = `http://${window.location.hostname}:5000`;

export const socket = io(URL, {
  autoConnect: true,
  transports: ["websocket"], // Enforce websocket to avoid CORS polling errors
});

socket.on("connect", () => {
  console.log(`✅ Connected to Backend at ${URL}`);
});

socket.on("connect_error", (err) => {
  console.error(`❌ Connection Error to ${URL}:`, err.message);
});