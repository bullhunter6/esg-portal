/**
 * ESG Portal - Server-Sent Events (SSE) Client
 * 
 * This file provides a common interface for SSE connections
 * throughout the application.
 */

// Event source instances
let eventSource = null;
let taskEventSource = null;

// Connection status
let isConnected = false;
let isTaskConnected = false;

// Reconnection settings
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000; // 3 seconds
let reconnectAttempts = 0;

/**
 * Initialize the SSE connection for general updates
 */
function initEventSource(url = '/sse') {
    // Close existing connection if any
    if (eventSource) {
        eventSource.close();
    }
    
    try {
        // Create new EventSource
        eventSource = new EventSource(url);
        
        // Set up event handlers
        eventSource.onopen = () => {
            console.log('Connected to SSE server');
            isConnected = true;
            reconnectAttempts = 0;
            
            // Notify any listeners that we're connected
            document.dispatchEvent(new CustomEvent('sse:connected'));
        };
        
        eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            isConnected = false;
            
            // Attempt to reconnect
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
                setTimeout(() => initEventSource(url), RECONNECT_DELAY);
            } else {
                console.error('Max reconnection attempts reached');
                document.dispatchEvent(new CustomEvent('sse:max_reconnect_attempts'));
            }
            
            // Notify any listeners that we're disconnected
            document.dispatchEvent(new CustomEvent('sse:disconnected'));
        };
        
        // Handle messages
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                document.dispatchEvent(new CustomEvent('sse:message', { detail: data }));
            } catch (e) {
                console.error('Error parsing SSE message:', e);
            }
        };
        
    } catch (error) {
        console.error('Failed to initialize SSE:', error);
    }
}

/**
 * Initialize a task-specific SSE connection
 */
function initTaskEventSource(taskId) {
    // Close existing connection if any
    if (taskEventSource) {
        taskEventSource.close();
    }
    
    const url = `/sse/task/${taskId}`;
    
    try {
        // Create new EventSource
        taskEventSource = new EventSource(url);
        
        // Set up event handlers
        taskEventSource.onopen = () => {
            console.log(`Connected to task SSE for task ${taskId}`);
            isTaskConnected = true;
            
            // Notify any listeners that we're connected
            document.dispatchEvent(new CustomEvent('task:connected', { detail: { taskId } }));
        };
        
        taskEventSource.onerror = (error) => {
            console.error(`Task SSE connection error for task ${taskId}:`, error);
            isTaskConnected = false;
            
            // Notify any listeners that we're disconnected
            document.dispatchEvent(new CustomEvent('task:disconnected', { detail: { taskId } }));
            
            // Close the connection on error
            taskEventSource.close();
        };
        
        // Handle messages
        taskEventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                document.dispatchEvent(new CustomEvent('task:update', { detail: data }));
                
                // If task is complete or failed, close the connection
                if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
                    console.log(`Task ${taskId} ${data.status}, closing SSE connection`);
                    taskEventSource.close();
                    isTaskConnected = false;
                }
            } catch (e) {
                console.error('Error parsing task SSE message:', e);
            }
        };
        
    } catch (error) {
        console.error(`Failed to initialize task SSE for task ${taskId}:`, error);
    }
    
    return taskEventSource;
}

/**
 * Initialize an SSE connection for ESG score updates
 */
function initScoreEventSource(companyName) {
    const url = `/esg-scores/stream-scores/${encodeURIComponent(companyName)}`;
    
    try {
        // Create new EventSource
        const scoreEventSource = new EventSource(url);
        
        // Set up event handlers
        scoreEventSource.onopen = () => {
            console.log(`Connected to ESG score SSE for ${companyName}`);
            
            // Notify any listeners that we're connected
            document.dispatchEvent(new CustomEvent('score:connected', { detail: { companyName } }));
        };
        
        scoreEventSource.onerror = (error) => {
            console.error(`ESG score SSE connection error for ${companyName}:`, error);
            
            // Notify any listeners that we're disconnected
            document.dispatchEvent(new CustomEvent('score:disconnected', { detail: { companyName } }));
            
            // Close the connection on error
            scoreEventSource.close();
        };
        
        // Handle messages
        scoreEventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                document.dispatchEvent(new CustomEvent('score:update', { detail: data }));
            } catch (e) {
                console.error('Error parsing score SSE message:', e);
            }
        };
        
        return scoreEventSource;
    } catch (error) {
        console.error(`Failed to initialize score SSE for ${companyName}:`, error);
        return null;
    }
}

/**
 * Get the main event source instance
 */
function getEventSource() {
    return eventSource;
}

/**
 * Get the task event source instance
 */
function getTaskEventSource() {
    return taskEventSource;
}

/**
 * Check if the main SSE is connected
 */
function isEventSourceConnected() {
    return isConnected;
}

/**
 * Check if the task SSE is connected
 */
function isTaskEventSourceConnected() {
    return isTaskConnected;
}

// Initialize the event source when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize general SSE if needed
    // initEventSource();
    
    // Task-specific SSE will be initialized when needed
});

// Export functions for use in other scripts
window.initEventSource = initEventSource;
window.initTaskEventSource = initTaskEventSource;
window.initScoreEventSource = initScoreEventSource;
window.getEventSource = getEventSource;
window.getTaskEventSource = getTaskEventSource;
window.isEventSourceConnected = isEventSourceConnected;
window.isTaskEventSourceConnected = isTaskEventSourceConnected;