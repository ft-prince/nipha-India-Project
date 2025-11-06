// admin_custom.js - Enhanced Django Unfold Admin JavaScript

document.addEventListener('DOMContentLoaded', function() {
    'use strict';
    
    // =============================================================================
    // UTILITY FUNCTIONS
    // =============================================================================
    
    /**
     * Utility function to add event listeners safely
     */
    function addEventListenerSafe(element, event, handler) {
        if (element && typeof element.addEventListener === 'function') {
            element.addEventListener(event, handler);
        }
    }
    
    /**
     * Utility function to select elements safely
     */
    function querySelectorSafe(selector) {
        try {
            return document.querySelector(selector);
        } catch (e) {
            console.warn('Invalid selector:', selector);
            return null;
        }
    }
    
    /**
     * Utility function to select multiple elements safely
     */
    function querySelectorAllSafe(selector) {
        try {
            return document.querySelectorAll(selector);
        } catch (e) {
            console.warn('Invalid selector:', selector);
            return [];
        }
    }
    
    // =============================================================================
    // ENHANCED TABLE INTERACTIONS
    // =============================================================================
    
    /**
     * Initialize enhanced table functionality
     */
    function initializeTableEnhancements() {
        // Add hover effects to table rows
        const tableRows = querySelectorAllSafe('.admin-table tbody tr');
        tableRows.forEach(row => {
            addEventListenerSafe(row, 'mouseenter', function() {
                this.style.transform = 'scale(1.01)';
                this.style.transition = 'transform 0.2s ease';
            });
            
            addEventListenerSafe(row, 'mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
        
        // Make table rows clickable if they contain links
        tableRows.forEach(row => {
            const firstLink = row.querySelector('a');
            if (firstLink) {
                addEventListenerSafe(row, 'click', function(e) {
                    // Only navigate if user didn't click on a specific interactive element
                    if (!e.target.matches('a, button, input, select, textarea')) {
                        window.location.href = firstLink.href;
                    }
                });
                row.style.cursor = 'pointer';
            }
        });
    }
    
    // =============================================================================
    // FORM ENHANCEMENTS
    // =============================================================================
    
    /**
     * Initialize form enhancements
     */
    function initializeFormEnhancements() {
        // Add floating label effect
        const formInputs = querySelectorAllSafe('.form-control');
        formInputs.forEach(input => {
            addEventListenerSafe(input, 'focus', function() {
                this.parentNode.classList.add('focused');
            });
            
            addEventListenerSafe(input, 'blur', function() {
                if (!this.value) {
                    this.parentNode.classList.remove('focused');
                }
            });
            
            // Check if input has value on load
            if (input.value) {
                input.parentNode.classList.add('focused');
            }
        });
        
        // Add form validation styling
        const forms = querySelectorAllSafe('form');
        forms.forEach(form => {
            addEventListenerSafe(form, 'submit', function(e) {
                const requiredFields = this.querySelectorAll('[required]');
                let hasErrors = false;
                
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        field.classList.add('error');
                        hasErrors = true;
                    } else {
                        field.classList.remove('error');
                    }
                });
                
                if (hasErrors) {
                    e.preventDefault();
                    showNotification('Please fill in all required fields', 'error');
                }
            });
        });
    }
    
    // =============================================================================
    // FILE UPLOAD ENHANCEMENTS
    // =============================================================================
    
    /**
     * Initialize file upload enhancements
     */
    function initializeFileUploadEnhancements() {
        const fileInputs = querySelectorAllSafe('input[type="file"]');
        
        fileInputs.forEach(input => {
            const uploadArea = input.closest('.file-upload-area') || input.parentNode;
            
            // Add drag and drop functionality
            addEventListenerSafe(uploadArea, 'dragover', function(e) {
                e.preventDefault();
                this.classList.add('dragover');
            });
            
            addEventListenerSafe(uploadArea, 'dragleave', function(e) {
                e.preventDefault();
                this.classList.remove('dragover');
            });
            
            addEventListenerSafe(uploadArea, 'drop', function(e) {
                e.preventDefault();
                this.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    input.files = files;
                    handleFileSelection(input, files[0]);
                }
            });
            
            // Handle file selection
            addEventListenerSafe(input, 'change', function() {
                if (this.files.length > 0) {
                    handleFileSelection(this, this.files[0]);
                }
            });
        });
    }
    
    /**
     * Handle file selection and preview
     */
    function handleFileSelection(input, file) {
        const previewContainer = input.parentNode.querySelector('.file-preview') || 
                               input.parentNode.querySelector('.media-preview');
        
        if (previewContainer) {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewContainer.innerHTML = `<img src="${e.target.result}" alt="Preview" style="max-width: 200px; max-height: 200px; border-radius: 0.5rem;">`;
                };
                reader.readAsDataURL(file);
            } else if (file.type.startsWith('video/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewContainer.innerHTML = `<video src="${e.target.result}" controls style="max-width: 200px; max-height: 200px; border-radius: 0.5rem;"></video>`;
                };
                reader.readAsDataURL(file);
            } else {
                previewContainer.innerHTML = `<div class="file-info">📄 ${file.name}</div>`;
            }
        }
        
        // Show file name
        const fileNameDisplay = input.parentNode.querySelector('.file-name');
        if (fileNameDisplay) {
            fileNameDisplay.textContent = file.name;
        }
    }
    
    // =============================================================================
    // COLLAPSIBLE SECTIONS
    // =============================================================================
    
    /**
     * Initialize collapsible sections
     */
    function initializeCollapsibleSections() {
        const toggles = querySelectorAllSafe('.collapse-toggle');
        
        toggles.forEach(toggle => {
            addEventListenerSafe(toggle, 'click', function() {
                const content = this.nextElementSibling;
                if (content && content.classList.contains('collapse-content')) {
                    const isOpen = content.classList.contains('show');
                    
                    if (isOpen) {
                        content.classList.remove('show');
                        this.classList.remove('active');
                    } else {
                        content.classList.add('show');
                        this.classList.add('active');
                    }
                }
            });
        });
        
        // Handle Django admin fieldset collapsing
        const fieldsetToggles = querySelectorAllSafe('.collapse');
        fieldsetToggles.forEach(fieldset => {
            const header = fieldset.querySelector('h2') || fieldset.querySelector('.fieldset-header');
            if (header) {
                header.style.cursor = 'pointer';
                addEventListenerSafe(header, 'click', function() {
                    fieldset.classList.toggle('collapsed');
                });
            }
        });
    }
    
    // =============================================================================
    // SEARCH AND FILTER ENHANCEMENTS
    // =============================================================================
    
    /**
     * Initialize search and filter functionality
     */
    function initializeSearchAndFilters() {
        // Add real-time search functionality
        const searchInputs = querySelectorAllSafe('.search-input, #searchbar');
        searchInputs.forEach(input => {
            let searchTimeout;
            
            addEventListenerSafe(input, 'input', function() {
                clearTimeout(searchTimeout);
                const searchTerm = this.value.toLowerCase();
                
                searchTimeout = setTimeout(() => {
                    filterTableRows(searchTerm);
                }, 300);
            });
        });
        
        // Add filter functionality
        const filterSelects = querySelectorAllSafe('.filter-select');
        filterSelects.forEach(select => {
            addEventListenerSafe(select, 'change', function() {
                applyFilters();
            });
        });
    }
    
    /**
     * Filter table rows based on search term
     */
    function filterTableRows(searchTerm) {
        const tableRows = querySelectorAllSafe('.admin-table tbody tr');
        let visibleCount = 0;
        
        tableRows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const isVisible = text.includes(searchTerm);
            
            if (isVisible) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });
        
        // Update results count
        const resultsCount = querySelectorSafe('.results-count');
        if (resultsCount) {
            resultsCount.textContent = `${visibleCount} results found`;
        }
    }
    
    /**
     * Apply multiple filters
     */
    function applyFilters() {
        const filters = {};
        const filterSelects = querySelectorAllSafe('.filter-select');
        
        filterSelects.forEach(select => {
            if (select.value) {
                filters[select.name] = select.value;
            }
        });
        
        const tableRows = querySelectorAllSafe('.admin-table tbody tr');
        tableRows.forEach(row => {
            let shouldShow = true;
            
            Object.keys(filters).forEach(filterName => {
                const cell = row.querySelector(`[data-filter="${filterName}"]`);
                if (cell && cell.textContent.toLowerCase() !== filters[filterName].toLowerCase()) {
                    shouldShow = false;
                }
            });
            
            row.style.display = shouldShow ? '' : 'none';
        });
    }
    
    // =============================================================================
    // NOTIFICATION SYSTEM
    // =============================================================================
    
    /**
     * Show notification message
     */
    function showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close" aria-label="Close">&times;</button>
            </div>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            padding: 1rem;
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
            z-index: 10000;
            min-width: 300px;
            animation: slideInRight 0.3s ease;
        `;
        
        // Add type-specific styling
        if (type === 'error') {
            notification.style.borderColor = '#ef4444';
            notification.style.backgroundColor = '#fef2f2';
        } else if (type === 'success') {
            notification.style.borderColor = '#10b981';
            notification.style.backgroundColor = '#f0fdf4';
        } else if (type === 'warning') {
            notification.style.borderColor = '#f59e0b';
            notification.style.backgroundColor = '#fffbeb';
        }
        
        document.body.appendChild(notification);
        
        // Add close functionality
        const closeButton = notification.querySelector('.notification-close');
        addEventListenerSafe(closeButton, 'click', function() {
            removeNotification(notification);
        });
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                removeNotification(notification);
            }, duration);
        }
        
        return notification;
    }
    
    /**
     * Remove notification
     */
    function removeNotification(notification) {
        if (notification && notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }
    
    // =============================================================================
    // LOADING STATES
    // =============================================================================
    
    /**
     * Show loading state
     */
    function showLoading(element, text = 'Loading...') {
        if (!element) return;
        
        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <span class="loading-text">${text}</span>
            </div>
        `;
        
        loader.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        `;
        
        element.style.position = 'relative';
        element.appendChild(loader);
        
        return loader;
    }
    
    /**
     * Hide loading state
     */
    function hideLoading(element) {
        if (!element) return;
        
        const loader = element.querySelector('.loading-overlay');
        if (loader) {
            loader.remove();
        }
    }
    
    // =============================================================================
    // AJAX FORM HANDLING
    // =============================================================================
    
    /**
     * Initialize AJAX form handling
     */
    function initializeAjaxForms() {
        const ajaxForms = querySelectorAllSafe('form[data-ajax="true"]');
        
        ajaxForms.forEach(form => {
            addEventListenerSafe(form, 'submit', function(e) {
                e.preventDefault();
                submitFormAjax(this);
            });
        });
    }
    
    /**
     * Submit form via AJAX
     */
    function submitFormAjax(form) {
        const formData = new FormData(form);
        const loader = showLoading(form);
        
        fetch(form.action || window.location.href, {
            method: form.method || 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Network response was not ok');
        })
        .then(data => {
            hideLoading(form);
            
            if (data.success) {
                showNotification(data.message || 'Operation successful', 'success');
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } else {
                showNotification(data.message || 'Operation failed', 'error');
            }
        })
        .catch(error => {
            hideLoading(form);
            showNotification('An error occurred. Please try again.', 'error');
            console.error('Form submission error:', error);
        });
    }
    
    // =============================================================================
    // KEYBOARD SHORTCUTS
    // =============================================================================
    
    /**
     * Initialize keyboard shortcuts
     */
    function initializeKeyboardShortcuts() {
        addEventListenerSafe(document, 'keydown', function(e) {
            // Ctrl/Cmd + S to save form
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                const saveButton = querySelectorSafe('input[type="submit"], button[type="submit"]');
                if (saveButton) {
                    saveButton.click();
                    showNotification('Form saved', 'success', 2000);
                }
            }
            
            // Escape to close modals/notifications
            if (e.key === 'Escape') {
                const notifications = querySelectorAllSafe('.notification');
                notifications.forEach(notification => {
                    removeNotification(notification);
                });
                
                const modals = querySelectorAllSafe('.modal.show');
                modals.forEach(modal => {
                    modal.classList.remove('show');
                });
            }
            
            // Ctrl/Cmd + F to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                const searchInput = querySelectorSafe('.search-input, #searchbar');
                if (searchInput) {
                    e.preventDefault();
                    searchInput.focus();
                }
            }
        });
    }
    
    // =============================================================================
    // PROGRESS TRACKING
    // =============================================================================
    
    /**
     * Update progress bars
     */
    function updateProgressBars() {
        const progressBars = querySelectorAllSafe('.progress-bar');
        
        progressBars.forEach(progressBar => {
            const progress = progressBar.getAttribute('data-progress');
            const progressFill = progressBar.querySelector('.progress-fill');
            
            if (progressFill && progress) {
                progressFill.style.width = `${progress}%`;
            }
        });
    }
    
    /**
     * Animate counters
     */
    function animateCounters() {
        const counters = querySelectorAllSafe('[data-counter]');
        
        counters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-counter'));
            const duration = 2000; // 2 seconds
            const start = performance.now();
            
            function updateCounter(currentTime) {
                const elapsed = currentTime - start;
                const progress = Math.min(elapsed / duration, 1);
                const current = Math.floor(progress * target);
                
                counter.textContent = current;
                
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                }
            }
            
            requestAnimationFrame(updateCounter);
        });
    }
    
    // =============================================================================
    // DATA TABLE ENHANCEMENTS
    // =============================================================================
    
    /**
     * Initialize sortable tables
     */
    function initializeSortableTables() {
        const sortableHeaders = querySelectorAllSafe('th[data-sortable="true"]');
        
        sortableHeaders.forEach(header => {
            header.style.cursor = 'pointer';
            header.innerHTML += ' <span class="sort-indicator">↕️</span>';
            
            addEventListenerSafe(header, 'click', function() {
                sortTable(this);
            });
        });
    }
    
    /**
     * Sort table by column
     */
    function sortTable(header) {
        const table = header.closest('table');
        const columnIndex = Array.from(header.parentNode.children).indexOf(header);
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        const isAscending = header.classList.contains('sort-asc');
        const isDescending = header.classList.contains('sort-desc');
        
        // Remove sorting classes from all headers
        const allHeaders = table.querySelectorAll('th');
        allHeaders.forEach(h => {
            h.classList.remove('sort-asc', 'sort-desc');
            const indicator = h.querySelector('.sort-indicator');
            if (indicator) {
                indicator.textContent = '↕️';
            }
        });
        
        // Determine sort direction
        let sortDirection = 'asc';
        if (isAscending) {
            sortDirection = 'desc';
        }
        
        // Sort rows
        rows.sort((a, b) => {
            const aValue = a.children[columnIndex].textContent.trim();
            const bValue = b.children[columnIndex].textContent.trim();
            
            // Try to parse as numbers
            const aNum = parseFloat(aValue.replace(/[^\d.-]/g, ''));
            const bNum = parseFloat(bValue.replace(/[^\d.-]/g, ''));
            
            let comparison = 0;
            if (!isNaN(aNum) && !isNaN(bNum)) {
                comparison = aNum - bNum;
            } else {
                comparison = aValue.localeCompare(bValue);
            }
            
            return sortDirection === 'asc' ? comparison : -comparison;
        });
        
        // Update header classes and indicator
        header.classList.add(`sort-${sortDirection}`);
        const indicator = header.querySelector('.sort-indicator');
        if (indicator) {
            indicator.textContent = sortDirection === 'asc' ? '↑' : '↓';
        }
        
        // Reorder rows in DOM
        rows.forEach(row => tbody.appendChild(row));
    }
    
    // =============================================================================
    // INITIALIZATION AND ERROR HANDLING
    // =============================================================================
    
    /**
     * Initialize all components
     */
    function initializeAll() {
        try {
            console.log('Initializing admin enhancements...');
            
            initializeTableEnhancements();
            initializeFormEnhancements();
            initializeFileUploadEnhancements();
            initializeCollapsibleSections();
            initializeSearchAndFilters();
            initializeAjaxForms();
            initializeKeyboardShortcuts();
            initializeSortableTables();
            
            updateProgressBars();
            animateCounters();
            
            // Add CSS animations
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                
                .form-control.error {
                    border-color: #ef4444 !important;
                    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
                }
                
                .notification-content {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                
                .notification-close {
                    background: none;
                    border: none;
                    font-size: 1.5rem;
                    cursor: pointer;
                    padding: 0;
                    margin-left: 1rem;
                }
                
                .loading-content {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 1rem;
                }
                
                .loading-text {
                    color: #6b7280;
                    font-weight: 500;
                }
                
                th.sort-asc,
                th.sort-desc {
                    background-color: #f3f4f6;
                }
                
                .sort-indicator {
                    font-size: 0.875rem;
                    margin-left: 0.5rem;
                }
            `;
            document.head.appendChild(style);
            
            console.log('Admin enhancements initialized successfully');
            
        } catch (error) {
            console.error('Error initializing admin enhancements:', error);
        }
    }
    
    /**
     * Global error handler
     */
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        showNotification('An unexpected error occurred', 'error');
    });
    
    /**
     * Global unhandled promise rejection handler
     */
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Unhandled promise rejection:', e.reason);
        showNotification('An error occurred while processing your request', 'error');
    });
    
    // =============================================================================
    // EXPOSE PUBLIC API
    // =============================================================================
    
    // Expose useful functions globally for use in Django templates
    window.AdminEnhancements = {
        showNotification,
        showLoading,
        hideLoading,
        updateProgressBars,
        animateCounters,
        filterTableRows,
        applyFilters
    };
    
    // Initialize everything
    initializeAll();
    
    console.log('Django Unfold Admin Enhancements loaded successfully');
});

