// UI Components and Utilities
class UIComponents {
    // Show notification
    static showNotification(message, type = 'info', duration = 5000) {
        const notification = document.getElementById('notification');
        const icon = notification.querySelector('.notification-icon');
        const messageEl = notification.querySelector('.notification-message');

        // Set icon based on type
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        icon.className = `notification-icon ${icons[type] || icons.info}`;
        messageEl.textContent = message;
        notification.className = `notification ${type} show`;

        // Auto hide
        setTimeout(() => {
            notification.classList.remove('show');
        }, duration);
    }

    // Show/Hide loading state
    static setLoading(element, isLoading = true) {
        if (isLoading) {
            element.innerHTML = '<div class="loading">Loading</div>';
        }
    }

    // Create paper card
    static createPaperCard(paper) {
        const card = document.createElement('div');
        card.className = 'paper-card';
        
        // Generate AI extraction status badge
        const aiStatus = UIComponents.getAIStatusBadge(paper);
        
        // Generate collection badges
        let collectionBadges = '';
        if (paper.collections && paper.collections.length > 0) {
            collectionBadges = '<div class="paper-collections">' +
                paper.collections.slice(0, 3).map(c => 
                    `<span class="collection-badge${c.is_smart ? ' smart-collection' : ''}" title="${Utils.sanitizeHtml(c.name)}">
                        ${c.is_smart ? '<i class="fas fa-brain"></i> ' : ''}${Utils.sanitizeHtml(c.name)}
                    </span>`
                ).join('') +
                (paper.collections.length > 3 ? `<span class="collection-badge more">+${paper.collections.length - 3} more</span>` : '') +
                '</div>';
        }
        
        card.innerHTML = `
            <div class="paper-header-row">
                <div class="paper-title" onclick="window.paperManager && window.paperManager.showPaperDetails(${paper.id})">
                    ${Utils.sanitizeHtml(paper.title)}
                </div>
                ${aiStatus}
            </div>
            <div class="paper-authors">${Utils.sanitizeHtml(paper.authors)}</div>
            ${collectionBadges}
            ${paper.abstract ? `<div class="paper-abstract-preview">${Utils.truncateText(paper.abstract)}</div>` : ''}
            <div class="paper-meta">
                <div>
                    ${paper.year ? `<span class="year">${paper.year}</span>` : ''}
                    ${paper.journal ? `<span class="journal">${Utils.sanitizeHtml(paper.journal)}</span>` : ''}
                    ${paper.extraction_confidence ? `<span class="ai-confidence" title="AI Extraction Confidence">${Math.round(paper.extraction_confidence * 100)}% AI</span>` : ''}
                </div>
                <div class="paper-actions">
                    <button class="action-btn view-btn" data-paper-id="${paper.id}" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn edit-btn" data-paper-id="${paper.id}" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete-btn" data-paper-id="${paper.id}" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
        return card;
    }

    // Get AI extraction status badge
    static getAIStatusBadge(paper) {
        if (!paper.extraction_status) {
            return '<span class="ai-badge ai-pending" title="Manual Entry"><i class="fas fa-user"></i> Manual</span>';
        }
        
        switch (paper.extraction_status) {
            case 'completed':
                const confidence = paper.extraction_confidence || 0;
                const confidenceClass = confidence > 0.8 ? 'high' : confidence > 0.5 ? 'medium' : 'low';
                return `<span class="ai-badge ai-completed ai-confidence-${confidenceClass} ai-badge-clickable" 
                    onclick="window.paperManager && window.paperManager.reExtractWithLLM(${paper.id}, event)" 
                    title="Click to re-extract with LLM (higher accuracy)">
                    <i class="fas fa-robot"></i> AI ${Math.round(confidence * 100)}%
                </span>`;
            case 'processing':
                return '<span class="ai-badge ai-processing" title="AI pipeline running..."><i class="fas fa-spinner fa-spin"></i> Extracting</span>';
            case 'failed':
                return `<span class="ai-badge ai-failed ai-badge-clickable" 
                    onclick="window.paperManager && window.paperManager.reExtractWithLLM(${paper.id}, event)" 
                    title="Click to retry with LLM">
                    <i class="fas fa-exclamation-triangle"></i> Failed
                </span>`;
            case 'pending':
            default:
                return '<span class="ai-badge ai-pending" title="Pending Extraction"><i class="fas fa-clock"></i> Pending</span>';
        }
    }

    // Create collection card
    static createCollectionCard(collection) {
        const card = document.createElement('div');
        card.className = 'collection-badge-card';
        if (collection.is_smart) {
            card.classList.add('smart');
        }
        
        // Store description for modal display
        card.dataset.description = collection.description || '';
        card.dataset.collectionId = collection.id;
        
        card.innerHTML = `
            <div class="collection-badge-content">
                ${collection.is_smart ? '<i class="fas fa-brain"></i>' : '<i class="fas fa-folder"></i>'}
                <span class="collection-badge-name">${Utils.sanitizeHtml(collection.name)}</span>
            </div>
            <div class="collection-badge-actions">
                <button class="badge-action-btn" onclick="event.stopPropagation(); window.collectionManager && window.collectionManager.editCollection(${collection.id})" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="badge-action-btn" onclick="event.stopPropagation(); window.collectionManager && window.collectionManager.deleteCollection(${collection.id})" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        return card;
    }

