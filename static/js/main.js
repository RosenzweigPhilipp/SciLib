// Main application logic
class App {
    constructor() {
        this.currentSection = 'dashboard';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupModals();
        this.checkAuthentication();
    }
    
    checkAuthentication() {
        const token = SessionManager.getToken();
        if (!token) {
            this.showLoginModal();
        } else {
            this.initializeManagers();
            this.showSection('dashboard');
        }
    }
    
    showLoginModal() {
        UIComponents.showModal('login-modal');
        // Hide main content until authenticated
        document.querySelector('.main').style.display = 'none';
        document.querySelector('.header').style.display = 'none';
    }
    
    onLoginSuccess() {
        UIComponents.hideModal('login-modal');
        document.querySelector('.main').style.display = 'block';
        document.querySelector('.header').style.display = 'block';
        this.initializeManagers();
        this.showSection('dashboard');
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const section = e.target.closest('.nav-btn').dataset.section;
                this.showSection(section);
            });
        });

        // Upload button
        document.getElementById('upload-btn').addEventListener('click', () => {
            UIComponents.showModal('upload-modal');
        });

        // Add buttons
        document.getElementById('add-paper-btn').addEventListener('click', () => {
            UIComponents.showModal('upload-modal');
        });

        document.getElementById('add-collection-btn').addEventListener('click', () => {
            this.collectionManager.showCreateModal();
        });

        document.getElementById('add-tag-btn').addEventListener('click', () => {
            this.tagManager.showCreateModal();
        });

        // Global search
        document.getElementById('global-search').addEventListener('input', (e) => {
            this.handleGlobalSearch(e.target.value);
        });

        // Login form
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleLogin();
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });
    }
    
    async handleLogin() {
        const apiKey = document.getElementById('api-key-input').value.trim();
        if (!apiKey) {
            UIComponents.showNotification('Please enter an API key', 'error');
            return;
        }
        
        try {
            await SessionManager.login(apiKey);
            UIComponents.showNotification('Login successful!', 'success');
            this.onLoginSuccess();
        } catch (error) {
            console.error('Login error:', error);
            UIComponents.showNotification('Invalid API key', 'error');
        }
    }
    
    handleLogout() {
        SessionManager.clearToken();
        UIComponents.showNotification('Logged out successfully', 'success');
        // Reset form
        document.getElementById('api-key-input').value = '';
        // Show login modal again
        this.showLoginModal();
    }

    setupModals() {
        // Close modal handlers
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                UIComponents.hideModal(modal.id);
            });
        });

        // Close modal on outside click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    UIComponents.hideModal(modal.id);
                }
            });
        });

        // Cancel buttons
        document.getElementById('collection-cancel').addEventListener('click', () => {
            UIComponents.hideModal('collection-modal');
        });

        document.getElementById('tag-cancel').addEventListener('click', () => {
            UIComponents.hideModal('tag-modal');
        });
    }

    initializeManagers() {
        this.dashboardManager = new DashboardManager();
        this.paperManager = new PaperManager();
        this.collectionManager = new CollectionManager();
        this.tagManager = new TagManager();
        this.uploadManager = new UploadManager();

        // Make managers globally accessible for component interactions
        window.dashboardManager = this.dashboardManager;
        window.paperManager = this.paperManager;
        window.collectionManager = this.collectionManager;
        window.tagManager = this.tagManager;
    }

    showSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');

        // Update sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(sectionName).classList.add('active');

        this.currentSection = sectionName;

        // Load section data
        this.loadSectionData(sectionName);
    }

    loadSectionData(sectionName) {
        switch (sectionName) {
            case 'dashboard':
                this.dashboardManager.loadDashboard();
                break;
            case 'papers':
                this.paperManager.loadPapers();
                break;
            case 'collections':
                this.collectionManager.loadCollections();
                break;
            case 'tags':
                this.tagManager.loadTags();
                break;
        }
    }

    handleGlobalSearch(query) {
        if (this.currentSection === 'papers') {
            this.paperManager.searchPapers(query);
        }
    }
}

// Dashboard Manager
class DashboardManager {
    async loadDashboard() {
        await this.loadStats();
        await this.loadRecentPapers();
    }

    async loadStats() {
        try {
            // Use the new stats endpoint that doesn't require authentication
            const response = await fetch('/api/stats');
            const stats = await response.json();

            document.getElementById('total-papers').textContent = stats.total_papers || 0;
            document.getElementById('total-collections').textContent = stats.total_collections || 0;
            document.getElementById('total-tags').textContent = stats.total_tags || 0;
            document.getElementById('recent-uploads').textContent = stats.recent_uploads || 0;

            if (stats.error) {
                console.warn('Stats API returned error:', stats.error);
            }

        } catch (error) {
            console.error('Error loading dashboard stats:', error);
            UIComponents.showNotification('Failed to load dashboard statistics', 'error');
            
            // Set default values on error
            document.getElementById('total-papers').textContent = '0';
            document.getElementById('total-collections').textContent = '0';
            document.getElementById('total-tags').textContent = '0';
            document.getElementById('recent-uploads').textContent = '0';
        }
    }

