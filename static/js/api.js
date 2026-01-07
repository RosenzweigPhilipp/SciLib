// API Configuration
const API_BASE_URL = '/api';

// Simple API key management
class ApiKeyManager {
    static getApiKey() {
        return localStorage.getItem('scilib_api_key');
    }
    
    static setApiKey(apiKey) {
        // Trim whitespace and sanitize
        const sanitized = apiKey ? apiKey.trim() : '';
        localStorage.setItem('scilib_api_key', sanitized);
    }
    
    static clearApiKey() {
        localStorage.removeItem('scilib_api_key');
    }
}

// API Helper Functions
class API {
    static async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        let apiKey = ApiKeyManager.getApiKey();
        
        console.log(`DEBUG: Making request to ${url}`);
        console.log(`DEBUG: API key from localStorage: ${apiKey ? apiKey.substring(0, 10) + '...' : 'null'}`);
        
        if (!apiKey) {
            throw new Error('API key required. Please set your API key first.');
        }
        
        // Sanitize API key - trim whitespace and ensure only ASCII characters
        apiKey = apiKey.trim();
        // Check if API key contains only valid characters (alphanumeric and common symbols)
        if (!/^[a-zA-Z0-9\-_]+$/.test(apiKey)) {
            console.error('DEBUG: API key contains invalid characters:', apiKey);
            throw new Error('API key contains invalid characters. Please re-enter your API key.');
        }
        
        const defaultOptions = {
            headers: {
                'X-API-Key': apiKey,
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

        console.log('DEBUG: Final request options:', {
            ...requestOptions,
            headers: { ...requestOptions.headers, 'X-API-Key': requestOptions.headers['X-API-Key'] ? requestOptions.headers['X-API-Key'].substring(0, 10) + '...' : 'missing' }
        });

        try {
            const response = await fetch(url, requestOptions);
            
            console.log(`DEBUG: Response status: ${response.status}`);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error(`DEBUG: Error response:`, errorData);
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
        async reExtract(paperId, useLLM = true) {
            return await API.request(`/papers/${paperId}/re-extract`, {
                method: 'POST',
                body: JSON.stringify({ use_llm: useLLM })
            });
        },
        
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

        async uploadBatch(files) {
            const formData = new FormData();
            for (const file of files) {
                formData.append('files', file);
            }
            
            return API.request('/papers/upload-batch', {
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
        },

        async clear() {
            return API.request('/papers/clear-all', { method: 'DELETE' });
        },
        
        async clearDatabase() {
            return API.request('/papers/clear-database', { method: 'DELETE' });
        }
    };

    // AI API
    static ai = {
        async getTaskStatus(taskId) {
            return API.request(`/ai/status/${taskId}`);
        },
        
        // Summaries (in papers API)
        async generateSummary(paperId) {
            return API.request(`/papers/${paperId}/summarize`, { 
                method: 'POST',
                body: JSON.stringify({ force_regenerate: false })
            });
        },
        
        async getSummary(paperId) {
            return API.request(`/papers/${paperId}/summary`);
        },

        async getTaskStatus(taskId) {
            return API.request(`/ai/status/${taskId}`);
        },
        
        // Recommendations (in papers API)
        async getRecommendations(paperId, limit = 5) {
            return API.request(`/papers/${paperId}/recommendations?limit=${limit}`);
        },
        
        // Search (search API)
        async semanticSearch(query, limit = 10, searchType = 'hybrid') {
            return API.request('/search', {
                method: 'POST',
                body: JSON.stringify({
                    query: query,
                    limit: limit,
                    mode: searchType,
                    semantic_weight: 0.7,
                    keyword_weight: 0.3
                })
            });
        },
        
        // External Discovery (discover API)
        async discoverPapers(query, limit = 10) {
            return API.request(`/discover/search?query=${encodeURIComponent(query)}&limit=${limit}`);
        },
        
        async addDiscoveredPaper(paperData) {
            return API.request('/discover/add', {
                method: 'POST',
                body: JSON.stringify(paperData)
            });
        }
    };
    
    // Citations API
    static citations = {
        async getPaperCitations(paperId) {
            return API.request(`/citations/paper/${paperId}`);
        },
        
        async addCitation(citingPaperId, citedPaperId, context = null) {
            return API.request('/citations/add', {
                method: 'POST',
                body: JSON.stringify({ citing_paper_id: citingPaperId, cited_paper_id: citedPaperId, context })
            });
        },
        
        async removeCitation(citingPaperId, citedPaperId) {
            return API.request(`/citations/${citingPaperId}/${citedPaperId}`, { method: 'DELETE' });
        },
        
        async calculateInfluence(paperId) {
            return API.request(`/citations/paper/${paperId}/calculate-influence`, { method: 'POST' });
        },
        
        async fetchExternalCitations(paperId) {
            return API.request(`/citations/paper/${paperId}/fetch-external`, { method: 'POST' });
        },
        
        async getInfluentialPapers(limit = 10) {
            return API.request(`/citations/influential?limit=${limit}`);
        },
        
        async getMostCited(limit = 10) {
            return API.request(`/citations/most-cited?limit=${limit}`);
        },
        
        async getNetwork() {
            return API.request('/citations/network');
        },
        
        async getClusters() {
            return API.request('/citations/clusters');
        },
        
        async getStats() {
            return API.request('/citations/stats');
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
    },

    formatAuthors(authors, maxAuthors = 3) {
        if (!authors) return '';
        
        // Split authors by common delimiters
        const authorList = authors.split(/[;,]|\band\b/i)
            .map(a => a.trim())
            .filter(a => a.length > 0);
        
        if (authorList.length <= maxAuthors) {
            return authors;
        }
        
        // Return first maxAuthors + et al.
        const abbreviated = authorList.slice(0, maxAuthors).join(', ') + ' et al.';
        return abbreviated;
    }
};

// Smart Collections API
const SmartCollectionsAPI = {
    async toggle(enabled) {
        return API.request('/collections/smart/toggle', {
            method: 'POST',
            body: JSON.stringify({ enabled })
        });
    },

    async getStatus() {
        return API.request('/collections/smart/status');
    },

    async classifyAll() {
        return API.request('/collections/smart/classify-all', {
            method: 'POST'
        });
    },

    async classifyPaper(paperId) {
        return API.request(`/collections/smart/classify/${paperId}`, {
            method: 'POST'
        });
    },

    async clear() {
        return API.request('/collections/smart/clear', {
            method: 'DELETE'
        });
    }
};

// Settings API
const SettingsAPI = {
    async getSummariesStatus() {
        return API.request('/settings/summaries/status');
    },

    async toggleSummaries(enabled) {
        return API.request('/settings/summaries/toggle', {
            method: 'POST',
            body: JSON.stringify({ enabled })
        });
    }
};

// Add to API object
API.smartCollections = SmartCollectionsAPI;
API.settings = SettingsAPI;
