// static/js/admin_custom.js - Enhanced functionality for Django Unfold Admin

document.addEventListener('DOMContentLoaded', function() {
    
    // Add loading states to buttons
    function addLoadingState() {
        const buttons = document.querySelectorAll('.btn-primary, .btn-success, .btn-warning, .btn-danger');
        
        buttons.forEach(button => {
            button.addEventListener('click', function() {
                if (!this.disabled) {
                    const originalText = this.innerHTML;
                    this.innerHTML = '<span class="loading-spinner"></span> Loading...';
                    this.disabled = true;
                    
                    // Re-enable after 3 seconds (adjust as needed)
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.disabled = false;
                    }, 3000);
                }
            });
        });
    }
    
    // Add animation classes to elements as they come into view
    function addScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-slide-up');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        // Observe table rows, cards, and form fields
        const elements = document.querySelectorAll('.admin-table tbody tr, .info-card, .dashboard-card, .form-row');
        elements.forEach(el => observer.observe(el));
    }
    
    // Enhanced search functionality
    function enhanceSearch() {
        const searchInputs = document.querySelectorAll('input[type="search"], input[name="q"]');
        
        searchInputs.forEach(input => {
            let searchTimeout;
            
            input.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                this.classList.add('searching');
                
                searchTimeout = setTimeout(() => {
                    this.classList.remove('searching');
                    // Add a subtle glow effect when search is complete
                    this.classList.add('search-complete');
                    setTimeout(() => this.classList.remove('search-complete'), 1000);
                }, 500);
            });
        });
    }
    
    // Status badge interactions
    function enhanceStatusBadges() {
        const statusBadges = document.querySelectorAll('[class*="bg-"][class*="text-"]');
        
        statusBadges.forEach(badge => {
            badge.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.05)';
                this.style.transition = 'transform 0.2s ease';
            });
            
            badge.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
    }
    
    // Photo preview enhancements
    function enhancePhotoPreview() {
        const photoElements = document.querySelectorAll('img[src*="bom_items"], img[src*="media"]');
        
        photoElements.forEach(img => {
            img.classList.add('photo-preview');
            
            // Add click to enlarge functionality
            img.addEventListener('click', function() {
                showImageModal(this.src, this.alt || 'Item Photo');
            });
            
            img.style.cursor = 'pointer';
        });
    }
    
    // Create image modal for enlarged view
    function showImageModal(src, title) {
        // Remove existing modal if any
        const existingModal = document.getElementById('image-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modal = document.createElement('div');
        modal.id = 'image-modal';
        modal.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
                cursor: pointer;
            ">
                <div style="
                    max-width: 90%;
                    max-height: 90%;
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                ">
                    <h3 style="
                        margin: 0 0 15px 0;
                        font-size: 1.25rem;
                        font-weight: 600;
                        color: #1f2937;
                        text-align: center;
                    ">${title}</h3>
                    <img src="${src}" style="
                        max-width: 100%;
                        max-height: 70vh;
                        border-radius: 8px;
                        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
                    " alt="${title}">
                    <p style="
                        margin: 15px 0 0 0;
                        text-align: center;
                        color: #6b7280;
                        font-size: 0.875rem;
                    ">Click anywhere to close</p>
                </div>
            </div>
        `;
        
        modal.addEventListener('click', function() {
            modal.remove();
        });
        
        document.body.appendChild(modal);
        modal.classList.add('animate-fade-scale');
    }
    
    // Progress bars animation
    function animateProgressBars() {
        const progressBars = document.querySelectorAll('.progress-fill');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const progressBar = entry.target;
                    const targetWidth = progressBar.dataset.width || '0%';
                    progressBar.style.width = '0%';
                    
                    setTimeout(() => {
                        progressBar.style.width = targetWidth;
                    }, 200);
                    
                    observer.unobserve(progressBar);
                }
            });
        });
        
        progressBars.forEach(bar => observer.observe(bar));
    }
    
    // Enhanced tooltips
    function enhanceTooltips() {
        const elements = document.querySelectorAll('[title]');
        
        elements.forEach(el => {
            const title = el.getAttribute('title');
            el.removeAttribute('title');
            el.setAttribute('data-tooltip', title);
            el.classList.add('tooltip');
        });
    }
    
    // Smooth scrolling for anchor links
    function addSmoothScrolling() {
        const anchorLinks = document.querySelectorAll('a[href^="#"]');
        
        anchorLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
    
    // Auto-refresh functionality for real-time data
    function addAutoRefresh() {
        const refreshButton = document.createElement('button');
        refreshButton.innerHTML = '🔄 Auto Refresh: OFF';
        refreshButton.className = 'btn-primary';
        refreshButton.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            padding: 10px 15px;
            font-size: 0.875rem;
            border-radius: 25px;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        `;
        
        let autoRefreshInterval;
        let isAutoRefreshOn = false;
        
        refreshButton.addEventListener('click', function() {
            if (isAutoRefreshOn) {
                clearInterval(autoRefreshInterval);
                this.innerHTML = '🔄 Auto Refresh: OFF';
                this.style.background = 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)';
                isAutoRefreshOn = false;
            } else {
                autoRefreshInterval = setInterval(() => {
                    // Only refresh if user is on a list page
                    if (window.location.pathname.includes('changelist')) {
                        window.location.reload();
                    }
                }, 30000); // Refresh every 30 seconds
                
                this.innerHTML = '🔄 Auto Refresh: ON';
                this.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                isAutoRefreshOn = true;
            }
        });
        
        // Only show on changelist pages
        if (window.location.pathname.includes('changelist')) {
            document.body.appendChild(refreshButton);
        }
    }
    
    // Form validation enhancements
    function enhanceFormValidation() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
            
            inputs.forEach(input => {
                input.addEventListener('blur', function() {
                    if (this.value.trim() === '') {
                        this.style.borderColor = '#ef4444';
                        this.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
                    } else {
                        this.style.borderColor = '#10b981';
                        this.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
                    }
                });
                
                input.addEventListener('input', function() {
                    if (this.value.trim() !== '') {
                        this.style.borderColor = '#10b981';
                        this.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
                    }
                });
            });
        });
    }
    
    // Keyboard shortcuts
    function addKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + S to save form
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                const saveButton = document.querySelector('input[name="_save"], button[name="_save"]');
                if (saveButton) {
                    e.preventDefault();
                    saveButton.click();
                    
                    // Show save indicator
                    showNotification('💾 Saving...', 'info');
                }
            }
            
            // Ctrl/Cmd + Enter to save and continue
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const saveContinueButton = document.querySelector('input[name="_continue"], button[name="_continue"]');
                if (saveContinueButton) {
                    e.preventDefault();
                    saveContinueButton.click();
                    showNotification('💾 Saving and continuing...', 'info');
                }
            }
            
            // Escape to go back
            if (e.key === 'Escape') {
                const backButton = document.querySelector('.back-button, a[href*="changelist"]');
                if (backButton) {
                    backButton.click();
                }
            }
        });
    }
    
    // Show notification system
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        const colors = {
            success: 'bg-green-100 text-green-800 border-green-200',
            error: 'bg-red-100 text-red-800 border-red-200',
            warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
            info: 'bg-blue-100 text-blue-800 border-blue-200'
        };
        
        notification.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                padding: 12px 20px;
                border-radius: 8px;
                border: 1px solid;
                font-weight: 500;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                animation: slideInUp 0.3s ease-out;
            " class="${colors[type]}">
                ${message}
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    // Statistics counter animation
    function animateCounters() {
        const counters = document.querySelectorAll('.stat-number');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const counter = entry.target;
                    const target = parseInt(counter.textContent.replace(/\D/g, ''));
                    const duration = 2000;
                    const step = target / (duration / 16);
                    let current = 0;
                    
                    const timer = setInterval(() => {
                        current += step;
                        if (current >= target) {
                            counter.textContent = target.toLocaleString();
                            clearInterval(timer);
                        } else {
                            counter.textContent = Math.floor(current).toLocaleString();
                        }
                    }, 16);
                    
                    observer.unobserve(counter);
                }
            });
        });
        
        counters.forEach(counter => observer.observe(counter));
    }
    
    // Initialize all enhancements
    function initializeEnhancements() {
        addLoadingState();
        addScrollAnimations();
        enhanceSearch();
        enhanceStatusBadges();
        enhancePhotoPreview();
        animateProgressBars();
        enhanceTooltips();
        addSmoothScrolling();
        addAutoRefresh();
        enhanceFormValidation();
        addKeyboardShortcuts();
        animateCounters();
        
        console.log('🎨 BRG Assembly Admin enhancements loaded successfully!');
    }
    
    // Initialize everything
    initializeEnhancements();
    
    // Reinitialize on AJAX content updates
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        return originalFetch.apply(this, args).then(response => {
            if (response.ok) {
                setTimeout(initializeEnhancements, 500);
            }
            return response;
        });
    };
});