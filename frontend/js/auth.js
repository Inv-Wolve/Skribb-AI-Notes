            localStorage.setItem(this.tokenKey, token);
        } else {
            localStorage.removeItem(this.tokenKey);
        }
    }

    // Get stored token
    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    // Get stored user data
    getUser() {
        const userData = localStorage.getItem(this.userKey);
        return userData ? JSON.parse(userData) : null;
    }

    // Store user data
    setUser(user) {
        if (user) {
            localStorage.setItem(this.userKey, JSON.stringify(user));
        } else {
            localStorage.removeItem(this.userKey);
        }
    }

    // Clear all auth data
    clearAuth() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
    }

    // Check if user is logged in
    isLoggedIn() {
        return !!(this.getToken() && this.getUser());
    }

    // Make authenticated API request
    async makeAuthenticatedRequest(endpoint, options = {}) {
        const token = this.getToken();
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` })
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, mergedOptions);
            const data = await response.json();

            // If request failed due to auth, redirect to login
            if (data.requiresAuth || (response.status === 401 && data.message === 'Authentication required')) {
                this.redirectToLogin();
                return null;
            }

            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Verify current session
    async verifySession() {
        const token = this.getToken();
        if (!token) {
            return false;
        }

        try {
            const response = await fetch(`${this.baseURL}/verify-session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            const data = await response.json();
            
            if (data.success && data.valid) {
                // Update stored user data with fresh session data
                this.setUser(data.user);
                return true;
            } else {
                // Invalid session, clear auth data
                this.clearAuth();
                return false;
            }
        } catch (error) {
            console.error('Session verification failed:', error);
            this.clearAuth();
            return false;
        }
    }

    // Get current user data from server
    async getCurrentUser() {
        try {
            const data = await this.makeAuthenticatedRequest('/me');
            if (data && data.success) {
                this.setUser(data.user);
                return data.user;
            }
            return null;
        } catch (error) {
            console.error('Failed to get current user:', error);
            return null;
        }
    }

    // Signup user
    async signup(username, email, password) {
        try {
            const response = await fetch(`${this.baseURL}/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, email, password })
            });

            const data = await response.json();
            
            if (data.success) {
                return { success: true, message: data.message };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('Signup failed:', error);
            return { success: false, message: 'Signup request failed' };
        }
    }

    // Login user
    async login(email, password) {
        try {
            const response = await fetch(`${this.baseURL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            
            if (data.success && data.token) {
                this.setToken(data.token);
                this.setUser(data.user);
                return { success: true, user: data.user };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('Login failed:', error);
            return { success: false, message: 'Login request failed' };
        }
    }

    // Google Login
    async googleLogin(credential, payload) {
        try {
            const response = await fetch(`${this.baseURL}/google-login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    credential,
                    email: payload.email,
                    name: payload.name,
                    picture: payload.picture,
                    googleId: payload.sub
                })
            });

            const data = await response.json();
            
            if (data.success && data.token) {
                this.setToken(data.token);
                this.setUser(data.user);
                return { success: true, user: data.user };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('Google Login failed:', error);
            return { success: false, message: 'Google Login request failed' };
        }
    }

    // Logout user
    async logout() {
        const token = this.getToken();
        
        try {
            // Call server logout endpoint
            if (token) {
                await fetch(`${this.baseURL}/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            }
        } catch (error) {
            console.error('Logout request failed:', error);
            // Continue with local logout even if server request fails
        }

        // Clear local auth data
        this.clearAuth();
        
        // Redirect to login page
        this.redirectToLogin();
    }

    // Redirect to login page
    redirectToLogin() {
        window.location.href = 'get-started.html#signin';
    }

    // Initialize auth on page load
    async init() {
        // If no token, user needs to login
        if (!this.isLoggedIn()) {
            // Check if this page requires authentication
            if (document.body.dataset.requiresAuth === 'true') {
                this.redirectToLogin();
            }
            return false;
        }

        // Verify session with server
        const isValid = await this.verifySession();
        
        if (!isValid) {
            // Only redirect if page requires auth
            if (document.body.dataset.requiresAuth === 'true') {
                this.redirectToLogin();
            }
            return false;
        }

        return true;
    }
}

// Create global auth manager instance
window.authManager = new AuthManager();

// Auto-initialize on DOM load for pages that need auth
document.addEventListener('DOMContentLoaded', () => {
    // Only auto-init on dashboard and other protected pages
    if (window.location.pathname.includes('dashboard.html') || 
        document.body.dataset.requiresAuth === 'true') {
        window.authManager.init();
    }
});