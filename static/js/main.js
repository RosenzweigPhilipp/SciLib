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
        this.currentPage = 1;
        this.itemsPerPage = 20;
        this.totalPapers = 0;
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
        console.log('DEBUG: showPaperDetails called with ID:', paperId);
        try {
            const paper = await API.papers.get(paperId);
            const modal = document.getElementById('paper-details-modal');
            const content = document.getElementById('paper-details-content');
            
            // Generate AI extraction info
            const aiInfo = this.generateAIExtractionInfo(paper);
            
            // Add extraction status banner if processing
            const statusBanner = paper.extraction_status === 'processing' ? `
                <div class="extraction-status-banner processing" style="margin-bottom: 1rem;">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Extracting metadata...</span>
                </div>
            ` : '';
            
            content.innerHTML = `
                ${statusBanner}
                <div class="paper-header">
                    <h3>${Utils.sanitizeHtml(paper.title)}</h3>
                    <div class="authors">${Utils.sanitizeHtml(paper.authors)}</div>
                    <div style="margin-top: 0.5rem;">
                        ${UIComponents.getAIStatusBadge(paper)}
                    </div>
                </div>
                
                <div class="paper-meta-grid">
                    ${paper.year ? `<div class="meta-item"><label>Year</label><value>${paper.year}</value></div>` : ''}
                    ${paper.journal ? `<div class="meta-item"><label>Journal</label><value>${Utils.sanitizeHtml(paper.journal)}</value></div>` : ''}
                    ${paper.doi ? `<div class="meta-item"><label>DOI</label><value>${Utils.sanitizeHtml(paper.doi)}</value></div>` : ''}
                    <div class="meta-item"><label>Uploaded</label><value>${Utils.formatDate(paper.created_at)}</value></div>
                    ${paper.extracted_at ? `<div class="meta-item"><label>AI Extracted</label><value>${Utils.formatDate(paper.extracted_at)}</value></div>` : ''}
                </div>
                
                ${aiInfo}
                
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

    generateAIExtractionInfo(paper) {
        if (!paper.extraction_status || paper.extraction_status === 'pending') {
            return '';
        }
        
        let aiSection = '<div class="ai-extraction-info">';
        aiSection += '<h4><i class="fas fa-robot"></i> AI Extraction Details</h4>';
        
        if (paper.extraction_status === 'completed') {
            aiSection += `<div class="ai-stats">`;
            aiSection += `<div class="ai-stat"><label>Confidence</label><value>${Math.round((paper.extraction_confidence || 0) * 100)}%</value></div>`;
            
            if (paper.extraction_sources) {
                try {
                    const sources = typeof paper.extraction_sources === 'string' 
                        ? JSON.parse(paper.extraction_sources) 
                        : paper.extraction_sources;
                    if (Array.isArray(sources) && sources.length > 0) {
                        aiSection += `<div class="ai-stat"><label>Sources</label><value>${sources.join(', ')}</value></div>`;
                    }
                } catch (e) {
                    // Ignore JSON parse errors
                }
            }
            aiSection += `</div>`;
            
            if (paper.extraction_metadata) {
                try {
                    const metadata = typeof paper.extraction_metadata === 'string' 
                        ? JSON.parse(paper.extraction_metadata) 
                        : paper.extraction_metadata;
                    if (metadata && Object.keys(metadata).length > 0) {
                        aiSection += '<div class="ai-metadata">';
                        aiSection += '<p><em>This papers metadata was automatically extracted using AI from PDF content and scientific databases.</em></p>';
                        aiSection += '</div>';
                    }
                } catch (e) {
                    // Ignore JSON parse errors
                }
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
        console.log('DEBUG: showPaperDetailsWithExtraction called with ID:', paperId, 'taskId:', taskId);
        try {
            const paper = await API.papers.get(paperId);
            
            // If processing, start polling and then show details
            if (paper.extraction_status === 'processing' || taskId) {
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

        this.detailsPollingInterval = setInterval(async () => {
            attempts++;
            
            try {
                const paper = await API.papers.get(paperId);
                
                if (paper.extraction_status === 'completed' || paper.extraction_status === 'failed') {
                    // Stop polling and refresh the details view
                    clearInterval(this.detailsPollingInterval);
                    this.detailsPollingInterval = null;
                    
                    // Refresh the details modal if it's still open
                    const modal = document.getElementById('paper-details-modal');
                    if (modal && modal.classList.contains('active')) {
                        await this.showPaperDetails(paperId);
                        
                        if (paper.extraction_status === 'completed') {
                            UIComponents.showNotification('Metadata extraction completed!', 'success');
                        }
                    }
                    
                    // Reload papers list to show updated metadata
                    await this.loadPapers();
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
        console.log('DEBUG: editPaper called with ID:', paperId);
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

    async editPaperWithExtraction(paperId, taskId = null) {
        console.log('DEBUG: editPaperWithExtraction called with ID:', paperId, 'taskId:', taskId);
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
}

// Collection Manager
class CollectionManager {
    constructor() {
        this.collections = [];
        this.currentEditingId = null;
        this.setupCollectionHandlers();
    }

    setupCollectionHandlers() {
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