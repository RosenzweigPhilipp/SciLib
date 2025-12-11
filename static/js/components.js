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
        card.innerHTML = `
            <div class="paper-title" onclick="PaperManager.showPaperDetails(${paper.id})">
                ${Utils.sanitizeHtml(paper.title)}
            </div>
            <div class="paper-authors">${Utils.sanitizeHtml(paper.authors)}</div>
            ${paper.abstract ? `<div class="paper-abstract-preview">${Utils.truncateText(paper.abstract)}</div>` : ''}
            <div class="paper-meta">
                <div>
                    ${paper.year ? `<span class="year">${paper.year}</span>` : ''}
                    ${paper.journal ? `<span class="journal">${Utils.sanitizeHtml(paper.journal)}</span>` : ''}
                </div>
                <div class="paper-actions">
                    <button class="action-btn" onclick="PaperManager.showPaperDetails(${paper.id})" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn" onclick="PaperManager.editPaper(${paper.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn" onclick="PaperManager.deletePaper(${paper.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
        return card;
    }

    // Create collection card
    static createCollectionCard(collection) {
        const card = document.createElement('div');
        card.className = 'collection-card';
        card.innerHTML = `
            <div class="collection-title">${Utils.sanitizeHtml(collection.name)}</div>
            ${collection.description ? `<div class="collection-description">${Utils.sanitizeHtml(collection.description)}</div>` : ''}
            <div class="collection-meta">
                <span>Created ${Utils.formatDate(collection.created_at)}</span>
                <div class="collection-actions">
                    <button class="action-btn" onclick="CollectionManager.editCollection(${collection.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn" onclick="CollectionManager.deleteCollection(${collection.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
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
                <button class="action-btn" onclick="TagManager.editTag(${tag.id})" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn" onclick="TagManager.deleteTag(${tag.id})" title="Delete">
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
        this.setupUploadHandlers();
    }

    setupUploadHandlers() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const browseBtn = document.getElementById('browse-btn');

        // Click to browse
        uploadArea.addEventListener('click', () => fileInput.click());
        browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });

        // Drag and drop
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

        // File input change
        fileInput.addEventListener('change', (e) => {
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
            UIComponents.showNotification('Paper uploaded successfully!', 'success');
            
            // Refresh the papers list
            if (window.paperManager) {
                window.paperManager.loadPapers();
            }
            
            // Update dashboard stats
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
            }
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