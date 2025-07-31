// Modern Upload JavaScript for Vendor Statements App

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    const fileStatusesDiv = document.getElementById('fileStatuses');
    const progressCard = document.getElementById('progressCard');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const progressText = document.getElementById('progressText');

    // Make upload area clickable
    uploadArea.addEventListener('click', function(e) {
        // Only trigger file input if not clicking on the file input itself
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    // Drag and drop functionality
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        fileInput.files = files;
        updateFileDisplay();
    });

    // Update file display when files are selected
    fileInput.addEventListener('change', updateFileDisplay);

    function updateFileDisplay() {
        const files = fileInput.files;
        if (files.length > 0) {
            const fileList = Array.from(files).map(file => file.name).join(', ');
            uploadArea.querySelector('.upload-text').innerHTML = 
                `<strong>${files.length} file(s) selected:</strong><br><small>${fileList}</small>`;
        }
    }

    // Form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (fileInput.files.length === 0) {
            showNotification('Please select files to upload', 'error');
            return;
        }

        uploadFiles();
    });

    function uploadFiles() {
        const formData = new FormData();
        Array.from(fileInput.files).forEach(file => {
            formData.append('files[]', file);
        });

        // Show progress card
        progressCard.style.display = 'block';
        progressCard.scrollIntoView({ behavior: 'smooth' });

        const xhr = new XMLHttpRequest();
        const uploadStartTime = Date.now();

        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                overallProgressBar.style.width = percentComplete + '%';
                progressText.textContent = Math.round(percentComplete) + '% complete';

                // Calculate ETA
                const elapsedMs = Date.now() - uploadStartTime;
                if (elapsedMs > 0 && percentComplete > 0) {
                    const totalTimeEstimateMs = (elapsedMs / percentComplete) * 100;
                    const remainingTimeSeconds = (totalTimeEstimateMs - elapsedMs) / 1000;
                    etaDisplay.textContent = formatTime(remainingTimeSeconds);
                }
            }
        });

        xhr.addEventListener('load', function() {
            overallProgressBar.style.width = '100%';
            progressText.textContent = '100% complete';
            etaDisplay.textContent = '00:00';

            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const results = JSON.parse(xhr.responseText);
                    displayResults(results);
                } catch (e) {
                    showNotification('Error parsing server response', 'error');
                }
            } else {
                showNotification('Upload failed. Please try again.', 'error');
            }
        });

        xhr.addEventListener('error', function() {
            showNotification('Network error. Please check your connection.', 'error');
        });

        xhr.open('POST', '/upload');
        xhr.send(formData);
    }

    function displayResults(results) {
        fileStatusesDiv.innerHTML = '';

        results.forEach((result, index) => {
            const fileCard = createFileCard(result, index);
            fileStatusesDiv.appendChild(fileCard);
        });

        // Hide progress card after a delay
        setTimeout(() => {
            progressCard.style.display = 'none';
        }, 2000);
    }

    function createFileCard(result, index) {
        const card = document.createElement('div');
        card.className = 'card fade-in';
        card.style.animationDelay = `${index * 0.1}s`;

        const fileExtension = result.filename.split('.').pop().toLowerCase();
        const statusClass = result.success ? 'success' : 'error';
        const statusIcon = result.success ? '✅' : '❌';

        card.innerHTML = `
            <div class="file-header">
                <div class="file-info">
                    <div class="file-icon ${fileExtension}">${fileExtension.toUpperCase()}</div>
                    <div>
                        <div class="file-name">${result.filename}</div>
                        <small style="color: #6c757d;">${result.file_type} • ${result.headers ? result.headers.length : 0} headers</small>
                    </div>
                </div>
                <div class="file-status ${statusClass}">
                    ${statusIcon} ${result.success ? 'Ready' : 'Error'}
                </div>
            </div>
            <div class="file-body">
                <div class="mb-3">
                    <strong>Status:</strong> ${result.message}
                    ${result.applied_template_name ? `<br><strong>Template:</strong> ${result.applied_template_name} (Skip ${result.skip_rows} rows)` : ''}
                </div>
                
                ${result.success ? createFileControls(result) : ''}
                ${result.success && result.headers ? createMappingTable(result) : ''}
            </div>
        `;

        return card;
    }

    function createFileControls(result) {
        const fileId = result.filename.replace(/[^a-zA-Z0-9]/g, '_');
        
        return `
            <div class="d-flex gap-2 mb-3" style="flex-wrap: wrap;">
                ${(result.file_type === 'CSV' || result.file_type === 'XLSX' || result.file_type === 'XLS') ? `
                    <div class="d-flex align-items-center gap-2">
                        <label for="skipRows-${fileId}" style="margin: 0; font-size: 0.875rem;">Skip Rows:</label>
                        <input type="number" id="skipRows-${fileId}" value="${result.skip_rows || 0}" min="0" 
                               class="form-control" style="width: 80px;">
                        <button type="button" class="btn btn-secondary btn-sm apply-skip-rows" 
                                data-file-id="${result.filename}" data-file-type="${result.file_type}">
                            Apply
                        </button>
                    </div>
                ` : ''}
                
                <select class="form-control form-select template-select" style="width: 200px;" 
                        data-file-id="${result.filename}">
                    <option value="">Select Template...</option>
                </select>
                
                <button type="button" class="btn btn-primary process-file" 
                        data-file-id="${result.filename}" data-file-type="${result.file_type}">
                    🚀 Process File
                </button>
                
                <button type="button" class="btn btn-warning save-template" 
                        data-file-id="${result.filename}">
                    💾 Save as Template
                </button>
            </div>
        `;
    }

    function createMappingTable(result) {
        if (!result.headers || result.headers.length === 0) {
            return '<p class="text-center" style="color: #6c757d;">No headers found in this file.</p>';
        }

        let tableHTML = `
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Original Header</th>
                            <th>Mapped Field</th>
                            <th>Confidence</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        result.headers.forEach((header, index) => {
            const mapping = result.field_mappings && result.field_mappings[index] ? result.field_mappings[index] : {};
            const confidence = mapping.confidence || 0;
            const confidenceClass = confidence > 0.8 ? 'success' : confidence > 0.5 ? 'warning' : 'danger';
            
            tableHTML += `
                <tr>
                    <td><strong>${header}</strong></td>
                    <td>
                        <select class="form-control form-select mapping-select" 
                                data-header="${header}" style="min-width: 200px;">
                            <option value="">-- Select Field --</option>
                        </select>
                    </td>
                    <td>
                        <span class="file-status ${confidenceClass}" style="font-size: 0.75rem;">
                            ${Math.round(confidence * 100)}%
                        </span>
                    </td>
                    <td>
                        <button type="button" class="btn btn-light btn-sm chatbot-help" 
                                data-header="${header}">
                            🤖 Help
                        </button>
                    </td>
                </tr>
            `;
        });

        tableHTML += `
                    </tbody>
                </table>
            </div>
        `;

        return tableHTML;
    }

    // Event delegation for dynamic buttons
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('apply-skip-rows')) {
            handleApplySkipRows(e.target);
        } else if (e.target.classList.contains('process-file')) {
            handleProcessFile(e.target);
        } else if (e.target.classList.contains('save-template')) {
            handleSaveTemplate(e.target);
        } else if (e.target.classList.contains('chatbot-help')) {
            handleChatbotHelp(e.target);
        }
    });

    // Event delegation for template selection
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('template-select')) {
            handleTemplateSelection(e.target);
        }
    });

    function handleApplySkipRows(button) {
        const fileId = button.dataset.fileId;
        const fileType = button.dataset.fileType;
        const skipRowsInput = document.getElementById(`skipRows-${fileId.replace(/[^a-zA-Z0-9]/g, '_')}`);
        const skipRows = parseInt(skipRowsInput.value) || 0;

        showNotification('Reprocessing file with new skip rows...', 'info');

        fetch('/reprocess_file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_identifier: fileId,
                file_type: fileType,
                skip_rows: skipRows
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('File reprocessed successfully!', 'success');
                // Update the UI with new headers and mappings
                updateFileCard(fileId, data);
            } else {
                showNotification(data.message || 'Failed to reprocess file', 'error');
            }
        })
        .catch(error => {
            showNotification('Error reprocessing file', 'error');
            console.error('Error:', error);
        });
    }

    function handleTemplateSelection(select) {
        const templateFilename = select.value;
        const fileId = select.dataset.fileId;

        if (!templateFilename) return;

        showNotification('Applying template...', 'info');

        fetch('/apply_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                template_filename: templateFilename,
                file_identifier: fileId,
                file_type: select.closest('.card').querySelector('.file-icon').textContent
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`Template "${data.template_name}" applied successfully!`, 'success');
                updateFileCard(fileId, data);
            } else {
                showNotification(data.error || 'Failed to apply template', 'error');
            }
        })
        .catch(error => {
            showNotification('Error applying template', 'error');
            console.error('Error:', error);
        });
    }

    function handleProcessFile(button) {
        const fileId = button.dataset.fileId;
        const fileType = button.dataset.fileType;
        
        // Collect mappings
        const mappings = [];
        const card = button.closest('.card');
        const mappingSelects = card.querySelectorAll('.mapping-select');
        
        mappingSelects.forEach(select => {
            if (select.value) {
                mappings.push({
                    original_header: select.dataset.header,
                    mapped_field: select.value
                });
            }
        });

        if (mappings.length === 0) {
            showNotification('Please map at least one field before processing', 'warning');
            return;
        }

        button.disabled = true;
        button.textContent = '⏳ Processing...';

        fetch('/process_file_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_identifier: fileId,
                file_type: fileType,
                finalized_mappings: mappings,
                skip_rows: document.getElementById(`skipRows-${fileId.replace(/[^a-zA-Z0-9]/g, '_')}`).value || 0
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`File processed successfully! ${data.extracted_data.length} records extracted.`, 'success');
                // Add download button or show results
                addDownloadButton(card, data.extracted_data, fileId);
            } else {
                showNotification(data.message || 'Failed to process file', 'error');
            }
        })
        .catch(error => {
            showNotification('Error processing file', 'error');
            console.error('Error:', error);
        })
        .finally(() => {
            button.disabled = false;
            button.textContent = '🚀 Process File';
        });
    }

    function addDownloadButton(card, data, fileId) {
        const controlsDiv = card.querySelector('.d-flex');
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'btn btn-success';
        downloadBtn.innerHTML = '📥 Download Results';
        downloadBtn.addEventListener('click', () => downloadData(data, fileId));
        controlsDiv.appendChild(downloadBtn);
    }

    function downloadData(data, filename) {
        const csv = convertToCSV(data);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `processed_${filename}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    function convertToCSV(data) {
        if (!data || data.length === 0) return '';
        
        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header => `"${row[header] || ''}"`).join(','))
        ].join('\n');
        
        return csvContent;
    }

    // Load templates for dropdowns
    function loadTemplates() {
        fetch('/list_templates')
            .then(response => response.json())
            .then(data => {
                const templates = data.templates || [];
                const selects = document.querySelectorAll('.template-select');
                
                selects.forEach(select => {
                    // Clear existing options except the first one
                    while (select.children.length > 1) {
                        select.removeChild(select.lastChild);
                    }
                    
                    templates.forEach(template => {
                        const option = document.createElement('option');
                        option.value = template.file_id;
                        option.textContent = template.display_name || template.file_id;
                        select.appendChild(option);
                    });
                });
            })
            .catch(error => console.error('Error loading templates:', error));
    }

    // Load field definitions for mapping selects
    function loadFieldDefinitions() {
        fetch('/field_definitions')
            .then(response => response.json())
            .then(fieldDefs => {
                window.FIELD_DEFINITIONS = fieldDefs;
                updateMappingSelects();
            })
            .catch(error => console.error('Error loading field definitions:', error));
    }

    function updateMappingSelects() {
        const selects = document.querySelectorAll('.mapping-select');
        selects.forEach(select => {
            // Clear existing options except the first one
            while (select.children.length > 1) {
                select.removeChild(select.lastChild);
            }
            
            Object.keys(window.FIELD_DEFINITIONS || {}).forEach(fieldKey => {
                const fieldDef = window.FIELD_DEFINITIONS[fieldKey];
                const option = document.createElement('option');
                option.value = fieldKey;
                option.textContent = fieldDef.display_name || fieldKey;
                select.appendChild(option);
            });
        });
    }

    // Utility functions
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return 'N/A';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease-out;
        `;

        // Set background color based on type
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        notification.style.backgroundColor = colors[type] || colors.info;

        notification.textContent = message;
        document.body.appendChild(notification);

        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }

    // Initialize
    loadTemplates();
    loadFieldDefinitions();

    // Refresh templates and field definitions periodically
    setInterval(loadTemplates, 30000); // Every 30 seconds
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .hidden-file-input {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0,0,0,0);
        border: 0;
    }
`;
document.head.appendChild(style);