/**
 * ESG News Portal - Like Functionality
 * Optimized to reduce API calls and improve performance
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize like functionality
    initLikes();
    
    // Handle unlike buttons on dashboard
    initDashboardUnlikeButtons();
});

function initLikes() {
    // Get all like buttons
    const likeButtons = document.querySelectorAll('.like-btn');
    if (likeButtons.length === 0) {
        // If no like buttons (user not authenticated), just update counts
        updateLikeCountsForNonAuth();
        return;
    }
    
    // Collect all content IDs grouped by type
    const contentItems = [];
    likeButtons.forEach(btn => {
        const contentType = btn.dataset.type;
        const contentId = btn.dataset.id;
        if (contentType && contentId) {
            contentItems.push(`${contentType}:${contentId}`);
        }
    });
    
    if (contentItems.length === 0) return;
    
    // Fetch like status for all items in a single request
    fetchLikeStatus(contentItems.join(','))
        .then(data => {
            if (data.success) {
                // Update like buttons
                likeButtons.forEach(btn => {
                    const contentType = btn.dataset.type;
                    const contentId = btn.dataset.id;
                    const item = data.items[`${contentType}:${contentId}`];
                    
                    if (item) {
                        // Update like count
                        const countElement = btn.querySelector('.like-count');
                        if (countElement) {
                            countElement.textContent = item.like_count;
                        }
                        
                        // Update button state if liked - Supporting multiple CSS class patterns
                        if (item.is_liked) {
                            // Support different class patterns used across templates
                            btn.classList.add('liked');
                            btn.classList.add('text-danger');
                            
                            // For article detail page style
                            if (btn.classList.contains('btn-outline-danger')) {
                                btn.classList.remove('btn-outline-danger');
                                btn.classList.add('btn-danger');
                                
                                // Update text if it exists
                                const textElement = btn.querySelector('#likeText');
                                if (textElement) {
                                    textElement.textContent = 'Liked';
                                }
                            }
                            
                            const iconElement = btn.querySelector('i');
                            if (iconElement) {
                                iconElement.classList.remove('far');
                                iconElement.classList.add('fas');
                            }
                        }
                    }
                });
                
                // Add click handlers for like buttons
                addLikeButtonHandlers(likeButtons);
            }
        })
        .catch(error => console.error('Error fetching like status:', error));
}

function initDashboardUnlikeButtons() {
    // Handle unlike buttons in dashboard
    const unlikeBtns = document.querySelectorAll('.unlike-btn');
    if (unlikeBtns.length === 0) return;
    
    unlikeBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const contentType = this.dataset.type;
            const contentId = this.dataset.id;
            
            // Disable button temporarily to prevent multiple clicks
            this.disabled = true;
            
            toggleLike(contentType, contentId)
                .then(data => {
                    if (data.success) {
                        // Remove the parent element (the whole liked item)
                        const parentCol = this.closest('.col-md-6');
                        if (parentCol) {
                            parentCol.remove();
                        }
                        
                        // Update the like count in the stats
                        const statValue = document.querySelector(`.stat-value:nth-child(1):has(+ .stat-label:contains('${contentType.charAt(0).toUpperCase() + contentType.slice(1)}s Liked'))`);
                        if (!statValue) {
                            // Fallback if the :has selector isn't supported
                            const statElements = document.querySelectorAll('.stat-value');
                            statElements.forEach(element => {
                                const label = element.nextElementSibling;
                                if (label && label.textContent.includes(`${contentType.charAt(0).toUpperCase() + contentType.slice(1)}s Liked`)) {
                                    element.textContent = parseInt(element.textContent) - 1;
                                }
                            });
                        } else {
                            statValue.textContent = parseInt(statValue.textContent) - 1;
                        }
                        
                        // Check if there are no more items in this category
                        const cardBody = parentCol ? parentCol.closest('.card-body') : null;
                        if (cardBody && cardBody.querySelectorAll('.col-md-6').length === 0) {
                            // Find the parent card and remove it
                            const card = cardBody.closest('.card.shadow-sm');
                            if (card) {
                                card.remove();
                            }
                            
                            // Check if there are no more liked content at all
                            const allCards = document.querySelectorAll('.card.shadow-sm.mb-4');
                            if (allCards.length === 0) {
                                // Show the "no liked content" message
                                const container = document.querySelector('.container.py-4');
                                if (container) {
                                    const noContentAlert = document.createElement('div');
                                    noContentAlert.className = 'alert alert-info';
                                    noContentAlert.innerHTML = '<i class="fas fa-info-circle me-2"></i>You haven\'t liked any content yet. Browse articles, events, and publications and click the heart icon to like them.';
                                    container.appendChild(noContentAlert);
                                }
                            }
                        }
                    }
                    
                    // Re-enable button
                    this.disabled = false;
                })
                .catch(error => {
                    console.error('Error toggling like:', error);
                    this.disabled = false;
                });
        });
    });
}

function updateLikeCountsForNonAuth() {
    // Get all cards with data-id attributes
    const contentCards = document.querySelectorAll('[data-id]');
    if (contentCards.length === 0) return;
    
    // Determine content type from page URL or data attributes
    let contentType = 'article'; // Default
    const path = window.location.pathname;
    if (path.includes('events')) {
        contentType = 'event';
    } else if (path.includes('publications')) {
        contentType = 'publication';
    }
    
    // Collect all content IDs
    const contentItems = [];
    contentCards.forEach(card => {
        const contentId = card.dataset.id;
        if (contentId) {
            contentItems.push(`${contentType}:${contentId}`);
        }
    });
    
    if (contentItems.length === 0) return;
    
    // Fetch like counts for all items
    fetchLikeStatus(contentItems.join(','))
        .then(data => {
            if (data.success) {
                // Update like counts
                contentCards.forEach(card => {
                    const contentId = card.dataset.id;
                    if (contentId) {
                        const item = data.items[`${contentType}:${contentId}`];
                        if (item) {
                            const countElement = card.querySelector('.like-count');
                            if (countElement) {
                                countElement.textContent = item.like_count;
                            }
                        }
                    }
                });
            }
        })
        .catch(error => console.error('Error fetching like counts:', error));
}

function addLikeButtonHandlers(buttons) {
    buttons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation(); // Prevent triggering card links
            
            const contentType = this.dataset.type;
            const contentId = this.dataset.id;
            
            // Disable button temporarily to prevent multiple clicks
            this.disabled = true;
            
            toggleLike(contentType, contentId)
                .then(data => {
                    if (data.success) {
                        // Update like count
                        const countElement = this.querySelector('.like-count');
                        if (countElement) {
                            countElement.textContent = data.like_count;
                        }
                        
                        // Update button state - Support multiple different CSS class patterns
                        const iconElement = this.querySelector('i');
                        
                        if (data.is_liked) {
                            // Liked state - support all class patterns used in different templates
                            this.classList.add('liked');
                            this.classList.add('text-danger');
                            
                            // For article detail page style
                            if (this.classList.contains('btn-outline-danger')) {
                                this.classList.remove('btn-outline-danger');
                                this.classList.add('btn-danger');
                                
                                // Update text if it exists
                                const textElement = this.querySelector('#likeText');
                                if (textElement) {
                                    textElement.textContent = 'Liked';
                                }
                            }
                            
                            if (iconElement) {
                                iconElement.classList.remove('far');
                                iconElement.classList.add('fas');
                            }
                        } else {
                            // Unliked state
                            this.classList.remove('liked');
                            this.classList.remove('text-danger');
                            
                            // For article detail page style
                            if (this.classList.contains('btn-danger')) {
                                this.classList.remove('btn-danger');
                                this.classList.add('btn-outline-danger');
                                
                                // Update text if it exists
                                const textElement = this.querySelector('#likeText');
                                if (textElement) {
                                    textElement.textContent = 'Like';
                                }
                            }
                            
                            if (iconElement) {
                                iconElement.classList.remove('fas');
                                iconElement.classList.add('far');
                            }
                        }
                    }
                    
                    // Re-enable button
                    this.disabled = false;
                })
                .catch(error => {
                    console.error('Error toggling like:', error);
                    this.disabled = false;
                });
        });
    });
}

// API functions with caching
const likeStatusCache = new Map();

async function fetchLikeStatus(items) {
    // Check cache first
    if (likeStatusCache.has(items)) {
        return likeStatusCache.get(items);
    }
    
    try {
        const response = await fetch(`/api/likes/status?items=${items}`);
        const data = await response.json();
        
        // Cache the result (for 30 seconds)
        likeStatusCache.set(items, data);
        setTimeout(() => likeStatusCache.delete(items), 30000);
        
        return data;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

async function toggleLike(contentType, contentId) {
    try {
        const response = await fetch(`/api/like/${contentType}/${contentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        const data = await response.json();
        
        // Clear cache for this item
        likeStatusCache.clear();
        
        return data;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}