rama script.js


// Get all the navigation links
const navLinks = document.querySelectorAll('.nav-link');

// Add a click event listener to each link
navLinks.forEach(link => {
  link.addEventListener('click', function() {
    // Remove 'active' class from all links
    navLinks.forEach(link => link.classList.remove('active'));
    
    // Add 'active' class to the clicked link
    this.classList.add('active');
  });
});



// Severity color mapping
const severityMap = {
    "Not Suspicious Traffic": "#00ff00", // Orange
    "Misc activity": "#ff0000", // Red
    "(null)": "#f28500", // Orange
    "UNAUTHORIZED RDC": "#ff0000", // Red
    "UNKNOWN LOCATION": "#ffcc00", // Yellow
    "UNUSUAL DATA TRANSFER": "#ff0000", // Red
};

// Function to fetch logs from API
function fetchLogs() {
    fetch('/api/logs')
        .then(response => response.json())
        .then(logs => {
            console.log("Received Logs:", logs); // Debugging
            updateAlerts(logs);
        })
        .catch(error => console.error("Error fetching logs:", error));
}

// Function to update alerts on the dashboard
function updateAlerts(logs) {
    const alertsContainer = document.getElementById("alerts");
    alertsContainer.innerHTML = ""; // Clear existing alerts

    logs.forEach(log => {
        console.log("Raw Classification:", log.classification); // Debugging

        const severityColor = getSeverityColor(log.classification);
        const alertBox = document.createElement("div");
        alertBox.className = "alert-box";
        alertBox.innerHTML = `
            <div class="alert-text">
                <p class="alert-title">${log.classification || "(Unknown Alert)"}</p>
                <p class="alert-time">${log.timestamp}</p>
            </div>
            <div class="alert-status"></div>
        `;

        const alertStatus = alertBox.querySelector(".alert-status");
        alertStatus.style.backgroundColor = severityColor;

        alertsContainer.appendChild(alertBox);
    });

    document.getElementById("lastUpdatedTime").textContent = new Date().toLocaleString();
}

// Function to determine severity color
function getSeverityColor(classification) {
    if (!classification) return "#000"; // Default black if no classification

    // Normalize classification to avoid case and spacing issues
   // const normalizedClassification = classification.trim().toUpperCase();

    //console.log(`Processed Classification: ${normalizedClassification}`); // Debugging

    return severityMap[classification] || "#000"; // Default black if not found
}

// Automatically refresh logs every 5 seconds
setInterval(fetchLogs, 5000);

// Fetch logs on page load
fetchLogs();