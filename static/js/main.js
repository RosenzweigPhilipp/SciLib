// Main application logic
class App {
    constructor() {
        this.currentSection = 'dashboard';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupModals();
        this.checkApiKey();
    }
    
    setupEventListeners() {
        // Navigation
        const navBtns = document.querySelectorAll('.nav-btn');
        if (navBtns && navBtns.length > 0) {
            navBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const section = e.target.closest('.nav-btn').dataset.section;
                    this.showSection(section);
                });
            });
        } else {
            console.warn('No navigation buttons found to attach listeners');
        }

        // Upload button
        const uploadBtn = document.getElementById('upload-btn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => UIComponents.showModal('upload-modal'));
        } else {
            console.warn('Upload button not found');
        }

        // Add buttons
        const addPaperBtn = document.getElementById('add-paper-btn');
        if (addPaperBtn) {
            addPaperBtn.addEventListener('click', () => UIComponents.showModal('upload-modal'));
        } else {
            console.warn('Add paper button not found');
        }

        const addCollectionBtn = document.getElementById('add-collection-btn');
        if (addCollectionBtn) {
            addCollectionBtn.addEventListener('click', () => { if (this.collectionManager) this.collectionManager.showCreateModal(); });
        } else {
            console.warn('Add collection button not found');
        }

        const addTagBtn = document.getElementById('add-tag-btn');
        if (addTagBtn) {
            addTagBtn.addEventListener('click', () => { if (this.tagManager) this.tagManager.showCreateModal(); });
        } else {
            console.warn('Add tag button not found');
        }

        // Global search
        const globalSearch = document.getElementById('global-search');
        if (globalSearch) {
            globalSearch.addEventListener('input', (e) => this.handleGlobalSearch(e.target.value));
        } else {
            console.warn('Global search input not found');
        }

        // API key form
        const apiKeyForm = document.getElementById('api-key-form');
        if (apiKeyForm) {
            apiKeyForm.addEventListener('submit', (e) => { e.preventDefault(); this.handleApiKeySubmit(); });
        } else {
            console.warn('API key form not found');
        }
    }
    
    checkApiKey() {
        const apiKey = ApiKeyManager.getApiKey();
        if (!apiKey) {
            this.showApiKeyModal();
        } else {
            this.initializeManagers();
            this.showSection('dashboard');
        }
    }
    
    showApiKeyModal() {
        UIComponents.showModal('api-key-modal');
        document.querySelector('.main').style.display = 'none';
        document.querySelector('.header').style.display = 'none';
    }
    
    onApiKeySet() {
        UIComponents.hideModal('api-key-modal');
        document.querySelector('.main').style.display = 'block';
        document.querySelector('.header').style.display = 'block';
        this.initializeManagers();
        this.showSection('dashboard');
    }
    
    handleApiKeySubmit() {
        const apiKey = document.getElementById('api-key-input').value.trim();
        if (!apiKey) {
            UIComponents.showNotification('Please enter an API key', 'error');
            return;
        }
        
        ApiKeyManager.setApiKey(apiKey);
        UIComponents.showNotification('API key saved successfully!', 'success');
        this.onApiKeySet();
    }

    setupModals() {
        // Close modal handlers
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                // Stop polling if paper edit modal is closed
                if (modal.id === 'paper-edit-modal' && this.paperManager && this.paperManager.metadataPollingInterval) {
                    clearInterval(this.paperManager.metadataPollingInterval);
                    this.paperManager.metadataPollingInterval = null;
                }
                // Stop polling if paper details modal is closed
                if (modal.id === 'paper-details-modal' && this.paperManager && this.paperManager.detailsPollingInterval) {
                    clearInterval(this.paperManager.detailsPollingInterval);
                    this.paperManager.detailsPollingInterval = null;
                }
                // Reload papers when closing paper-related modals to show updated metadata
                if ((modal.id === 'paper-details-modal' || modal.id === 'paper-edit-modal') && this.paperManager) {
                    this.paperManager.loadPapers();
                }
                UIComponents.hideModal(modal.id);
            });
        });

        // Close modal on outside click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    // Stop polling if paper edit modal is closed
                    if (modal.id === 'paper-edit-modal' && this.paperManager && this.paperManager.metadataPollingInterval) {
                        clearInterval(this.paperManager.metadataPollingInterval);
                        this.paperManager.metadataPollingInterval = null;
                    }
                    // Stop polling if paper details modal is closed
                    if (modal.id === 'paper-details-modal' && this.paperManager && this.paperManager.detailsPollingInterval) {
                        clearInterval(this.paperManager.detailsPollingInterval);
                        this.paperManager.detailsPollingInterval = null;
                    }
                    // Reload papers when closing paper-related modals to show updated metadata
                    if ((modal.id === 'paper-details-modal' || modal.id === 'paper-edit-modal') && this.paperManager) {
                        this.paperManager.loadPapers();
                    }
                    UIComponents.hideModal(modal.id);
                }
            });
        });

        // Cancel buttons
        const collectionCancel = document.getElementById('collection-cancel');
        if (collectionCancel) collectionCancel.addEventListener('click', () => UIComponents.hideModal('collection-modal'));

        const tagCancel = document.getElementById('tag-cancel');
        if (tagCancel) tagCancel.addEventListener('click', () => UIComponents.hideModal('tag-modal'));
        
        // Paper edit cancel - also stop polling
        const paperEditCancel = document.getElementById('paper-edit-cancel');
        if (paperEditCancel) {
            paperEditCancel.addEventListener('click', () => {
                if (this.paperManager && this.paperManager.metadataPollingInterval) {
                    clearInterval(this.paperManager.metadataPollingInterval);
                    this.paperManager.metadataPollingInterval = null;
                }
                UIComponents.hideModal('paper-edit-modal');
            });
        }
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
        window.uploadManager = this.uploadManager;

        console.log('DEBUG: Managers initialized', {
            dashboard: !!window.dashboardManager,
            paper: !!window.paperManager,
            collection: !!window.collectionManager,
            tag: !!window.tagManager,
            upload: !!window.uploadManager,
        });
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
    constructor() {
        this.setupSmartCollections();
    }

    async loadDashboard() {
        await this.loadStats();
        await this.loadRecentPapers();
        await this.loadSmartCollectionsStatus();
        await this.loadAutoSummariesStatus();
    }

    setupSmartCollections() {
        const toggle = document.getElementById('smart-collections-toggle');
        if (toggle) {
            toggle.addEventListener('change', async (e) => {
                await this.toggleSmartCollections(e.target.checked);
            });
        }

        const summariesToggle = document.getElementById('auto-summaries-toggle');
        if (summariesToggle) {
            summariesToggle.addEventListener('change', async (e) => {
                await this.toggleAutoSummaries(e.target.checked);
            });
        }
    }

    async loadSmartCollectionsStatus() {
        try {
            const panel = document.getElementById('smart-collections-panel');
            if (panel) {
                panel.style.display = 'block';
            }

            const status = await API.smartCollections.getStatus();
            
            // Update toggle
            const toggle = document.getElementById('smart-collections-toggle');
            const label = document.getElementById('smart-toggle-label');
            if (toggle && label) {
                toggle.checked = status.enabled;
                label.textContent = status.enabled ? 'Enabled' : 'Disabled';
            }

            // Update stats
            const statsContainer = document.getElementById('smart-collections-stats');
            if (statsContainer) {
                statsContainer.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${status.total_smart_collections || 0}</div>
                        <div class="stat-label">Research Fields</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${status.classified_papers || 0}</div>
                        <div class="stat-label">Classified Papers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${status.unclassified_papers || 0}</div>
                        <div class="stat-label">Unclassified</div>
                    </div>
                `;
            }

            // Update collections list
            const listContainer = document.getElementById('smart-collections-list');
            if (listContainer && status.smart_collections && status.smart_collections.length > 0) {
                listContainer.innerHTML = status.smart_collections
                    .sort((a, b) => b.paper_count - a.paper_count)
                    .slice(0, 10)
                    .map(c => `
                        <div class="smart-collection-item">
                            <span class="name"><i class="fas fa-brain"></i> ${Utils.sanitizeHtml(c.name)}</span>
                            <span class="count">${c.paper_count} papers</span>
                        </div>
                    `).join('');
            } else if (listContainer) {
                listContainer.innerHTML = '<p style="text-align: center; color: #777; padding: 1rem;">No smart collections yet</p>';
            }
        } catch (error) {
            console.error('Error loading smart collections status:', error);
        }
    }

    async loadAutoSummariesStatus() {
        try {
            const panel = document.getElementById('auto-summaries-panel');
            if (panel) {
                panel.style.display = 'block';
            }

            const status = await API.settings.getSummariesStatus();
            
            // Update toggle
            const toggle = document.getElementById('auto-summaries-toggle');
            const label = document.getElementById('summaries-toggle-label');
            if (toggle && label) {
                toggle.checked = status.enabled;
                label.textContent = status.enabled ? 'Enabled' : 'Disabled';
            }
        } catch (error) {
            console.error('Error loading auto-summaries status:', error);
        }
    }

    async toggleSmartCollections(enabled) {
        try {
            const label = document.getElementById('smart-toggle-label');
            if (label) {
                label.textContent = enabled ? 'Enabling...' : 'Disabling...';
            }

            const result = await API.smartCollections.toggle(enabled);
            
            if (enabled && result.task_id) {
                UIComponents.showNotification('Smart collections enabled. Classifying all papers...', 'info');
            } else {
                UIComponents.showNotification(`Smart collections ${enabled ? 'enabled' : 'disabled'}`, 'success');
            }

            // Reload status and papers after a delay to show updated stats
            setTimeout(() => {
                this.loadSmartCollectionsStatus();
                if (window.paperManager) {
                    window.paperManager.loadPapers();
                }
            }, 2000);
        } catch (error) {
            console.error('Error toggling smart collections:', error);
            UIComponents.showNotification('Failed to toggle smart collections', 'error');
            
            // Revert toggle
            const toggle = document.getElementById('smart-collections-toggle');
            if (toggle) {
                toggle.checked = !enabled;
            }
        }
    }

    async toggleAutoSummaries(enabled) {
        try {
            const label = document.getElementById('summaries-toggle-label');
            if (label) {
                label.textContent = enabled ? 'Enabling...' : 'Disabling...';
            }

            await API.settings.toggleSummaries(enabled);
            
            UIComponents.showNotification(`Auto-summaries ${enabled ? 'enabled' : 'disabled'}`, 'success');

            // Update label
            if (label) {
                label.textContent = enabled ? 'Enabled' : 'Disabled';
            }
        } catch (error) {
            console.error('Error toggling auto-summaries:', error);
            UIComponents.showNotification('Failed to toggle auto-summaries', 'error');
            
            // Revert toggle
            const toggle = document.getElementById('auto-summaries-toggle');
            if (toggle) {
                toggle.checked = !enabled;
            }
        }
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
        this.currentPage = 1;
        this.itemsPerPage = 20;
        this.totalPapers = 0;
        this.activeSummaryTasks = new Set(); // Track papers with active summary generation
        this.currentDiscoveryResults = []; // Store current discovery results
        this.discoveryVisibleCount = 3; // Number of discovery results to show initially
        this.setupPaperHandlers();
    }

    setupPaperHandlers() {
        // Sort papers
        const sortPapersEl = document.getElementById('sort-papers');
        if (sortPapersEl) sortPapersEl.addEventListener('change', (e) => this.sortPapers(e.target.value));

        // Paper edit form
        const paperEditForm = document.getElementById('paper-edit-form');
        if (paperEditForm) paperEditForm.addEventListener('submit', (e) => { e.preventDefault(); this.savePaper(); });

        // Clear all papers button
        const clearBtn = document.getElementById('clear-papers-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', async () => {
                const confirmed = await UIComponents.confirm('Are you sure you want to permanently delete ALL papers? This cannot be undone.');
                if (!confirmed) return;

                try {
                    await API.papers.clear();
                    UIComponents.showNotification('All papers cleared', 'success');
                    this.loadPapers();
                    if (window.dashboardManager) {
                        window.dashboardManager.loadStats();
                    }
                } catch (error) {
                    console.error('Error clearing papers:', error);
                    UIComponents.showNotification('Failed to clear papers', 'error');
                }
            });
            console.log('DEBUG: Attached clear all papers button listener');
        }

        // Event delegation for paper action buttons
        const papersListEl = document.getElementById('papers-list');
        if (papersListEl) papersListEl.addEventListener('click', (e) => {
            console.log('DEBUG: Papers list clicked', e.target);
            
            const button = e.target.closest('.action-btn');
            if (!button) {
                console.log('DEBUG: Not an action button');
                return;
            }

            console.log('DEBUG: Action button clicked', button);
            const paperId = parseInt(button.dataset.paperId);
            console.log('DEBUG: Paper ID:', paperId);
            
            if (!paperId) {
                console.log('DEBUG: No paper ID found');
                return;
            }

            if (button.classList.contains('view-btn')) {
                console.log('DEBUG: View button clicked for paper', paperId);
                this.showPaperDetails(paperId);
            } else if (button.classList.contains('edit-btn')) {
                console.log('DEBUG: Edit button clicked for paper', paperId);
                this.editPaper(paperId);
            } else if (button.classList.contains('delete-btn')) {
                console.log('DEBUG: Delete button clicked for paper', paperId);
                this.deletePaper(paperId);
            }
        });
        if (papersListEl) console.log('DEBUG: Attached papers list delegation listener');
    }

    async loadPapers(page = null) {
        try {
            if (page !== null) {
                this.currentPage = page;
            }
            
            const skip = (this.currentPage - 1) * this.itemsPerPage;
            
            UIComponents.setLoading(document.getElementById('papers-list'));
            
            // Load papers with pagination
            this.papers = await API.papers.list({ 
                skip: skip,
                limit: this.itemsPerPage
            });
            
            // Get total count (we'll need to add this to the API response)
            // For now, estimate based on returned results
            this.totalPapers = this.papers.length < this.itemsPerPage ? 
                skip + this.papers.length : 
                (this.currentPage + 1) * this.itemsPerPage; // Estimate there's at least one more page
            
            this.displayPapers(this.papers);
            this.renderPagination();
        } catch (error) {
            console.error('Error loading papers:', error);
            UIComponents.showNotification('Failed to load papers', 'error');
        }
    }
    
    renderPagination() {
        const container = document.getElementById('papers-pagination');
        if (!container) return;
        
        const totalPages = Math.ceil(this.totalPapers / this.itemsPerPage);
        
        // Hide pagination if only one page
        if (totalPages <= 1) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'flex';
        container.innerHTML = '';
        
        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.className = 'pagination-btn';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
        prevBtn.disabled = this.currentPage === 1;
        prevBtn.addEventListener('click', () => this.loadPapers(this.currentPage - 1));
        container.appendChild(prevBtn);
        
        // Page info
        const pageInfo = document.createElement('span');
        pageInfo.className = 'pagination-info';
        pageInfo.textContent = `Page ${this.currentPage}`;
        container.appendChild(pageInfo);
        
        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.className = 'pagination-btn';
        nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
        nextBtn.disabled = this.papers.length < this.itemsPerPage;
        nextBtn.addEventListener('click', () => this.loadPapers(this.currentPage + 1));
        container.appendChild(nextBtn);
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
            
            // Generate AI extraction info
            const aiInfo = this.generateAIExtractionInfo(paper);
            
            // Add status banner based on current state
            let statusBanner = '';
            const isGeneratingSummary = this.activeSummaryTasks.has(paper.id);
            
            if (paper.extraction_status === 'pending') {
                statusBanner = `
                    <div class="extraction-status-banner processing" style="margin-bottom: 1rem;">
                        <i class="fas fa-clock"></i>
                        <span>Waiting for extraction task to start...</span>
                    </div>
                `;
            } else if (paper.extraction_status === 'processing') {
                statusBanner = `
                    <div class="extraction-status-banner processing" style="margin-bottom: 1rem;">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>AI pipeline extracting metadata...</span>
                    </div>
                `;
            } else if (isGeneratingSummary) {
                statusBanner = `
                    <div class="extraction-status-banner generating" style="margin-bottom: 1rem;">
                        <i class="fas fa-magic fa-spin"></i>
                        <span>Generating AI summaries...</span>
                    </div>
                `;
            }
            
            content.innerHTML = `
                ${statusBanner}
                <div class="paper-header">
                    <h3>${Utils.sanitizeHtml(paper.title)}</h3>
                    <div class="authors" id="paper-authors-display" style="cursor: pointer;" title="Click to show all authors">
                        ${Utils.sanitizeHtml(Utils.formatAuthors(paper.authors, 3))}
                    </div>
                    <div style="margin-top: 0.5rem;">
                        ${UIComponents.getAIStatusBadge(paper)}
                    </div>
                </div>
                
                <div class="paper-meta-grid">
                    ${paper.year ? `<div class="meta-item"><label>Year</label><value>${paper.year}</value></div>` : ''}
                    ${paper.journal ? `<div class="meta-item"><label>Journal</label><value>${Utils.sanitizeHtml(paper.journal)}</value></div>` : ''}
                    ${paper.publisher ? `<div class="meta-item"><label>Publisher</label><value>${Utils.sanitizeHtml(paper.publisher)}</value></div>` : ''}
                    ${paper.volume ? `<div class="meta-item"><label>Volume</label><value>${paper.volume}</value></div>` : ''}
                    ${paper.issue ? `<div class="meta-item"><label>Issue</label><value>${paper.issue}</value></div>` : ''}
                    ${paper.pages ? `<div class="meta-item"><label>Pages</label><value>${paper.pages}</value></div>` : ''}
                    ${paper.booktitle ? `<div class="meta-item"><label>Conference</label><value>${Utils.sanitizeHtml(paper.booktitle)}</value></div>` : ''}
                    ${paper.doi ? `<div class="meta-item"><label>DOI</label><value>${Utils.sanitizeHtml(paper.doi)}</value></div>` : ''}
                    <div class="meta-item"><label>Uploaded</label><value>${Utils.formatDate(paper.created_at)}</value></div>
                    ${paper.extracted_at ? `<div class="meta-item"><label>AI Extracted</label><value>${Utils.formatDate(paper.extracted_at)}</value></div>` : ''}
                </div>
                
                <div class="action-buttons" style="margin: 1rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <button class="btn btn-secondary" onclick="window.paperManager.exportBibtex(${paper.id})">
                        <i class="fas fa-download"></i> Export BibTeX
                    </button>
                    <button class="btn btn-secondary" onclick="window.paperManager.organizePdf(${paper.id})" title="Rename PDF to: Author - Year - Title.pdf">
                        <i class="fas fa-file-signature"></i> Organize PDF Name
                    </button>
                </div>
                
                ${aiInfo}
                
                <div class="content-tabs">
                    <div class="tabs-header">
                        <button class="tab-btn active" onclick="window.paperManager.switchTab(event, 'abstract-tab')">Abstract</button>
                        <button class="tab-btn" onclick="window.paperManager.switchTab(event, 'summary-long-tab')">Detailed Summary</button>
                        <button class="tab-btn" onclick="window.paperManager.switchTab(event, 'summary-short-tab')">Short Summary</button>
                        <button class="tab-btn" onclick="window.paperManager.switchTab(event, 'eli5-tab')">ELI5</button>
                        <button class="tab-btn" onclick="window.paperManager.switchTab(event, 'findings-tab')">Key Findings</button>
                    </div>
                    <div class="tabs-content">
                        <div id="abstract-tab" class="tab-pane active">
                            ${paper.abstract ? `<p>${Utils.sanitizeHtml(paper.abstract)}</p>` : '<p class="empty-message">No abstract available</p>'}
                        </div>
                        <div id="summary-long-tab" class="tab-pane">
                            ${paper.ai_summary_long ? `<p>${Utils.sanitizeHtml(paper.ai_summary_long)}</p>` : '<p class="empty-message">No detailed summary available yet</p>'}
                        </div>
                        <div id="summary-short-tab" class="tab-pane">
                            ${paper.ai_summary_short ? `<p>${Utils.sanitizeHtml(paper.ai_summary_short)}</p>` : '<p class="empty-message">No short summary available yet</p>'}
                        </div>
                        <div id="eli5-tab" class="tab-pane">
                            ${paper.ai_summary_eli5 ? `<p class="eli5-summary">${Utils.sanitizeHtml(paper.ai_summary_eli5)}</p>` : '<p class="empty-message">No ELI5 summary available yet</p>'}
                        </div>
                        <div id="findings-tab" class="tab-pane">
                            ${this.generateKeyFindingsContent(paper)}
                        </div>
                    </div>
                </div>
                
                ${this.generateSummaryButton(paper)}
                
                ${this.generateCollectionsSection(paper)}
                
                ${paper.keywords ? `
                    <div class="paper-keywords">
                        <h4>Keywords</h4>
                        <p>${Utils.sanitizeHtml(paper.keywords)}</p>
                    </div>
                ` : ''}
                
                <div id="discovery-section"></div>
            `;
            
            UIComponents.showModal('paper-details-modal');
            
            // Add click handler for authors toggle
            this.setupAuthorsToggle(paper.authors);
            
            // Initialize discovery section
            this.initializeDiscoverySection(paper);
            
        } catch (error) {
            console.error('Error loading paper details:', error);
            UIComponents.showNotification('Failed to load paper details', 'error');
        }
    }
    
    setupAuthorsToggle(fullAuthors) {
        const authorsDisplay = document.getElementById('paper-authors-display');
        if (!authorsDisplay || !fullAuthors) return;
        
        let isExpanded = false;
        
        authorsDisplay.addEventListener('click', () => {
            if (isExpanded) {
                // Show abbreviated
                authorsDisplay.innerHTML = Utils.sanitizeHtml(Utils.formatAuthors(fullAuthors, 3));
                authorsDisplay.title = 'Click to show all authors';
                isExpanded = false;
            } else {
                // Show all
                authorsDisplay.innerHTML = Utils.sanitizeHtml(fullAuthors);
                authorsDisplay.title = 'Click to show fewer authors';
                isExpanded = true;
            }
        });
    }
    
    generateKeyFindingsContent(paper) {
        if (!paper.ai_key_findings) {
            return '<p class="empty-message">No key findings available yet</p>';
        }
        
        const findings = Array.isArray(paper.ai_key_findings) ? paper.ai_key_findings : 
                        (typeof paper.ai_key_findings === 'string' ? JSON.parse(paper.ai_key_findings) : []);
        
        if (findings.length === 0) {
            return '<p class="empty-message">No key findings available yet</p>';
        }
        
        return `
            <ul class="findings-list">
                ${findings.map(f => `<li>${Utils.sanitizeHtml(f)}</li>`).join('')}
            </ul>
        `;
    }
    
    showSummaryLoadingState() {
        // Update all summary tabs to show loading state
        const longTab = document.getElementById('summary-long-tab');
        const shortTab = document.getElementById('summary-short-tab');
        const findingsTab = document.getElementById('findings-tab');
        
        const loadingHTML = `
            <div class="summary-loading">
                <div class="loading-spinner">
                    <i class="fas fa-circle-notch fa-spin"></i>
                </div>
                <p>Generating AI summary...</p>
                <p class="loading-subtext">This may take 30-60 seconds</p>
            </div>
        `;
        
        if (longTab) longTab.innerHTML = loadingHTML;
        if (shortTab) shortTab.innerHTML = loadingHTML;
        if (findingsTab) findingsTab.innerHTML = loadingHTML;
        
        // Update the generate button area
        const summaryAction = document.querySelector('.summary-action');
        if (summaryAction) {
            summaryAction.innerHTML = `
                <div class="summary-status generating">
                    <i class="fas fa-magic fa-spin"></i>
                    <span>Generating summaries...</span>
                </div>
            `;
        }
    }
    
    generateSummaryButton(paper) {
        const hasSummaries = paper.ai_summary_short || paper.ai_summary_long || paper.ai_key_findings;
        const isGenerating = this.activeSummaryTasks.has(paper.id);
        
        // Determine what stage we're in
        let statusDisplay = '';
        if (isGenerating) {
            // Check if we have knowledge check results
            if (paper.llm_knowledge_check === null) {
                statusDisplay = `
                    <div class="summary-status-box processing">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>Checking if LLM has knowledge of this paper...</span>
                    </div>
                `;
            } else if (paper.llm_knowledge_check === true && !hasSummaries) {
                statusDisplay = `
                    <div class="summary-status-box processing">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>Generating summaries from LLM training data...</span>
                    </div>
                `;
            } else if (paper.llm_knowledge_check === false && !hasSummaries) {
                statusDisplay = `
                    <div class="summary-status-box processing">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>Extracting full paper text and generating summaries...</span>
                    </div>
                `;
            }
        }
        
        // Knowledge check indicator
        let knowledgeIndicator = '';
        if (paper.llm_knowledge_check !== null && paper.llm_knowledge_check !== undefined) {
            if (paper.llm_knowledge_check) {
                knowledgeIndicator = `<span class="badge badge-success" title="LLM has knowledge of this paper (confidence: ${(paper.llm_knowledge_confidence * 100).toFixed(0)}%)"><i class="fas fa-brain"></i> Known</span>`;
            } else {
                knowledgeIndicator = `<span class="badge badge-warning" title="LLM doesn't know this paper (confidence: ${(paper.llm_knowledge_confidence * 100).toFixed(0)}%)"><i class="fas fa-question"></i> Unknown</span>`;
            }
        }
        
        if (!hasSummaries) {
            // Disable button if currently generating
            const buttonDisabled = isGenerating ? 'disabled' : '';
            const buttonText = isGenerating ? '<i class="fas fa-spinner fa-spin"></i> Generating...' : '<i class="fas fa-magic"></i> Generate AI Summary';
            
            return `
                ${statusDisplay}
                <div class="summary-action">
                    ${knowledgeIndicator}
                    <button class="btn btn-primary" onclick="window.paperManager.generateSummary(${paper.id})" ${buttonDisabled}>
                        ${buttonText}
                    </button>
                </div>
            `;
        }
        
        // Determine generation method badge
        let methodBadge = '';
        if (paper.summary_generation_method === 'llm_knowledge') {
            methodBadge = '<span class="badge badge-auto" title="Auto-generated from LLM training data"><i class="fas fa-bolt"></i> Auto</span>';
        } else if (paper.summary_generation_method === 'manual') {
            methodBadge = '<span class="badge badge-manual" title="Generated from full paper extraction"><i class="fas fa-user"></i> Manual</span>';
        }
        
        return `
            ${statusDisplay}
            <div class="summary-action">
                <div class="summary-info">
                    ${knowledgeIndicator}
                    ${methodBadge}
                    ${paper.summary_generated_at ? `<span class="summary-date">Generated ${Utils.formatDate(paper.summary_generated_at)}</span>` : ''}
                </div>
                <button class="btn btn-secondary btn-sm" onclick="window.paperManager.generateSummary(${paper.id})" ${isGenerating ? 'disabled' : ''}>
                    ${isGenerating ? '<i class="fas fa-spinner fa-spin"></i> Regenerating...' : '<i class="fas fa-sync"></i> Regenerate Summary'}
                </button>
            </div>
        `;
    }
    
    generateCitationsSection(paper) {
        const citationCount = paper.citation_count || 0;
        const externalCount = paper.external_citation_count || 0;
        const influenceScore = paper.influence_score || 0;
        const hIndex = paper.h_index || 0;
        
        return `
            <div class="citations-section">
                <h4><i class="fas fa-quote-right"></i> Citation Metrics</h4>
                <div class="citation-metrics">
                    <div class="metric-item">
                        <span class="metric-value">${citationCount}</span>
                        <span class="metric-label">Internal Citations</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-value">${externalCount}</span>
                        <span class="metric-label">External Citations</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-value">${influenceScore.toFixed(3)}</span>
                        <span class="metric-label">Influence Score</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-value">${hIndex}</span>
                        <span class="metric-label">H-Index</span>
                    </div>
                </div>
                <div class="citation-actions">
                    <button class="btn btn-secondary btn-sm" onclick="window.paperManager.fetchExternalCitations(${paper.id})">
                        <i class="fas fa-cloud-download-alt"></i> Fetch External Citations
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="window.paperManager.calculateInfluence(${paper.id})">
                        <i class="fas fa-calculator"></i> Calculate Influence
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="window.paperManager.showCitations(${paper.id})">
                        <i class="fas fa-network-wired"></i> View Citation Network
                    </button>
                </div>
            </div>
        `;
    }

    generateCollectionsSection(paper) {
        if (!paper.collections || paper.collections.length === 0) {
            return '';
        }
        
        return `
            <div class="paper-collections-section">
                <h4><i class="fas fa-folder"></i> Collections</h4>
                <div class="collection-badges-list">
                    ${paper.collections.map(c => `
                        <div class="collection-badge-item${c.is_smart ? ' smart' : ''}" 
                             onclick="window.collectionManager.viewCollectionPapers(${c.id}, event)" 
                             title="${Utils.sanitizeHtml(c.description || c.name)}">
                            ${c.is_smart ? '<i class="fas fa-brain"></i> ' : '<i class="fas fa-folder"></i> '}
                            ${Utils.sanitizeHtml(c.name)}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    async loadRecommendations(paperId) {
        const container = document.getElementById('recommendations-section');
        if (!container) return;
        
        container.innerHTML = `
            <div class="recommendations-section">
                <h4><i class="fas fa-star"></i> Similar Papers</h4>
                <div class="loading">Loading recommendations...</div>
            </div>
        `;
        
        try {
            const recommendations = await API.ai.getRecommendations(paperId, 5);
            
            if (!recommendations || recommendations.length === 0) {
                container.innerHTML = `
                    <div class="recommendations-section">
                        <h4><i class="fas fa-star"></i> Similar Papers</h4>
                        <p class="no-data">No similar papers found in your library.</p>
                    </div>
                `;
                return;
            }
            
            let recsHTML = `
                <div class="recommendations-section">
                    <h4><i class="fas fa-star"></i> Similar Papers</h4>
                    <div class="recommendations-list">
            `;
            
            recommendations.forEach((rec, idx) => {
                recsHTML += `
                    <div class="recommendation-item">
                        <div class="rec-rank">#${idx + 1}</div>
                        <div class="rec-content">
                            <div class="rec-title" onclick="window.paperManager.showPaperDetails(${rec.id})">
                                ${Utils.sanitizeHtml(rec.title)}
                            </div>
                            <div class="rec-authors">${Utils.sanitizeHtml(rec.authors)}</div>
                            <div class="rec-score">
                                <span class="score-label">Similarity:</span>
                                <span class="score-value">${(rec.score * 100).toFixed(1)}%</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            recsHTML += '</div></div>';
            container.innerHTML = recsHTML;
            
        } catch (error) {
            console.error('Error loading recommendations:', error);
            container.innerHTML = `
                <div class="recommendations-section">
                    <h4><i class="fas fa-star"></i> Similar Papers</h4>
                    <p class="error-message">Failed to load recommendations.</p>
                </div>
            `;
        }
    }
    
    initializeDiscoverySection(paper) {
        const container = document.getElementById('discovery-section');
        if (!container) return;
        
        container.innerHTML = `
            <div class="discovery-section">
                <h4>
                    <i class="fas fa-globe"></i> External Discovery
                    <span class="badge badge-experimental"><i class="fas fa-flask"></i> Experimental</span>
                </h4>
                <p class="discovery-description">Search external databases for similar papers</p>
                <button class="btn btn-primary" onclick="window.paperManager.discoverSimilarPapers(${paper.id})">
                    <i class="fas fa-search"></i> Discover Similar Papers
                </button>
                <div id="discovery-results"></div>
            </div>
        `;
    }
    
    async discoverSimilarPapers(paperId) {
        const resultsContainer = document.getElementById('discovery-results');
        if (!resultsContainer) return;
        
        try {
            // Show loading state
            resultsContainer.innerHTML = `
                <div class="discovery-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Searching external databases...</span>
                </div>
            `;
            
            // Get paper details to build search query
            const paper = await API.papers.get(paperId);
            const searchQuery = paper.title;
            
            // Search external databases
            const results = await API.ai.discoverPapers(searchQuery, 10);
            
            if (!results || !results.papers || results.papers.length === 0) {
                resultsContainer.innerHTML = `
                    <div class="discovery-empty">
                        <p>No similar papers found in external databases.</p>
                    </div>
                `;
                return;
            }
            
            // Store results for later use
            this.currentDiscoveryResults = results.papers;
            this.discoveryVisibleCount = 3; // Initially show 3 papers
            
            // Render the results
            this.renderDiscoveryResults(paperId, resultsContainer, results.total_results);
            
        } catch (error) {
            console.error('Error discovering similar papers:', error);
            resultsContainer.innerHTML = `
                <div class="discovery-error">
                    <p class="error-message">Failed to search external databases. Please try again.</p>
                </div>
            `;
            UIComponents.showNotification('Failed to discover papers', 'error');
        }
    }
    
    renderDiscoveryResults(paperId, container, totalResults) {
        const papers = this.currentDiscoveryResults;
        const visibleCount = this.discoveryVisibleCount;
        
        // Display results header
        let html = `
            <div class="discovery-results-header">
                <span class="results-count">Found ${totalResults} papers</span>
            </div>
            <div class="discovery-results-list">
        `;
        
        // Show only visible count
        papers.slice(0, visibleCount).forEach((paper, idx) => {
            const inLibrary = paper.in_library;
            const statusBadge = inLibrary 
                ? '<span class="badge badge-success"><i class="fas fa-check"></i> In Library</span>'
                : '';
            
            html += `
                <div class="discovery-result-item">
                    <div class="discovery-result-header">
                        <span class="result-number">#${idx + 1}</span>
                        <span class="result-source badge badge-info">${paper.source}</span>
                        ${statusBadge}
                    </div>
                    <div class="discovery-result-title">${Utils.sanitizeHtml(paper.title)}</div>
                    <div class="discovery-result-authors">${Utils.sanitizeHtml(paper.authors || 'Unknown authors')}</div>
                    <div class="discovery-result-meta">
                        ${paper.year ? `<span><i class="fas fa-calendar"></i> ${paper.year}</span>` : ''}
                        ${paper.citation_count ? `<span><i class="fas fa-quote-right"></i> ${paper.citation_count} citations</span>` : ''}
                        ${paper.journal ? `<span><i class="fas fa-book"></i> ${Utils.sanitizeHtml(paper.journal)}</span>` : ''}
                    </div>
                    ${paper.abstract ? `
                        <div class="discovery-result-abstract">
                            ${Utils.sanitizeHtml(paper.abstract.substring(0, 200))}${paper.abstract.length > 200 ? '...' : ''}
                        </div>
                    ` : ''}
                    <div class="discovery-result-actions">
                        ${!inLibrary ? `
                            <button class="btn btn-sm btn-secondary" disabled title="Coming soon - feature in development">
                                <i class="fas fa-plus"></i> Add to Library
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-secondary" onclick="window.paperManager.showPaperDetails(${paper.library_paper_id})">
                                <i class="fas fa-eye"></i> View in Library
                            </button>
                        `}
                        ${paper.url ? `
                            <a href="${paper.url}" target="_blank" class="btn btn-sm btn-secondary">
                                <i class="fas fa-external-link-alt"></i> View Original
                            </a>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        
        // Add "Show More" button if there are more results
        if (visibleCount < papers.length) {
            const remaining = papers.length - visibleCount;
            html += `
                <div class="discovery-show-more">
                    <button class="btn btn-secondary" onclick="window.paperManager.showMoreDiscoveryResults(${paperId})">
                        <i class="fas fa-chevron-down"></i> Show ${remaining} More ${remaining === 1 ? 'Paper' : 'Papers'}
                    </button>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }
    
    showMoreDiscoveryResults(paperId) {
        const container = document.getElementById('discovery-results');
        if (!container) return;
        
        // Increase visible count by 3
        this.discoveryVisibleCount += 3;
        
        // Re-render with new count
        this.renderDiscoveryResults(paperId, container, this.currentDiscoveryResults.length);
    }
    
    async addDiscoveredPaper(currentPaperId, resultIndex) {
        try {
            const paper = this.currentDiscoveryResults[resultIndex];
            if (!paper) {
                UIComponents.showNotification('Paper data not found', 'error');
                return;
            }
            
            // Add paper to library via API
            const addedPaper = await API.ai.addDiscoveredPaper({
                title: paper.title,
                authors: paper.authors,
                year: paper.year,
                abstract: paper.abstract,
                doi: paper.doi,
                journal: paper.journal,
                url: paper.url,
                source: paper.source,
                citation_count: paper.citation_count
            });
            
            UIComponents.showNotification(`Paper \"${paper.title}\" added to library!`, 'success');
            
            // Refresh the discovery results to update the status
            await this.discoverSimilarPapers(currentPaperId);
            
            // Reload papers list
            await this.loadPapers();
            
        } catch (error) {
            console.error('Error adding discovered paper:', error);
            UIComponents.showNotification('Failed to add paper to library', 'error');
        }
    }
    
    async generateSummary(paperId, autoTriggered = false) {
        try {
            // Mark as generating
            this.activeSummaryTasks.add(paperId);
            
            // Refresh UI to show generating state
            await this.showPaperDetails(paperId);
            
            if (!autoTriggered) {
                UIComponents.showNotification('Generating AI summary...', 'info');
            }
            const response = await API.ai.generateSummary(paperId);
            const taskId = response.task_id;
            
            // Poll for task completion
            await this.pollTaskStatus(taskId, paperId, autoTriggered);
        } catch (error) {
            console.error('Error generating summary:', error);
            this.activeSummaryTasks.delete(paperId);
            UIComponents.showNotification('Failed to generate summary', 'error');
        }
    }

    async pollTaskStatus(taskId, paperId, autoTriggered = false, maxAttempts = 60) {
        let attempts = 0;
        
        const poll = async () => {
            try {
                attempts++;
                const status = await API.ai.getTaskStatus(taskId);
                
                console.log('Poll attempt', attempts, 'for task', taskId, '- Status:', status);
                
                if (status.status === 'completed') {
                    console.log('Task completed! Refreshing paper details...');
                    
                    // Remove from active tasks
                    this.activeSummaryTasks.delete(paperId);
                    
                    if (!autoTriggered) {
                        UIComponents.showNotification('Summary generated successfully!', 'success');
                    }
                    
                    // Force reload paper details to show new summary
                    const paper = await API.papers.get(paperId);
                    console.log('Reloaded paper data:', paper);
                    
                    await this.showPaperDetails(paperId);
                    
                    // Also reload the papers list to update the card
                    await this.loadPapers();
                    
                    return;
                } else if (status.status === 'failed' || status.status === 'error') {
                    console.log('Task failed:', status.error);
                    
                    // Remove from active tasks
                    this.activeSummaryTasks.delete(paperId);
                    
                    UIComponents.showNotification(`Summary generation failed: ${status.error || 'Unknown error'}`, 'error');
                    
                    // Still reload to show the knowledge check badge
                    await this.showPaperDetails(paperId);
                    await this.loadPapers();
                    
                    return;
                } else if (attempts >= maxAttempts) {
                    console.log('Task polling timed out after', attempts, 'attempts');
                    UIComponents.showNotification('Summary generation timed out. Please refresh the page later.', 'warning');
                    return;
                }
                
                // Update progress message in the tabs if available
                if (status.message && autoTriggered) {
                    const summaryAction = document.querySelector('.summary-status');
                    if (summaryAction) {
                        const messageText = summaryAction.querySelector('span');
                        if (messageText) {
                            messageText.textContent = status.message;
                        }
                    }
                }
                
                // Poll again after 2 seconds
                setTimeout(poll, 2000);
            } catch (error) {
                console.error('Error polling task status:', error);
                if (attempts < maxAttempts) {
                    setTimeout(poll, 2000);
                } else {
                    UIComponents.showNotification('Failed to check summary status', 'error');
                }
            }
        };
        
        // Start polling
        poll();
    }
    
    async fetchExternalCitations(paperId) {
        try {
            UIComponents.showNotification('Fetching external citations...', 'info');
            const result = await API.citations.fetchExternalCitations(paperId);
            UIComponents.showNotification(`Found ${result.external_citations} external citations`, 'success');
            await this.showPaperDetails(paperId);
        } catch (error) {
            console.error('Error fetching citations:', error);
            UIComponents.showNotification('Failed to fetch external citations', 'error');
        }
    }
    
    async calculateInfluence(paperId) {
        try {
            UIComponents.showNotification('Calculating influence score...', 'info');
            const result = await API.citations.calculateInfluence(paperId);
            UIComponents.showNotification(`Influence score: ${result.influence_score.toFixed(3)}`, 'success');
            await this.showPaperDetails(paperId);
        } catch (error) {
            console.error('Error calculating influence:', error);
            UIComponents.showNotification('Failed to calculate influence', 'error');
        }
    }
    
    async showCitations(paperId) {
        try {
            const citations = await API.citations.getPaperCitations(paperId);
            // TODO: Show citations in a modal or expand section
            console.log('Citations:', citations);
            alert(`This paper has ${citations.citation_count} citations and references ${citations.reference_count} papers`);
        } catch (error) {
            console.error('Error loading citations:', error);
            UIComponents.showNotification('Failed to load citations', 'error');
        }
    }

    switchTab(event, tabId) {
        // Remove active class from all tabs and panes
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        
        // Add active class to clicked tab and corresponding pane
        event.currentTarget.classList.add('active');
        document.getElementById(tabId).classList.add('active');
    }

    generateAIExtractionInfo(paper) {
        if (!paper.extraction_status || paper.extraction_status === 'pending') {
            return '';
        }
        
        let aiSection = '<div class="ai-extraction-info">';
        aiSection += '<h4><i class="fas fa-robot"></i> AI Extraction Pipeline</h4>';
        
        if (paper.extraction_status === 'completed') {
            // Parse extraction metadata to show pipeline steps
            let pipelineSteps = [];
            let sources = [];
            
            try {
                const metadata = paper.extraction_metadata;
                const sourcesData = typeof paper.extraction_sources === 'string' 
                    ? JSON.parse(paper.extraction_sources) 
                    : paper.extraction_sources;
                
                if (Array.isArray(sourcesData)) {
                    sources = sourcesData;
                }
                
                // Determine pipeline steps based on sources (in actual execution order)
                
                // 1. PDF extraction (always first - extracts text from PDF)
                if (sources.some(s => s.toLowerCase().includes('pdf'))) {
                    pipelineSteps.push({
                        icon: 'fa-file-pdf',
                        label: 'PDF Extraction',
                        description: 'Direct text extraction',
                        type: 'success'
                    });
                }
                
                // 2. DOI discovery (found in extracted PDF text)
                if (metadata && metadata.doi_found) {
                    pipelineSteps.push({
                        icon: 'fa-fingerprint',
                        label: 'DOI Discovered',
                        description: metadata.doi || 'Found in PDF',
                        type: 'success'
                    });
                }
                
                // 3. API sources (queried with DOI or metadata)
                const apiSources = sources.filter(s => 
                    s.toLowerCase().includes('crossref') || 
                    s.toLowerCase().includes('arxiv') || 
                    s.toLowerCase().includes('semantic') ||
                    s.toLowerCase().includes('openalex')
                );
                
                if (apiSources.length > 0) {
                    // Format source names nicely
                    const formattedSources = apiSources.map(s => {
                        const lower = s.toLowerCase();
                        if (lower.includes('crossref')) return 'CrossRef';
                        if (lower.includes('semantic')) return 'Semantic Scholar';
                        if (lower.includes('openalex')) return 'OpenAlex';
                        if (lower.includes('arxiv')) return 'arXiv';
                        return s;
                    });
                    
                    // Remove duplicates
                    const uniqueSources = [...new Set(formattedSources)];
                    
                    pipelineSteps.push({
                        icon: 'fa-database',
                        label: 'API Data Retrieved',
                        description: uniqueSources.join(', '),
                        type: 'success'
                    });
                }
                
                // 4. LLM analysis (optional - for validation/enhancement)
                const llmSources = sources.filter(s => 
                    s.toLowerCase().includes('llm') || 
                    s.toLowerCase().includes('gpt') ||
                    s.toLowerCase().includes('openai')
                );
                
                if (llmSources.length > 0) {
                    pipelineSteps.push({
                        icon: 'fa-brain',
                        label: 'LLM Analysis',
                        description: 'AI-powered validation',
                        type: 'info'
                    });
                }
                
                // Note: Cross-validation happens throughout but isn't shown as separate step
                
            } catch (e) {
                console.error('Error parsing extraction metadata:', e);
            }
            
            // Display pipeline steps
            if (pipelineSteps.length > 0) {
                aiSection += '<div class="pipeline-steps">';
                pipelineSteps.forEach((step, idx) => {
                    aiSection += `
                        <div class="pipeline-step">
                            <div class="step-icon ${step.type}">
                                <i class="fas ${step.icon}"></i>
                            </div>
                            <div class="step-content">
                                <div class="step-label">${step.label}</div>
                                <div class="step-description">${step.description}</div>
                            </div>
                            ${idx < pipelineSteps.length - 1 ? '<div class="step-arrow"><i class="fas fa-arrow-right"></i></div>' : ''}
                        </div>
                    `;
                });
                aiSection += '</div>';
            } else {
                // Fallback if no metadata
                aiSection += '<div class="pipeline-simple"><i class="fas fa-check-circle"></i> Metadata extracted successfully</div>';
            }
            
        } else if (paper.extraction_status === 'failed') {
            aiSection += '<div class="ai-error">';
            aiSection += '<p><i class="fas fa-exclamation-triangle"></i> AI extraction failed. This paper was entered manually.</p>';
            aiSection += '</div>';
        }
        
        aiSection += '</div>';
        return aiSection;
    }

    async showPaperDetailsWithExtraction(paperId, taskId = null) {
        try {
            const paper = await API.papers.get(paperId);
            
            // If processing AND we have a valid taskId, start polling
            if (paper.extraction_status === 'processing' && taskId && taskId !== 'undefined') {
                // Start polling for updates
                this.startMetadataPollingForDetails(paperId, taskId);
            }
            
            // Show the details modal
            await this.showPaperDetails(paperId);
            
        } catch (error) {
            console.error('Error loading paper details with extraction:', error);
            UIComponents.showNotification('Failed to load paper details', 'error');
        }
    }

    startMetadataPollingForDetails(paperId, taskId) {
        // Clear any existing polling
        if (this.detailsPollingInterval) {
            clearInterval(this.detailsPollingInterval);
        }

        const pollInterval = 2000; // 2 seconds
        const maxAttempts = 90; // 3 minutes max
        let attempts = 0;
        let summaryTaskChecked = false;

        this.detailsPollingInterval = setInterval(async () => {
            attempts++;
            
            try {
                const paper = await API.papers.get(paperId);
                
                if (paper.extraction_status === 'completed' || paper.extraction_status === 'failed') {
                    // Stop metadata polling
                    clearInterval(this.detailsPollingInterval);
                    this.detailsPollingInterval = null;
                    
                    if (paper.extraction_status === 'completed') {
                        UIComponents.showNotification('Metadata extraction completed!', 'success');
                    }
                    
                    // Reload papers list
                    await this.loadPapers();
                    
                    // Check for summary task and start polling once
                    if (!summaryTaskChecked) {
                        summaryTaskChecked = true;
                        try {
                            const taskStatus = await API.ai.getTaskStatus(taskId);
                            
                            if (taskStatus.status === 'completed' && taskStatus.result && taskStatus.result.summary_task_id) {
                                const summaryTaskId = taskStatus.result.summary_task_id;
                                console.log('Starting summary polling for task:', summaryTaskId);
                                
                                // Mark as generating and refresh modal to show the banner
                                this.activeSummaryTasks.add(paperId);
                                await this.showPaperDetails(paperId);
                                
                                // Start polling for summary generation (will auto-refresh modal when done)
                                this.pollTaskStatus(summaryTaskId, paperId, true);
                            } else {
                                console.log('No summary task found or task not completed yet');
                            }
                        } catch (error) {
                            console.error('Error checking for summary task:', error);
                        }
                    }
                    
                    return;
                }
                
            } catch (error) {
                console.error('Error polling paper metadata:', error);
            }
            
            // Stop polling after max attempts
            if (attempts >= maxAttempts) {
                clearInterval(this.detailsPollingInterval);
                this.detailsPollingInterval = null;
                UIComponents.showNotification('Extraction is taking longer than expected', 'warning');
            }
        }, pollInterval);
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
            document.getElementById('paper-edit-publisher').value = paper.publisher || '';
            document.getElementById('paper-edit-booktitle').value = paper.booktitle || '';
            document.getElementById('paper-edit-volume').value = paper.volume || '';
            document.getElementById('paper-edit-issue').value = paper.issue || '';
            document.getElementById('paper-edit-pages').value = paper.pages || '';
            document.getElementById('paper-edit-doi').value = paper.doi || '';
            document.getElementById('paper-edit-url').value = paper.url || '';
            document.getElementById('paper-edit-isbn').value = paper.isbn || '';
            document.getElementById('paper-edit-abstract').value = paper.abstract || '';
            document.getElementById('paper-edit-keywords').value = paper.keywords || '';
            
            UIComponents.showModal('paper-edit-modal');
        } catch (error) {
            console.error('Error loading paper for editing:', error);
            UIComponents.showNotification('Failed to load paper details', 'error');
        }
    }

    async editPaperWithExtraction(paperId, taskId = null) {
        try {
            const paper = await API.papers.get(paperId);
            this.currentEditingId = paperId;
            
            // Fill the form with paper data
            document.getElementById('paper-edit-title-input').value = paper.title || '';
            document.getElementById('paper-edit-authors').value = paper.authors || '';
            document.getElementById('paper-edit-year').value = paper.year || '';
            document.getElementById('paper-edit-journal').value = paper.journal || '';
            document.getElementById('paper-edit-publisher').value = paper.publisher || '';
            document.getElementById('paper-edit-booktitle').value = paper.booktitle || '';
            document.getElementById('paper-edit-volume').value = paper.volume || '';
            document.getElementById('paper-edit-issue').value = paper.issue || '';
            document.getElementById('paper-edit-pages').value = paper.pages || '';
            document.getElementById('paper-edit-doi').value = paper.doi || '';
            document.getElementById('paper-edit-url').value = paper.url || '';
            document.getElementById('paper-edit-isbn').value = paper.isbn || '';
            document.getElementById('paper-edit-abstract').value = paper.abstract || '';
            document.getElementById('paper-edit-keywords').value = paper.keywords || '';
            
            // Show extraction status banner if processing
            const modal = document.getElementById('paper-edit-modal');
            let statusBanner = modal.querySelector('.extraction-status-banner');
            if (!statusBanner) {
                statusBanner = document.createElement('div');
                statusBanner.className = 'extraction-status-banner';
                const modalBody = modal.querySelector('.modal-body');
                modalBody.insertBefore(statusBanner, modalBody.firstChild);
            }
            
            if (paper.extraction_status === 'processing' || taskId) {
                // Set fields as disabled and show processing state
                this.setExtractionState('processing');
                statusBanner.innerHTML = `
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Extracting metadata...</span>
                `;
                statusBanner.className = 'extraction-status-banner processing';
                statusBanner.style.display = 'flex';
                
                // Start polling for updates
                this.startMetadataPolling(paperId, taskId);
            } else if (paper.extraction_status === 'completed') {
                statusBanner.innerHTML = `
                    <i class="fas fa-check-circle"></i>
                    <span>Extraction completed!</span>
                `;
                statusBanner.className = 'extraction-status-banner completed';
                statusBanner.style.display = 'flex';
                this.setExtractionState('completed');
                
                // Auto-hide completed banner after 5 seconds
                setTimeout(() => {
                    statusBanner.style.display = 'none';
                }, 5000);
            } else {
                statusBanner.style.display = 'none';
                this.setExtractionState('completed');
            }
            
            UIComponents.showModal('paper-edit-modal');
        } catch (error) {
            console.error('Error loading paper for editing:', error);
            UIComponents.showNotification('Failed to load paper details', 'error');
        }
    }

    async reExtractWithLLM(paperId, event) {
        // Stop event propagation to prevent card actions
        if (event) {
            event.stopPropagation();
            event.preventDefault();
        }
        
        try {
            UIComponents.showNotification('Re-extracting with LLM...', 'info');
            
            // Trigger re-extraction
            const result = await API.papers.reExtract(paperId, true);
            
            // Reload the papers list to show processing state
            await this.loadPapers();
            
            // Start polling for completion and reload when done
            this.startReExtractPolling(paperId);
            
            UIComponents.showNotification('High-accuracy extraction started!', 'success');
        } catch (error) {
            console.error('Error starting re-extraction:', error);
            UIComponents.showNotification('Failed to start re-extraction: ' + error.message, 'error');
        }
    }

    startReExtractPolling(paperId) {
        // Clear any existing polling
        if (this.reExtractPollingInterval) {
            clearInterval(this.reExtractPollingInterval);
        }

        const pollInterval = 2000; // 2 seconds
        const maxAttempts = 90; // 3 minutes max
        let attempts = 0;

        this.reExtractPollingInterval = setInterval(async () => {
            attempts++;
            
            try {
                const paper = await API.papers.get(paperId);
                
                if (paper.extraction_status === 'completed' || paper.extraction_status === 'failed') {
                    // Stop polling and reload papers
                    clearInterval(this.reExtractPollingInterval);
                    this.reExtractPollingInterval = null;
                    
                    // Reload the papers list to show updated results
                    await this.loadPapers();
                    
                    if (paper.extraction_status === 'completed') {
                        UIComponents.showNotification(
                            `Extraction completed! (Confidence: ${Math.round((paper.extraction_confidence || 0) * 100)}%)`,
                            'success'
                        );
                    } else {
                        UIComponents.showNotification('Extraction failed', 'warning');
                    }
                }
                
            } catch (error) {
                console.error('Error polling re-extraction:', error);
            }
            
            // Stop polling after max attempts
            if (attempts >= maxAttempts) {
                clearInterval(this.reExtractPollingInterval);
                this.reExtractPollingInterval = null;
                UIComponents.showNotification('Extraction is taking longer than expected', 'warning');
                // Still reload to show current state
                await this.loadPapers();
            }
        }, pollInterval);
    }

    setExtractionState(state) {
        const fields = [
            'paper-edit-title-input',
            'paper-edit-authors',
            'paper-edit-year',
            'paper-edit-journal',
            'paper-edit-doi',
            'paper-edit-abstract',
            'paper-edit-keywords'
        ];
        
        fields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                if (state === 'processing') {
                    field.classList.add('extracting');
                    field.disabled = true;
                } else {
                    field.classList.remove('extracting');
                    field.disabled = false;
                }
            }
        });
    }

    async startMetadataPolling(paperId, taskId) {
        // Stop any existing polling
        if (this.metadataPollingInterval) {
            clearInterval(this.metadataPollingInterval);
        }
        
        const pollInterval = 2000; // 2 seconds
        const maxAttempts = 90; // 3 minutes
        let attempts = 0;
        
        this.metadataPollingInterval = setInterval(async () => {
            attempts++;
            
            try {
                // Fetch updated paper data
                const paper = await API.papers.get(paperId);
                
                // Update form fields with new data (only if changed)
                this.updateFieldIfChanged('paper-edit-title-input', paper.title);
                this.updateFieldIfChanged('paper-edit-authors', paper.authors);
                this.updateFieldIfChanged('paper-edit-year', paper.year);
                this.updateFieldIfChanged('paper-edit-journal', paper.journal);
                this.updateFieldIfChanged('paper-edit-doi', paper.doi);
                this.updateFieldIfChanged('paper-edit-abstract', paper.abstract);
                this.updateFieldIfChanged('paper-edit-keywords', paper.keywords);
                
                // Check if extraction is complete
                if (paper.extraction_status === 'completed') {
                    clearInterval(this.metadataPollingInterval);
                    this.setExtractionState('completed');
                    
                    // Update status banner
                    const modal = document.getElementById('paper-edit-modal');
                    const statusBanner = modal.querySelector('.extraction-status-banner');
                    if (statusBanner) {
                        statusBanner.innerHTML = `
                            <i class="fas fa-check-circle"></i>
                            <span>AI extraction completed! (Confidence: ${Math.round((paper.extraction_confidence || 0) * 100)}%)</span>
                        `;
                        statusBanner.className = 'extraction-status-banner completed';
                        
                        // Auto-hide after 5 seconds
                        setTimeout(() => {
                            statusBanner.style.display = 'none';
                        }, 5000);
                    }
                    
                    UIComponents.showNotification('AI extraction completed!', 'success');
                    
                    // Refresh paper list
                    if (window.paperManager) window.paperManager.loadPapers();
                    
                } else if (paper.extraction_status === 'failed') {
                    clearInterval(this.metadataPollingInterval);
                    this.setExtractionState('completed');
                    
                    // Update status banner
                    const modal = document.getElementById('paper-edit-modal');
                    const statusBanner = modal.querySelector('.extraction-status-banner');
                    if (statusBanner) {
                        statusBanner.innerHTML = `
                            <i class="fas fa-exclamation-triangle"></i>
                            <span>AI extraction failed. You can edit the metadata manually.</span>
                        `;
                        statusBanner.className = 'extraction-status-banner failed';
                    }
                    
                    UIComponents.showNotification('AI extraction failed', 'warning');
                }
                
            } catch (error) {
                console.error('Error polling paper metadata:', error);
            }
            
            // Stop polling after max attempts
            if (attempts >= maxAttempts) {
                clearInterval(this.metadataPollingInterval);
                this.setExtractionState('completed');
                UIComponents.showNotification('AI extraction timed out', 'warning');
            }
        }, pollInterval);
    }

    updateFieldIfChanged(fieldId, newValue) {
        const field = document.getElementById(fieldId);
        if (field && newValue && field.value !== String(newValue)) {
            // Add a subtle animation when updating
            field.classList.add('field-updated');
            field.value = newValue;
            setTimeout(() => {
                field.classList.remove('field-updated');
            }, 1000);
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
            publisher: document.getElementById('paper-edit-publisher').value.trim() || null,
            booktitle: document.getElementById('paper-edit-booktitle').value.trim() || null,
            volume: document.getElementById('paper-edit-volume').value.trim() || null,
            issue: document.getElementById('paper-edit-issue').value.trim() || null,
            pages: document.getElementById('paper-edit-pages').value.trim() || null,
            doi: document.getElementById('paper-edit-doi').value.trim() || null,
            url: document.getElementById('paper-edit-url').value.trim() || null,
            isbn: document.getElementById('paper-edit-isbn').value.trim() || null,
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
        console.log('DEBUG: deletePaper called with ID:', paperId);
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

    async exportBibtex(paperId) {
        try {
            // Use fetch directly for text response (not JSON)
            const apiKey = ApiKeyManager.getApiKey();
            const response = await fetch(`/api/papers/${paperId}/bibtex`, {
                method: 'GET',
                headers: {
                    'X-API-Key': apiKey
                }
            });
            
            if (response.ok) {
                const bibtexContent = await response.text();
                
                // Create download
                const blob = new Blob([bibtexContent], { type: 'application/x-bibtex' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `paper_${paperId}.bib`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                UIComponents.showNotification('BibTeX exported successfully', 'success');
            } else {
                const errorText = await response.text();
                console.error('BibTeX export failed:', errorText);
                throw new Error('Failed to export BibTeX');
            }
        } catch (error) {
            console.error('Error exporting BibTeX:', error);
            UIComponents.showNotification('Failed to export BibTeX', 'error');
        }
    }
    
    async organizePdf(paperId) {
        try {
            UIComponents.showNotification('Organizing PDF filename...', 'info');
            
            const result = await API.request(`/papers/${paperId}/organize-pdf`, {
                method: 'POST'
            });
            
            if (result.success) {
                UIComponents.showNotification(
                    `PDF renamed to: ${result.filename}`,
                    'success',
                    5000
                );
                
                // Refresh the paper details to show updated info
                await this.showPaperDetails(paperId);
            }
        } catch (error) {
            console.error('Error organizing PDF:', error);
            const message = error.message || 'Failed to organize PDF filename';
            UIComponents.showNotification(message, 'error');
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
        const addButton = document.getElementById('add-collection-btn');
        if (addButton) {
            addButton.addEventListener('click', () => this.showCreateModal());
        }

        const deleteAllButton = document.getElementById('delete-all-collections-btn');
        if (deleteAllButton) {
            deleteAllButton.addEventListener('click', () => this.deleteAllCollections());
        }

        const reclassifyAllButton = document.getElementById('reclassify-all-btn');
        if (reclassifyAllButton) {
            reclassifyAllButton.addEventListener('click', () => this.reclassifyAllPapers());
        }

        const collectionForm = document.getElementById('collection-form');
        if (collectionForm) {
            collectionForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveCollection();
            });
        } else {
            console.warn('CollectionManager: collection-form not found');
        }
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
                // Add click handler to view papers
                card.style.cursor = 'pointer';
                card.addEventListener('click', (e) => {
                    // Don't trigger if clicking action buttons
                    if (!e.target.closest('.action-btn')) {
                        this.viewCollectionPapers(collection.id);
                    }
                });
                container.appendChild(card);
            });
        }
    }

    async viewCollectionPapers(collectionId, event = null) {
        if (event) {
            event.stopPropagation();
        }
        
        try {
            const collection = await API.collections.get(collectionId);
            const modal = document.getElementById('collection-papers-modal') || this.createCollectionPapersModal();
            const content = document.getElementById('collection-papers-content');
            
            content.innerHTML = `
                <div class="collection-header">
                    <h3>
                        ${collection.is_smart ? '<i class="fas fa-brain" style="color: #764ba2;"></i>' : '<i class="fas fa-folder"></i>'}
                        ${Utils.sanitizeHtml(collection.name)}
                    </h3>
                </div>
                ${collection.description ? `<p class="collection-description" style="margin-top: 0.5rem; margin-bottom: 1rem; color: #666;">${Utils.sanitizeHtml(collection.description)}</p>` : ''}
                    <div class="collection-meta">
                        <span><i class="fas fa-file-pdf"></i> ${collection.papers ? collection.papers.length : 0} papers</span>
                        ${collection.is_smart ? '<span class="smart-badge"><i class="fas fa-brain"></i> Smart Collection</span>' : ''}
                    </div>
                </div>
                
                <div class="collection-papers-list">
                    ${collection.papers && collection.papers.length > 0 ? 
                        collection.papers.map(paper => `
                            <div class="collection-paper-item" onclick="window.paperManager.showPaperDetails(${paper.id}); UIComponents.hideModal('collection-papers-modal');">
                                <div class="paper-title-area">
                                    <h4>${Utils.sanitizeHtml(paper.title)}</h4>
                                    <p class="paper-authors">${Utils.sanitizeHtml(paper.authors)}</p>
                                </div>
                                <div class="paper-meta-area">
                                    ${paper.year ? `<span class="year">${paper.year}</span>` : ''}
                                    ${paper.journal ? `<span class="journal">${Utils.sanitizeHtml(paper.journal)}</span>` : ''}
                                </div>
                            </div>
                        `).join('') 
                        : '<p class="empty-message">No papers in this collection yet</p>'
                    }
                </div>
            `;
            
            UIComponents.showModal('collection-papers-modal');
        } catch (error) {
            console.error('Error loading collection papers:', error);
            UIComponents.showNotification('Failed to load collection papers', 'error');
        }
    }

    createCollectionPapersModal() {
        const modal = document.createElement('div');
        modal.id = 'collection-papers-modal';
        modal.className = 'modal large';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Collection Papers</h2>
                    <button class="close-btn" onclick="UIComponents.hideModal('collection-papers-modal')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body" id="collection-papers-content"></div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
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

    async deleteAllCollections() {
        const confirmed = await UIComponents.confirm(
            'Are you sure you want to delete ALL collections? This action cannot be undone.'
        );
        if (!confirmed) return;

        try {
            // Delete all regular collections
            const deletePromises = this.collections
                .filter(c => !c.is_smart)
                .map(c => API.collections.delete(c.id));
            
            await Promise.all(deletePromises);

            // Clear smart collections
            const smartCollectionsEnabled = await API.smartCollections.getStatus();
            if (smartCollectionsEnabled && smartCollectionsEnabled.enabled) {
                await API.smartCollections.clear();
            }

            UIComponents.showNotification('All collections deleted successfully', 'success');
            this.loadCollections();
            
            // Update dashboard stats and smart collections display
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
                window.dashboardManager.loadSmartCollectionsStatus();
            }
        } catch (error) {
            console.error('Error deleting all collections:', error);
            UIComponents.showNotification('Failed to delete all collections: ' + error.message, 'error');
        }
    }

    async reclassifyAllPapers() {
        const confirmed = await UIComponents.confirm(
            'Re-classify all papers with smart collections? This may take several minutes depending on the number of papers.'
        );
        if (!confirmed) return;

        try {
            const result = await API.smartCollections.classifyAll();
            
            if (result.task_ids && result.task_ids.length > 0) {
                UIComponents.showNotification(
                    `Started re-classification of ${result.task_ids.length} papers. This will run in the background.`,
                    'success'
                );
            } else {
                UIComponents.showNotification('No papers to classify', 'info');
            }

            // Reload collections and papers after a short delay to show initial results
            setTimeout(() => {
                this.loadCollections();
                if (window.dashboardManager) {
                    window.dashboardManager.loadSmartCollectionsStatus();
                }
                if (window.paperManager) {
                    window.paperManager.loadPapers();
                }
            }, 3000);
        } catch (error) {
            console.error('Error re-classifying papers:', error);
            UIComponents.showNotification('Failed to start re-classification: ' + error.message, 'error');
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
        const tagForm = document.getElementById('tag-form');
        if (tagForm) {
            tagForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveTag();
            });
        } else {
            console.warn('TagManager: tag-form not found');
        }

        const tagColor = document.getElementById('tag-color');
        const colorPreview = document.getElementById('color-preview');
        if (tagColor && colorPreview) {
            tagColor.addEventListener('change', (e) => {
                colorPreview.style.background = e.target.value;
            });
        } else {
            console.warn('TagManager: tag-color or color-preview not found');
        }
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