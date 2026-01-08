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
        
        // Generate publication type badge
        const pubTypeBadge = UIComponents.getPublicationTypeBadge(paper.publication_type);
        
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
            <div class="paper-authors">${Utils.sanitizeHtml(Utils.formatAuthors(paper.authors, 3))}</div>
            ${collectionBadges}
            ${paper.abstract ? `<div class="paper-abstract-preview">${Utils.truncateText(paper.abstract)}</div>` : ''}
            <div class="paper-meta">
                <div>
                    ${pubTypeBadge}
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
    
    // Get publication type badge
    static getPublicationTypeBadge(publicationType) {
        if (!publicationType) return '';
        
        const typeLabels = {
            'article': 'Article',
            'inproceedings': 'Conference',
            'book': 'Book',
            'inbook': 'Book Chapter',
            'incollection': 'Collection',
            'phdthesis': 'PhD Thesis',
            'mastersthesis': 'Master\'s Thesis',
            'techreport': 'Tech Report',
            'misc': 'Other'
        };
        
        const typeIcons = {
            'article': 'fa-file-alt',
            'inproceedings': 'fa-users',
            'book': 'fa-book',
            'inbook': 'fa-bookmark',
            'incollection': 'fa-layer-group',
            'phdthesis': 'fa-graduation-cap',
            'mastersthesis': 'fa-user-graduate',
            'techreport': 'fa-file-code',
            'misc': 'fa-file'
        };
        
        const label = typeLabels[publicationType] || publicationType;
        const icon = typeIcons[publicationType] || 'fa-file';
        
        return `<span class="paper-type-badge ${publicationType}" title="${label}">
            <i class="fas ${icon}"></i> ${label}
        </span>`;
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
        this.batchTasks = new Map(); // Track task_id -> { paperId, filename, status }
        this.pollingInterval = null;
        try {
            this.setupUploadHandlers();
            this.setupBatchModalHandlers();
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
                const files = Array.from(e.dataTransfer.files).filter(f => f.type.includes('pdf'));
                if (files.length > 1) {
                    this.handleBatchUpload(files);
                } else if (files.length === 1) {
                    this.handleFileUpload(files[0]);
                }
            });
        }

        // File input change - handle multiple files
        if (fileInput) fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 1) {
                this.handleBatchUpload(files);
            } else if (files.length === 1) {
                this.handleFileUpload(files[0]);
            }
        });
    }

    setupBatchModalHandlers() {
        const closeBtn = document.getElementById('batch-upload-close');
        const doneBtn = document.getElementById('batch-upload-done');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeBatchModal());
        }
        if (doneBtn) {
            doneBtn.addEventListener('click', () => this.closeBatchModal());
        }
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

    async handleBatchUpload(files) {
        // Hide upload modal and show batch progress modal
        UIComponents.hideModal('upload-modal');
        this.showBatchModal(files);
        
        try {
            // Upload all files at once
            const result = await API.papers.uploadBatch(files);
            
            // Update the UI with results
            this.updateBatchResults(result);
            
            // Start polling for extraction status
            this.startBatchPolling(result.results);
            
            // Refresh papers list
            if (window.paperManager) {
                window.paperManager.loadPapers();
            }
            
            // Refresh dashboard stats
            if (window.dashboardManager) {
                window.dashboardManager.loadStats();
            }
            
        } catch (error) {
            UIComponents.showNotification(`Batch upload failed: ${error.message}`, 'error');
            this.updateBatchError(error.message);
        }
    }

    showBatchModal(files) {
        // Reset state
        this.batchTasks.clear();
        
        // Update summary counts
        document.getElementById('batch-total').textContent = files.length;
        document.getElementById('batch-uploaded').textContent = '0';
        document.getElementById('batch-extracting').textContent = '0';
        document.getElementById('batch-completed').textContent = '0';
        document.getElementById('batch-failed').textContent = '0';
        
        // Reset progress bar
        document.getElementById('batch-progress-fill').style.width = '0%';
        
        // Create file list items
        const filesList = document.getElementById('batch-files-list');
        filesList.innerHTML = files.map((file, index) => `
            <div class="batch-file-item" id="batch-file-${index}">
                <div class="batch-file-icon">
                    <i class="fas fa-file-pdf"></i>
                </div>
                <div class="batch-file-info">
                    <div class="batch-file-name">${Utils.sanitizeHtml(file.name)}</div>
                    <div class="batch-file-status">
                        <span class="status-text">Uploading...</span>
                        <i class="fas fa-spinner fa-spin status-icon"></i>
                    </div>
                </div>
            </div>
        `).join('');
        
        // Hide done button initially
        document.getElementById('batch-upload-done').style.display = 'none';
        
        // Show modal
        UIComponents.showModal('batch-upload-modal');
    }

    updateBatchResults(result) {
        // Update uploaded count
        document.getElementById('batch-uploaded').textContent = result.successful;
        document.getElementById('batch-failed').textContent = result.failed;
        
        // Update progress bar for upload phase (50%)
        const uploadProgress = (result.successful / result.total) * 50;
        document.getElementById('batch-progress-fill').style.width = `${uploadProgress}%`;
        
        // Track upload failures separately (for polling logic)
        const failedEl = document.getElementById('batch-failed');
        failedEl.textContent = result.failed;
        failedEl.dataset.uploadFailed = result.failed;
        
        // Update each file item
        result.results.forEach((fileResult, index) => {
            const fileItem = document.getElementById(`batch-file-${index}`);
            if (!fileItem) return;
            
            const statusText = fileItem.querySelector('.status-text');
            const statusIcon = fileItem.querySelector('.status-icon');
            
            if (fileResult.success) {
                if (fileResult.task_id) {
                    // Track for polling
                    this.batchTasks.set(fileResult.task_id, {
                        paperId: fileResult.paper.id,
                        filename: fileResult.filename,
                        index: index,
                        status: 'extracting'
                    });
                    
                    statusText.textContent = 'Extracting metadata...';
                    statusIcon.className = 'fas fa-cog fa-spin status-icon extracting';
                    fileItem.classList.add('extracting');
                } else {
                    statusText.textContent = 'Uploaded (no extraction)';
                    statusIcon.className = 'fas fa-check status-icon success';
                    fileItem.classList.add('completed');
                }
            } else {
                statusText.textContent = fileResult.error || 'Upload failed';
                statusIcon.className = 'fas fa-times status-icon error';
                fileItem.classList.add('failed');
            }
        });
        
        // Update extracting count
        document.getElementById('batch-extracting').textContent = this.batchTasks.size;
    }

    updateBatchError(errorMessage) {
        // Mark all as failed
        const fileItems = document.querySelectorAll('.batch-file-item');
        fileItems.forEach(item => {
            const statusText = item.querySelector('.status-text');
            const statusIcon = item.querySelector('.status-icon');
            statusText.textContent = errorMessage;
            statusIcon.className = 'fas fa-times status-icon error';
            item.classList.add('failed');
        });
        
        document.getElementById('batch-failed').textContent = fileItems.length;
        document.getElementById('batch-upload-done').style.display = 'block';
    }

    startBatchPolling(results) {
        // If no tasks to track, show done button
        if (this.batchTasks.size === 0) {
            document.getElementById('batch-upload-done').style.display = 'block';
            document.getElementById('batch-progress-fill').style.width = '100%';
            return;
        }
        
        // Poll every 2 seconds
        this.pollingInterval = setInterval(() => this.pollBatchStatus(), 2000);
    }

    async pollBatchStatus() {
        let allComplete = true;
        let completedCount = 0;
        let failedCount = 0;
        let extractingCount = 0;
        
        // Count already-failed uploads (non-task failures)
        const uploadFailedCount = parseInt(document.getElementById('batch-failed').dataset.uploadFailed || '0');
        
        for (const [taskId, taskInfo] of this.batchTasks) {
            // Count already completed/failed tasks
            if (taskInfo.status === 'completed') {
                completedCount++;
                continue;
            }
            if (taskInfo.status === 'failed') {
                failedCount++;
                continue;
            }
            
            // Task still in progress, poll for status
            try {
                const response = await API.ai.getTaskStatus(taskId);
                
                const fileItem = document.getElementById(`batch-file-${taskInfo.index}`);
                if (!fileItem) continue;
                
                const statusText = fileItem.querySelector('.status-text');
                const statusIcon = fileItem.querySelector('.status-icon');
                
                // API returns 'status' field with values: completed, failed, pending, processing
                if (response.status === 'completed') {
                    taskInfo.status = 'completed';
                    completedCount++;
                    
                    const confidence = response.result?.extraction_data?.confidence || 0;
                    statusText.textContent = `Completed (${Math.round(confidence * 100)}% confidence)`;
                    statusIcon.className = 'fas fa-check status-icon success';
                    fileItem.classList.remove('extracting');
                    fileItem.classList.add('completed');
                    
                } else if (response.status === 'failed' || response.status === 'error') {
                    taskInfo.status = 'failed';
                    failedCount++;
                    
                    statusText.textContent = response.error || 'Extraction failed';
                    statusIcon.className = 'fas fa-times status-icon error';
                    fileItem.classList.remove('extracting');
                    fileItem.classList.add('failed');
                    
                } else {
                    // Still processing (pending, processing, or other states)
                    allComplete = false;
                    extractingCount++;
                    if (response.progress) {
                        statusText.textContent = `Extracting: ${response.progress}%`;
                    }
                }
            } catch (error) {
                console.error(`Error polling task ${taskId}:`, error);
                allComplete = false;
                extractingCount++;
            }
        }
        
        // Update counts in UI
        document.getElementById('batch-extracting').textContent = extractingCount;
        document.getElementById('batch-completed').textContent = completedCount;
        document.getElementById('batch-failed').textContent = failedCount + uploadFailedCount;
        
        // Update progress bar (50% for upload + 50% for extraction)
        const totalTasks = this.batchTasks.size;
        const uploadedCount = parseInt(document.getElementById('batch-uploaded').textContent) || 0;
        const totalFiles = parseInt(document.getElementById('batch-total').textContent) || 1;
        const uploadProgress = (uploadedCount / totalFiles) * 50;
        const extractionProgress = totalTasks > 0 ? ((completedCount + failedCount) / totalTasks) * 50 : 50;
        document.getElementById('batch-progress-fill').style.width = `${uploadProgress + extractionProgress}%`;
        
        // Check if all complete
        if (allComplete || extractingCount === 0) {
            this.stopBatchPolling();
            document.getElementById('batch-upload-done').style.display = 'block';
            document.getElementById('batch-progress-fill').style.width = '100%';
            
            // Refresh papers list to show updated metadata
            if (window.paperManager) {
                window.paperManager.loadPapers();
            }
        }
    }

    stopBatchPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    closeBatchModal() {
        this.stopBatchPolling();
        UIComponents.hideModal('batch-upload-modal');
        
        // Clear file input
        const fileInput = document.getElementById('file-input');
        if (fileInput) fileInput.value = '';
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