    async loadRecentPapers() {
        try {
            const papers = await API.papers.list({ limit: 5 });
            const container = document.getElementById('recent-papers-list');
            
            if (papers.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>No papers uploaded yet. Start by uploading your first paper!</p>
                    </div>
                `;
            } else {
                container.innerHTML = '';
                papers.forEach(paper => {
                    const card = UIComponents.createPaperCard(paper);
                    container.appendChild(card);
                });
            }
        } catch (error) {
            console.error('Error loading recent papers:', error);
        }
    }
}

// Paper Manager
class PaperManager {
    constructor() {
        this.papers = [];
        this.currentEditingId = null;
        this.setupPaperHandlers();
    }

    setupPaperHandlers() {
        // Sort papers
        document.getElementById('sort-papers').addEventListener('change', (e) => {
            this.sortPapers(e.target.value);
        });

        // Paper edit form
        document.getElementById('paper-edit-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.savePaper();
        });

        // Paper edit cancel
        document.getElementById('paper-edit-cancel').addEventListener('click', () => {
            UIComponents.hideModal('paper-edit-modal');
        });

        // Event delegation for paper action buttons
        document.getElementById('papers-list').addEventListener('click', (e) => {
            const button = e.target.closest('.action-btn');
            if (!button) return;

            const paperId = parseInt(button.dataset.paperId);
            if (!paperId) return;

            if (button.classList.contains('view-btn')) {
                this.showPaperDetails(paperId);
            } else if (button.classList.contains('edit-btn')) {
                this.editPaper(paperId);
            } else if (button.classList.contains('delete-btn')) {
                this.deletePaper(paperId);
            }
        });
    }

    async loadPapers() {
        try {
            UIComponents.setLoading(document.getElementById('papers-list'));
            this.papers = await API.papers.list({ limit: 100 });
            this.displayPapers(this.papers);
        } catch (error) {
            console.error('Error loading papers:', error);
            UIComponents.showNotification('Failed to load papers', 'error');
        }
    }

    displayPapers(papers) {
        const container = document.getElementById('papers-list');
        
        if (papers.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No papers found. Upload your first paper to get started!</p>
                </div>
            `;
        } else {
            container.innerHTML = '';
            papers.forEach(paper => {
                const card = UIComponents.createPaperCard(paper);
                container.appendChild(card);
            });
        }
    }

    sortPapers(sortBy) {
        let sortedPapers = [...this.papers];
        
        switch (sortBy) {
            case 'newest':
                sortedPapers.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                break;
            case 'oldest':
                sortedPapers.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
                break;
            case 'title':
                sortedPapers.sort((a, b) => a.title.localeCompare(b.title));
                break;
            case 'authors':
                sortedPapers.sort((a, b) => a.authors.localeCompare(b.authors));
                break;
        }
        
        this.displayPapers(sortedPapers);
    }

    searchPapers(query) {
        if (!query) {
            this.displayPapers(this.papers);
            return;
        }

        const filteredPapers = this.papers.filter(paper => 
            paper.title.toLowerCase().includes(query.toLowerCase()) ||
            paper.authors.toLowerCase().includes(query.toLowerCase()) ||
            (paper.abstract && paper.abstract.toLowerCase().includes(query.toLowerCase()))
        );

        this.displayPapers(filteredPapers);
    }

    async showPaperDetails(paperId) {
        try {
            const paper = await API.papers.get(paperId);
            const modal = document.getElementById('paper-details-modal');
            const content = document.getElementById('paper-details-content');
            
            content.innerHTML = `
                <div class="paper-header">
                    <h3>${Utils.sanitizeHtml(paper.title)}</h3>
                    <div class="authors">${Utils.sanitizeHtml(paper.authors)}</div>
                </div>
                
                <div class="paper-meta-grid">
                    ${paper.year ? `<div class="meta-item"><label>Year</label><value>${paper.year}</value></div>` : ''}
                    ${paper.journal ? `<div class="meta-item"><label>Journal</label><value>${Utils.sanitizeHtml(paper.journal)}</value></div>` : ''}
                    ${paper.doi ? `<div class="meta-item"><label>DOI</label><value>${Utils.sanitizeHtml(paper.doi)}</value></div>` : ''}
                    <div class="meta-item"><label>Uploaded</label><value>${Utils.formatDate(paper.created_at)}</value></div>
                </div>
                
                ${paper.abstract ? `
                    <div class="paper-abstract">
                        <h4>Abstract</h4>
                        <p>${Utils.sanitizeHtml(paper.abstract)}</p>
                    </div>
                ` : ''}
                
                ${paper.keywords ? `
                    <div class="paper-keywords">
                        <h4>Keywords</h4>
                        <p>${Utils.sanitizeHtml(paper.keywords)}</p>
                    </div>
                ` : ''}
            `;
            
            UIComponents.showModal('paper-details-modal');
        } catch (error) {
            console.error('Error loading paper details:', error);
            UIComponents.showNotification('Failed to load paper details', 'error');
        }
    }

    async editPaper(paperId) {
        try {
            const paper = await API.papers.get(paperId);
            this.currentEditingId = paperId;
            
            // Fill the form with paper data
            document.getElementById('paper-edit-title-input').value = paper.title || '';
            document.getElementById('paper-edit-authors').value = paper.authors || '';
            document.getElementById('paper-edit-year').value = paper.year || '';
            document.getElementById('paper-edit-journal').value = paper.journal || '';
            document.getElementById('paper-edit-doi').value = paper.doi || '';
            document.getElementById('paper-edit-abstract').value = paper.abstract || '';
            document.getElementById('paper-edit-keywords').value = paper.keywords || '';
            
            UIComponents.showModal('paper-edit-modal');
        } catch (error) {
            console.error('Error loading paper for editing:', error);
            UIComponents.showNotification('Failed to load paper details', 'error');
        }
    }

    async savePaper() {
        const title = document.getElementById('paper-edit-title-input').value.trim();
        const authors = document.getElementById('paper-edit-authors').value.trim();

        if (!title || !authors) {
            UIComponents.showNotification('Title and authors are required', 'error');
            return;
        }

        const data = {
            title: title,
            authors: authors,
            year: document.getElementById('paper-edit-year').value ? parseInt(document.getElementById('paper-edit-year').value) : null,
            journal: document.getElementById('paper-edit-journal').value.trim() || null,
            doi: document.getElementById('paper-edit-doi').value.trim() || null,
            abstract: document.getElementById('paper-edit-abstract').value.trim() || null,
            keywords: document.getElementById('paper-edit-keywords').value.trim() || null
        };

        try {
            await API.papers.update(this.currentEditingId, data);
            UIComponents.showNotification('Paper updated successfully', 'success');
            UIComponents.hideModal('paper-edit-modal');
            this.loadPapers();
            
            // Update dashboard stats if needed
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
            }
        } catch (error) {
            console.error('Error updating paper:', error);
            UIComponents.showNotification(`Failed to update paper: ${error.message}`, 'error');
        }
    }

