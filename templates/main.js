// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const mobileBtn = document.getElementById('mobileMenuBtn');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileBtn) {
        mobileBtn.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Add loading animation to buttons
    const buttons = document.querySelectorAll('.btn-primary, .btn-success');
    buttons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (this.classList.contains('btn-primary') || this.classList.contains('btn-success')) {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 1000);
            }
        });
    });
});

// Flash message auto-hide
setTimeout(() => {
    const flashes = document.querySelectorAll('.flash-message');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 300);
        }, 5000);
    });
}, 1000);

// Job search functionality
const searchInput = document.querySelector('input[name="search"]');
if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const value = e.target.value;
            if (value.length > 2) {
                // Implement live search
                console.log('Searching for:', value);
            }
        }, 500);
    });
}

// Save job function
function saveJob(jobId) {
    fetch(`/save/${jobId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `job_id=${jobId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Job saved successfully!', 'success');
        } else {
            showNotification('Error saving job', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error saving job', 'error');
    });
}

// Apply to job function
function applyToJob(jobId) {
    fetch(`/apply/${jobId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `job_id=${jobId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Application submitted! Good luck!', 'success');
        } else {
            showNotification('Error submitting application', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error submitting application', 'error');
    });
}

// Show notification
function showNotification(message, type) {
    const flashContainer = document.getElementById('flashContainer');
    if (!flashContainer) return;
    
    const flash = document.createElement('div');
    flash.className = `flash-message flash-${type}`;
    flash.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        ${message}
        <button class="flash-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    flashContainer.appendChild(flash);
    
    setTimeout(() => {
        flash.style.opacity = '0';
        setTimeout(() => flash.remove(), 300);
    }, 5000);
}

// Filter jobs by region
function filterByRegion(region) {
    const jobCards = document.querySelectorAll('.job-section');
    jobCards.forEach(card => {
        if (region === 'all' || card.classList.contains(region)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
    
    // Update active button state
    const buttons = document.querySelectorAll('.filter-btn');
    buttons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-region') === region) {
            btn.classList.add('active');
        }
    });
}

// Scroll to top button
const scrollBtn = document.createElement('button');
scrollBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
scrollBtn.className = 'scroll-to-top';
scrollBtn.style.cssText = `
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white;
    border: none;
    cursor: pointer;
    display: none;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    transition: all 0.3s ease;
    z-index: 1000;
`;

document.body.appendChild(scrollBtn);

scrollBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
        scrollBtn.style.display = 'flex';
    } else {
        scrollBtn.style.display = 'none';
    }
});

// Lazy load images
const images = document.querySelectorAll('img[data-src]');
const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
            imageObserver.unobserve(img);
        }
    });
});

images.forEach(img => imageObserver.observe(img));

// Form validation
const forms = document.querySelectorAll('form');
forms.forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = this.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.style.borderColor = '#ef4444';
                isValid = false;
            } else {
                field.style.borderColor = '#e2e8f0';
            }
        });
        
        if (!isValid) {
            e.preventDefault();
            showNotification('Please fill in all required fields', 'error');
        }
    });
});

// Password match validation
const passwordField = document.querySelector('input[name="password"]');
const confirmField = document.querySelector('input[name="confirm"]');

if (passwordField && confirmField) {
    function validatePasswordMatch() {
        if (passwordField.value !== confirmField.value) {
            confirmField.setCustomValidity('Passwords do not match');
            confirmField.style.borderColor = '#ef4444';
        } else {
            confirmField.setCustomValidity('');
            confirmField.style.borderColor = '#e2e8f0';
        }
    }
    
    passwordField.addEventListener('input', validatePasswordMatch);
    confirmField.addEventListener('input', validatePasswordMatch);
}

// Analytics tracking
function trackEvent(eventName, eventData = {}) {
    console.log('Event:', eventName, eventData);
    // Send to analytics service
    if (typeof gtag !== 'undefined') {
        gtag('event', eventName, eventData);
    }
}

// Track page views
trackEvent('page_view', { page: window.location.pathname });

// Track job clicks
const jobCards = document.querySelectorAll('.job-card');
jobCards.forEach(card => {
    card.addEventListener('click', () => {
        const jobTitle = card.querySelector('.job-title')?.innerText || 'Unknown';
        trackEvent('job_click', { job_title: jobTitle });
    });
});

// Copy to clipboard function
function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    showNotification('Copied to clipboard!', 'success');
}

// Share job function
function shareJob(jobTitle, jobUrl) {
    if (navigator.share) {
        navigator.share({
            title: jobTitle,
            url: jobUrl
        });
    } else {
        copyToClipboard(jobUrl);
    }
}