    // Create tag item
    static createTagItem(tag) {
        const item = document.createElement('div');
        item.className = 'tag-item';
        item.innerHTML = `
            <div class="tag-info">
                <div class="tag-color" style="background-color: ${tag.color}"></div>
                <span class="tag-name">${Utils.sanitizeHtml(tag.name)}</span>
            </div>
                <div class="tag-actions">
                <button class="action-btn" onclick="window.tagManager && window.tagManager.editTag(${tag.id})" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn" onclick="window.tagManager && window.tagManager.deleteTag(${tag.id})" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        return item;
    }

    // Modal utilities
    static showModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    static hideModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    // Clear form
    static clearForm(formId) {
        const form = document.getElementById(formId);
        form.reset();
    }

    // Confirm dialog
    static async confirm(message) {
        return new Promise((resolve) => {
            const result = window.confirm(message);
            resolve(result);
        });
    }
}

// Upload Manager
class UploadManager {
    constructor() {
        try {
            this.setupUploadHandlers();
        } catch (e) {
            console.error('UploadManager initialization failed', e);
        }
    }

    setupUploadHandlers() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const browseBtn = document.getElementById('browse-btn');

        if (!uploadArea) console.warn('UploadManager: upload-area element not found');
        if (!fileInput) console.warn('UploadManager: file-input element not found');
        if (!browseBtn) console.warn('UploadManager: browse-btn element not found');

        // Click to browse
        if (uploadArea && fileInput) uploadArea.addEventListener('click', () => fileInput.click());
        if (browseBtn && fileInput) browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });

        // Drag and drop
        if (uploadArea) {
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFileUpload(files[0]);
                }
            });
        }

        // File input change
        if (fileInput) fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileUpload(e.target.files[0]);
            }
        });
    }

    async handleFileUpload(file) {
        if (!file.type.includes('pdf')) {
            UIComponents.showNotification('Please select a PDF file', 'error');
            return;
        }

        this.showUploadProgress();

        try {
            const result = await API.papers.upload(file);
            this.hideUploadProgress();
            UIComponents.hideModal('upload-modal');

            // result now contains { paper, task_id }
            const paper = result && result.paper ? result.paper : null;
            const taskId = result && result.task_id ? result.task_id : null;

            UIComponents.showNotification('Paper uploaded successfully!', 'success');

            // Smart collection classification will happen automatically after metadata extraction completes

            // Navigate to the paper details view immediately
            if (paper && window.paperManager) {
                window.paperManager.showPaperDetailsWithExtraction(paper.id, taskId);
                // Also refresh the papers list
                window.paperManager.loadPapers();
            }

            // Refresh dashboard stats
            if (window.dashboardManager) window.dashboardManager.loadStats();

        } catch (error) {
            this.hideUploadProgress();
            UIComponents.showNotification(`Upload failed: ${error.message}`, 'error');
        }
    }

    showUploadProgress() {
        const uploadArea = document.getElementById('upload-area');
        const uploadProgress = document.getElementById('upload-progress');
        
        uploadArea.style.display = 'none';
        uploadProgress.style.display = 'block';

        // Simulate progress (since we don't have real progress tracking)
        const progressFill = uploadProgress.querySelector('.progress-fill');
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressFill.style.width = `${progress}%`;
        }, 200);

        this.progressInterval = interval;
    }

    hideUploadProgress() {
        const uploadArea = document.getElementById('upload-area');
        const uploadProgress = document.getElementById('upload-progress');
        
        uploadArea.style.display = 'block';
        uploadProgress.style.display = 'none';

        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        // Reset progress
        const progressFill = uploadProgress.querySelector('.progress-fill');
        progressFill.style.width = '0%';

        // Clear file input
        document.getElementById('file-input').value = '';
    }
}