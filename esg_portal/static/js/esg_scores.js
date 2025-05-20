/**
 * ESG Scores - Client-side functionality
 * 
 * This file handles the display and updates of ESG scores using Server-Sent Events (SSE)
 */

// Track active SSE connections
let activeScoreEventSource = null;

// Initialize the score display
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the ESG scores page
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            // Don't prevent default form submission for initial page load
            // But set up SSE connection after the page loads
            const companyNameInput = document.getElementById('company_name');
            if (companyNameInput && companyNameInput.value) {
                // Store the company name for later use with SSE
                localStorage.setItem('lastSearchedCompany', companyNameInput.value);
            }
        });
    }

    // Check if we're on the results page
    const resultsContainer = document.getElementById('esg-results-container');
    if (resultsContainer) {
        // Get the company name from the page
        const companyNameElement = document.querySelector('.company-name');
        if (companyNameElement) {
            const companyName = companyNameElement.textContent.trim();
            if (companyName) {
                // Initialize SSE for score updates
                initializeScoreUpdates(companyName);
            }
        }
    }
});

/**
 * Initialize SSE connection for real-time score updates
 */
function initializeScoreUpdates(companyName) {
    // Close any existing connections
    if (activeScoreEventSource) {
        activeScoreEventSource.close();
    }
    
    console.log(`Initializing SSE for ${companyName} scores`);
    
    // Create new SSE connection using the function from socket.js
    if (window.initScoreEventSource) {
        activeScoreEventSource = window.initScoreEventSource(companyName);
        
        // Listen for score updates
        document.addEventListener('score:update', handleScoreUpdate);
    } else {
        console.error('initScoreEventSource function not found. Make sure socket.js is loaded before this script.');
    }
}

/**
 * Handle score update events from SSE
 */
function handleScoreUpdate(event) {
    const data = event.detail;
    console.log('Score update received:', data);
    
    if (!data || !data.source) {
        return;
    }
    
    // Update the score display
    const scoreElement = document.querySelector(`.score-value[data-source="${data.source}"]`);
    if (scoreElement) {
        // Update status classes
        if (data.status === 'fetching') {
            scoreElement.innerHTML = '<span class="loading">Loading...</span>';
            scoreElement.classList.add('loading');
            scoreElement.classList.remove('error', 'success');
        } else if (data.status === 'error') {
            scoreElement.innerHTML = `<span class="error" title="${data.message}">Error</span>`;
            scoreElement.classList.add('error');
            scoreElement.classList.remove('loading', 'success');
        } else if (data.status === 'success') {
            scoreElement.textContent = data.score;
            scoreElement.classList.add('success');
            scoreElement.classList.remove('loading', 'error');
        }
    }
    
    // Update the status message
    const statusElement = document.getElementById('search-status');
    if (statusElement) {
        if (data.status === 'fetching') {
            statusElement.textContent = `Fetching ${data.source} score...`;
            statusElement.classList.add('loading');
            statusElement.classList.remove('error', 'success');
        } else if (data.status === 'error') {
            statusElement.textContent = `Error fetching ${data.source} score: ${data.message}`;
            statusElement.classList.add('error');
            statusElement.classList.remove('loading', 'success');
        } else if (data.status === 'success') {
            statusElement.textContent = `${data.source} score updated successfully`;
            statusElement.classList.add('success');
            statusElement.classList.remove('loading', 'error');
            
            // Clear the status message after a delay
            setTimeout(() => {
                statusElement.textContent = '';
                statusElement.classList.remove('success');
            }, 3000);
        }
    }
}

/**
 * Close any active SSE connections
 */
function closeScoreConnections() {
    if (activeScoreEventSource) {
        activeScoreEventSource.close();
        activeScoreEventSource = null;
    }
}

// Clean up when navigating away
window.addEventListener('beforeunload', closeScoreConnections);