    async deletePaper(paperId) {
        const confirmed = await UIComponents.confirm('Are you sure you want to delete this paper?');
        if (!confirmed) return;

        try {
            await API.papers.delete(paperId);
            UIComponents.showNotification('Paper deleted successfully', 'success');
            this.loadPapers();
            
            // Update dashboard stats
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
            }
        } catch (error) {
            console.error('Error deleting paper:', error);
            UIComponents.showNotification('Failed to delete paper', 'error');
        }
    }
}

// Collection Manager
class CollectionManager {
    constructor() {
        this.collections = [];
        this.currentEditingId = null;
        this.setupCollectionHandlers();
    }

    setupCollectionHandlers() {
        document.getElementById('collection-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveCollection();
        });
    }

    async loadCollections() {
        try {
            this.collections = await API.collections.list();
            this.displayCollections(this.collections);
        } catch (error) {
            console.error('Error loading collections:', error);
            UIComponents.showNotification('Failed to load collections', 'error');
        }
    }

    displayCollections(collections) {
        const container = document.getElementById('collections-list');
        
        if (collections.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>No collections created. Create your first collection to organize your papers!</p>
                </div>
            `;
        } else {
            container.innerHTML = '';
            collections.forEach(collection => {
                const card = UIComponents.createCollectionCard(collection);
                container.appendChild(card);
            });
        }
    }

    showCreateModal() {
        this.currentEditingId = null;
        document.getElementById('collection-modal-title').textContent = 'New Collection';
        UIComponents.clearForm('collection-form');
        UIComponents.showModal('collection-modal');
    }

    async editCollection(collectionId) {
        try {
            const collection = await API.collections.get(collectionId);
            this.currentEditingId = collectionId;
            
            document.getElementById('collection-modal-title').textContent = 'Edit Collection';
            document.getElementById('collection-name').value = collection.name;
            document.getElementById('collection-description').value = collection.description || '';
            
            UIComponents.showModal('collection-modal');
        } catch (error) {
            console.error('Error loading collection:', error);
            UIComponents.showNotification('Failed to load collection', 'error');
        }
    }

    async saveCollection() {
        const name = document.getElementById('collection-name').value;
        const description = document.getElementById('collection-description').value;

        if (!name.trim()) {
            UIComponents.showNotification('Collection name is required', 'error');
            return;
        }

        const data = {
            name: name.trim(),
            description: description.trim() || null
        };

        try {
            if (this.currentEditingId) {
                await API.collections.update(this.currentEditingId, data);
                UIComponents.showNotification('Collection updated successfully', 'success');
            } else {
                await API.collections.create(data);
                UIComponents.showNotification('Collection created successfully', 'success');
            }

            UIComponents.hideModal('collection-modal');
            this.loadCollections();
            
            // Update dashboard stats
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
            }
        } catch (error) {
            console.error('Error saving collection:', error);
            UIComponents.showNotification(`Failed to ${this.currentEditingId ? 'update' : 'create'} collection: ${error.message}`, 'error');
        }
    }

    async deleteCollection(collectionId) {
        const confirmed = await UIComponents.confirm('Are you sure you want to delete this collection?');
        if (!confirmed) return;

        try {
            await API.collections.delete(collectionId);
            UIComponents.showNotification('Collection deleted successfully', 'success');
            this.loadCollections();
            
            // Update dashboard stats
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
            }
        } catch (error) {
            console.error('Error deleting collection:', error);
            UIComponents.showNotification('Failed to delete collection', 'error');
        }
    }
}

// Tag Manager
class TagManager {
    constructor() {
        this.tags = [];
        this.currentEditingId = null;
        this.setupTagHandlers();
    }

    setupTagHandlers() {
        document.getElementById('tag-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveTag();
        });

        document.getElementById('tag-color').addEventListener('change', (e) => {
            document.getElementById('color-preview').style.background = e.target.value;
        });
    }

    async loadTags() {
        try {
            this.tags = await API.tags.list();
            this.displayTags(this.tags);
        } catch (error) {
            console.error('Error loading tags:', error);
            UIComponents.showNotification('Failed to load tags', 'error');
        }
    }

    displayTags(tags) {
        const container = document.getElementById('tags-list');
        
        if (tags.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-tag"></i>
                    <p>No tags created. Create tags to categorize your papers!</p>
                </div>
            `;
        } else {
            container.innerHTML = '';
            tags.forEach(tag => {
                const item = UIComponents.createTagItem(tag);
                container.appendChild(item);
            });
        }
    }

    showCreateModal() {
        this.currentEditingId = null;
        document.getElementById('tag-modal-title').textContent = 'New Tag';
        UIComponents.clearForm('tag-form');
        document.getElementById('color-preview').style.background = '#007bff';
        UIComponents.showModal('tag-modal');
    }

    async editTag(tagId) {
        try {
            const tag = await API.tags.get(tagId);
            this.currentEditingId = tagId;
            
            document.getElementById('tag-modal-title').textContent = 'Edit Tag';
            document.getElementById('tag-name').value = tag.name;
            document.getElementById('tag-color').value = tag.color;
            document.getElementById('color-preview').style.background = tag.color;
            
            UIComponents.showModal('tag-modal');
        } catch (error) {
            console.error('Error loading tag:', error);
            UIComponents.showNotification('Failed to load tag', 'error');
        }
    }

    async saveTag() {
        const name = document.getElementById('tag-name').value;
        const color = document.getElementById('tag-color').value;

        if (!name.trim()) {
            UIComponents.showNotification('Tag name is required', 'error');
            return;
        }

        const data = {
            name: name.trim(),
            color: color
        };

        try {
            if (this.currentEditingId) {
                await API.tags.update(this.currentEditingId, data);
                UIComponents.showNotification('Tag updated successfully', 'success');
            } else {
                await API.tags.create(data);
                UIComponents.showNotification('Tag created successfully', 'success');
            }

            UIComponents.hideModal('tag-modal');
            this.loadTags();
            
            // Update dashboard stats
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
            }
        } catch (error) {
            console.error('Error saving tag:', error);
            UIComponents.showNotification(`Failed to ${this.currentEditingId ? 'update' : 'create'} tag: ${error.message}`, 'error');
        }
    }

    async deleteTag(tagId) {
        const confirmed = await UIComponents.confirm('Are you sure you want to delete this tag?');
        if (!confirmed) return;

        try {
            await API.tags.delete(tagId);
            UIComponents.showNotification('Tag deleted successfully', 'success');
            this.loadTags();
            
            // Update dashboard stats
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
            }
        } catch (error) {
            console.error('Error deleting tag:', error);
            UIComponents.showNotification('Failed to delete tag', 'error');
        }
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});