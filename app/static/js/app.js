// Main application JavaScript
class MinutesTrackerApp {
    constructor() {
        this.socket = null;
        this.offlineEntries = JSON.parse(localStorage.getItem('offlineEntries') || '[]');
        this.init();
    }
    
    init() {
        this.initializeSocket();
        this.setupEventListeners();
        this.checkOfflineMode();
        this.initializeDarkMode();
    }
    
    initializeSocket() {
        if (typeof io !== 'undefined') {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('Connected to server');
                this.updateConnectionStatus(true);
            });
            
            this.socket.on('disconnect', () => {
                console.log('Disconnected from server');
                this.updateConnectionStatus(false);
            });
            
            this.socket.on('entry_added', (data) => {
                this.handleEntryAdded(data);
            });
        }
    }
    
    setupEventListeners() {
        // Online/Offline detection
        window.addEventListener('online', () => this.goOnline());
        window.addEventListener('offline', () => this.goOffline());
        
        // Mobile menu toggle
        const menuToggle = document.querySelector('.menu-toggle');
        if (menuToggle) {
            menuToggle.addEventListener('click', this.toggleMobileMenu);
        }
        
        // Dark mode toggle
        const darkModeToggle = document.querySelector('.dark-mode-toggle');
        if (darkModeToggle) {
            darkModeToggle.addEventListener('click', this.toggleDarkMode);
        }
        
        // Form enhancements
        this.enhanceForms();
    }
    
    enhanceForms() {
        // Add loading states to forms
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner"></span> Processing...';
                }
            });
        });
        
        // Auto-save form data in localStorage for recovery
        const formInputs = document.querySelectorAll('input, select, textarea');
        formInputs.forEach(input => {
            const storageKey = `form_${input.name}_${window.location.pathname}`;
            
            // Restore saved data
            const savedValue = localStorage.getItem(storageKey);
            if (savedValue && input.type !== 'password') {
                input.value = savedValue;
            }
            
            // Save data on change
            input.addEventListener('input', () => {
                if (input.type !== 'password') {
                    localStorage.setItem(storageKey, input.value);
                }
            });
            
            // Clear saved data on successful form submission
            input.form?.addEventListener('submit', () => {
                if (navigator.onLine) {
                    localStorage.removeItem(storageKey);
                }
            });
        });
    }
    
    updateConnectionStatus(isOnline) {
        const statusIndicator = document.querySelector('.connection-status');
        if (statusIndicator) {
            statusIndicator.classList.toggle('online', isOnline);
            statusIndicator.classList.toggle('offline', !isOnline);
        }
        
        // Show notification
        if (!isOnline) {
            this.showNotification('You are offline. Data will be saved locally.', 'warning');
        } else if (this.offlineEntries.length > 0) {
            this.syncOfflineEntries();
        }
    }
    
    goOnline() {
        console.log('Back online');
        this.updateConnectionStatus(true);
        this.syncOfflineEntries();
    }
    
    goOffline() {
        console.log('Gone offline');
        this.updateConnectionStatus(false);
        this.showNotification('You are now offline. Changes will be saved locally.', 'info');
    }
    
    checkOfflineMode() {
        this.updateConnectionStatus(navigator.onLine);
        
        // Sync any pending offline entries on page load
        if (navigator.onLine && this.offlineEntries.length > 0) {
            this.syncOfflineEntries();
        }
    }
    
    saveOfflineEntry(entryData) {
        const offlineEntry = {
            ...entryData,
            timestamp: new Date().toISOString(),
            id: 'offline_' + Date.now()
        };
        
        this.offlineEntries.push(offlineEntry);
        localStorage.setItem('offlineEntries', JSON.stringify(this.offlineEntries));
        
        this.showNotification(`Entry saved offline. ${this.offlineEntries.length} entries pending sync.`, 'info');
    }
    
    async syncOfflineEntries() {
        if (this.offlineEntries.length === 0) return;
        
        try {
            const response = await fetch('/api/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ entries: this.offlineEntries })
            });
            
            const data = await response.json();
            
            if (data.synced > 0) {
                this.offlineEntries = [];
                localStorage.removeItem('offlineEntries');
                this.showNotification(`Successfully synced ${data.synced} offline entries!`, 'success');
                
                // Refresh the page to update stats
                if (window.location.pathname === '/') {
                    this.refreshDashboardStats();
                }
            }
            
            if (data.errors > 0) {
                console.error('Sync errors:', data.error_details);
                this.showNotification(`${data.errors} entries failed to sync. Check console for details.`, 'warning');
            }
        } catch (error) {
            console.error('Sync error:', error);
            this.showNotification('Failed to sync offline entries. Will retry later.', 'error');
        }
    }
    
    async refreshDashboardStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            // Update stats on dashboard
            const todayMinutes = document.getElementById('today-minutes');
            const todayCalls = document.getElementById('today-calls');
            
            if (todayMinutes) todayMinutes.textContent = data.today_minutes;
            if (todayCalls) todayCalls.textContent = data.today_calls;
            
        } catch (error) {
            console.error('Error refreshing stats:', error);
        }
    }
    
    handleEntryAdded(data) {
        // Handle real-time entry updates
        if (window.location.pathname === '/') {
            this.refreshDashboardStats();
        }
        
        // Show notification for other users' entries (admin only)
        if (data.user_id !== parseInt(document.body.dataset.currentUserId)) {
            this.showNotification(`New entry added by ${data.entry.user_name}`, 'info');
        }
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `flash-message flash-${type}`;
        notification.textContent = message;
        
        const container = document.querySelector('.flash-messages') || document.body;
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
    
    toggleMobileMenu() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.toggle('open');
        }
    }
    
    initializeDarkMode() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
        }
    }
    
    toggleDarkMode() {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }
    
    // Utility functions
    formatDate(date) {
        return new Date(date).toLocaleDateString();
    }
    
    formatTime(time) {
        return new Date(`1970-01-01T${time}`).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    formatDuration(minutes) {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.minutesApp = new MinutesTrackerApp();
});

// Export for use in other scripts
window.MinutesTrackerApp = MinutesTrackerApp;