// API Configuration
const API_BASE_URL = '/api';

// Session management
class SessionManager {
    static getToken() {
        return localStorage.getItem('scilib_session_token');
    }
    
    static setToken(token) {
        localStorage.setItem('scilib_session_token', token);
    }
    
    static clearToken() {
        localStorage.removeItem('scilib_session_token');
    }
    
    static async login(apiKey) {
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ api_key: apiKey })
            });
            
            if (!response.ok) {
                throw new Error('Invalid API key');
            }
            
            const data = await response.json();
            this.setToken(data.session_token);
            return true;
        } catch (error) {
            this.clearToken();
            throw error;
        }
    }
}

// API Helper Functions
class API {
    static async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const token = SessionManager.getToken();
        
        if (!token) {
            throw new Error('No session token found. Please login first.');
        }
        
        const defaultOptions = {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        };

        // Merge options
        const requestOptions = {
            ...defaultOptions,
            ...options,
        };

        // Handle FormData (for file uploads)
        if (options.body instanceof FormData) {
            delete requestOptions.headers['Content-Type'];
        }

        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            // Handle 204 No Content responses
            if (response.status === 204) {
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Papers API
    static papers = {
        async list(params = {}) {
            const queryParams = new URLSearchParams(params);
            return API.request(`/papers?${queryParams}`);
        },

        async get(id) {
            return API.request(`/papers/${id}`);
        },

        async upload(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            return API.request('/papers/upload', {
                method: 'POST',
                body: formData,
            });
        },

        async update(id, data) {
            return API.request(`/papers/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        },

        async delete(id) {
            return API.request(`/papers/${id}`, {
                method: 'DELETE',
            });
        }
    };

    // Collections API
    static collections = {
        async list() {
            return API.request('/collections');
        },

        async get(id) {
            return API.request(`/collections/${id}`);
        },

        async create(data) {
            return API.request('/collections', {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },

        async update(id, data) {
            return API.request(`/collections/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        },

        async delete(id) {
            return API.request(`/collections/${id}`, {
                method: 'DELETE',
            });
        }
    };

    // Tags API
    static tags = {
        async list() {
            return API.request('/tags');
        },

        async get(id) {
            return API.request(`/tags/${id}`);
        },

        async create(data) {
            return API.request('/tags', {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },

        async update(id, data) {
            return API.request(`/tags/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        },

        async delete(id) {
            return API.request(`/tags/${id}`, {
                method: 'DELETE',
            });
        }
    };
}

// Utility Functions
const Utils = {
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    formatDateTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    truncateText(text, maxLength = 150) {
        if (text && text.length > maxLength) {
            return text.substring(0, maxLength) + '...';
        }
        return text || '';
    },

    sanitizeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};