// =============================================================================
// ADDITIONAL UTILITIES FOR DJANGO INTEGRATION
// =============================================================================

/**
 * Django CSRF token handling
 */
function getCSRFToken() {
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrf ? csrf.value : '';
}

/**
 * Add CSRF token to all AJAX requests
 */
if (window.fetch) {
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        if (args[1] && (args[1].method === 'POST' || args[1].method === 'PUT' || args[1].method === 'PATCH')) {
            args[1].headers = args[1].headers || {};
            if (!args[1].headers['X-CSRFToken']) {
                args[1].headers['X-CSRFToken'] = getCSRFToken();
            }
        }
        return originalFetch.apply(this, args);
    };
}

/**
 * Helper function for Django admin integration
 */
function initializeDjangoAdminFeatures() {
    // Handle Django admin inline forms
    const inlineGroups = document.querySelectorAll('.inline-group');
    inlineGroups.forEach(group => {
        const addButton = group.querySelector('.add-row a');
        if (addButton) {
            addButton.addEventListener('click', function() {
                setTimeout(() => {
                    // Re-initialize enhancements for new rows
                    initializeFormEnhancements();
                    initializeFileUploadEnhancements();
                }, 100);
            });
        }
    });
    
    // Handle Django admin filter sidebar
    const filterSidebar = document.querySelector('#changelist-filter');
    if (filterSidebar) {
        filterSidebar.addEventListener('change', function() {
            const loader = showLoading(document.querySelector('#result_list'));
            // Hide loader after a short delay (Django will handle the actual filtering)
            setTimeout(() => hideLoading(document.querySelector('#result_list')), 1000);
        });
    }
}

// Initialize Django-specific features
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initializeDjangoAdminFeatures, 500);
});