document.addEventListener('DOMContentLoaded', function () {
    const templatesTableContainer = document.getElementById('templatesTableContainer');
    const loadingMessage = document.getElementById('loadingMessage');
    const errorMessageDiv = document.getElementById('errorMessage');

    function displayError(message) {
        if (loadingMessage) loadingMessage.style.display = 'none';
        const errorText = document.getElementById('errorText');
        if (errorText) {
            errorText.textContent = message;
        }
        errorMessageDiv.style.display = 'block';
        // Clear previous table if any
        const existingTable = templatesTableContainer.querySelector('table');
        if (existingTable) existingTable.remove();

        // Also show as notification for better UX
        showNotification(message, 'error');
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
            border-radius: 12px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            max-width: 400px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            animation: slideInRight 0.3s ease-out;
        `;

        // Set background color based on type
        const colors = {
            success: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            error: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
            warning: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            info: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
        };
        notification.style.background = colors[type] || colors.info;

        notification.textContent = message;
        document.body.appendChild(notification);

        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }

    function fetchAndDisplayTemplates() {
        if (loadingMessage) loadingMessage.style.display = 'block';
        errorMessageDiv.style.display = 'none'; // Hide previous errors

        fetch('/list_templates')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (loadingMessage) loadingMessage.style.display = 'none';

                // Clear only table, not error message div
                const existingTable = templatesTableContainer.querySelector('table');
                if (existingTable) existingTable.remove();

                if (!data.templates || !Array.isArray(data.templates) || data.templates.length === 0) {
                    templatesTableContainer.innerHTML = `
                        <div class="text-center" style="padding: 40px; color: #6c757d;">
                            <div style="font-size: 3rem; margin-bottom: 16px;">📋</div>
                            <h3>No Templates Found</h3>
                            <p>Create your first template to get started with automated processing.</p>
                        </div>
                    `;
                    return;
                }

                // Add template statistics
                const statsDiv = document.createElement('div');
                statsDiv.className = 'mb-3';
                statsDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <span style="color: #6c757d;">
                            📊 ${data.templates.length} template${data.templates.length !== 1 ? 's' : ''} available
                        </span>
                    </div>
                `;
                templatesTableContainer.appendChild(statsDiv);

                const table = document.createElement('table');
                table.className = 'table';
                table.innerHTML = `
                    <thead>
                        <tr>
                            <th>📋 Template Name</th>
                            <th>📁 Filename</th>
                            <th>📅 Created On</th>
                            <th>⚙️ Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                    </tbody>
                `;
                const tbody = table.querySelector('tbody');

                data.templates.forEach(template => {
                    const tr = document.createElement('tr');

                    const nameTd = document.createElement('td');
                    nameTd.textContent = template.display_name;
                    tr.appendChild(nameTd);

                    const fileIdTd = document.createElement('td');
                    fileIdTd.textContent = template.file_id;
                    tr.appendChild(fileIdTd);

                    const timestampTd = document.createElement('td');
                    // Attempt to format timestamp for better readability if it's a valid ISO string
                    let formattedTimestamp = template.creation_timestamp || 'N/A';
                    if (formattedTimestamp !== 'N/A') {
                        try {
                            const date = new Date(formattedTimestamp);
                            // Check if date is valid after parsing
                            if (!isNaN(date.getTime())) {
                                formattedTimestamp = date.toLocaleString(); // User's local time and format
                            } else {
                                formattedTimestamp = template.creation_timestamp; // Show original if invalid
                            }
                        } catch (e) {
                            // If error in parsing, show original
                            formattedTimestamp = template.creation_timestamp;
                        }
                    }
                    timestampTd.textContent = formattedTimestamp;
                    tr.appendChild(timestampTd);

                    const actionsTd = document.createElement('td');
                    const deleteButton = document.createElement('button');
                    deleteButton.classList.add('delete-template-btn', 'btn', 'btn-danger', 'btn-sm');
                    deleteButton.dataset.filename = template.file_id;
                    deleteButton.innerHTML = '🗑️ Delete';
                    actionsTd.appendChild(deleteButton);
                    tr.appendChild(actionsTd);

                    tbody.appendChild(tr);
                });

                // Make sure loading message is gone before adding table
                const currentLoadingMsg = document.getElementById('loadingMessage');
                if (currentLoadingMsg) currentLoadingMsg.remove();

                templatesTableContainer.appendChild(table);
            })
            .catch(error => {
                console.error('Error fetching templates:', error);
                displayError('Failed to load templates. ' + error.message);
            });
    }

    // Event listener for delete buttons (using event delegation)
    templatesTableContainer.addEventListener('click', function (event) {
        if (event.target.classList.contains('delete-template-btn')) {
            const templateFilename = event.target.dataset.filename;
            if (!templateFilename) {
                alert('Error: Template filename not found.');
                return;
            }

            if (window.confirm(`Are you sure you want to delete template '${templateFilename}'?`)) {
                fetch(`/delete_template/${encodeURIComponent(templateFilename)}`, {
                    method: 'DELETE',
                })
                    .then(response => {
                        // Regardless of ok status, try to parse JSON, as error messages might be in JSON body
                        return response.json().then(data => ({ ok: response.ok, status: response.status, data }));
                    })
                    .then(result => {
                        if (result.ok) {
                            showNotification(result.data.message || 'Template deleted successfully.', 'success');
                            fetchAndDisplayTemplates(); // Refresh the list
                        } else {
                            // Server responded with an error status code (4xx, 5xx)
                            const errorMsg = result.data.error || `Failed to delete template. Status: ${result.status}`;
                            showNotification(`Error: ${errorMsg}`, 'error');
                        }
                    })
                    .catch(error => {
                        // Network error or issue with parsing the JSON response itself
                        console.error('Error deleting template:', error);
                        showNotification('An unexpected error occurred while trying to delete the template. ' + error.message, 'error');
                    });
            }
        }
    });

    // Create New Template functionality
    const createNewTemplateBtn = document.getElementById('createNewTemplateBtn');
    const createTemplateModal = document.getElementById('createTemplateModal');
    const createTemplateForm = document.getElementById('createTemplateForm');
    const cancelCreateTemplate = document.getElementById('cancelCreateTemplate');
    const addMappingBtn = document.getElementById('addMappingBtn');
    const fieldMappingsContainer = document.getElementById('fieldMappingsContainer');

    // Load field definitions for the dropdown
    let fieldDefinitions = {};

    // Try to get field definitions from the global variable or fetch them
    if (typeof window.FIELD_DEFINITIONS !== 'undefined') {
        fieldDefinitions = window.FIELD_DEFINITIONS;
        populateFieldOptions();
    } else {
        // Fetch field definitions if not available globally
        fetch('/field_definitions')
            .then(response => response.json())
            .then(data => {
                fieldDefinitions = data;
                populateFieldOptions();
            })
            .catch(error => {
                console.error('Error loading field definitions:', error);
                fieldDefinitions = {
                    'InvoiceID': 'Invoice ID',
                    'InvoiceDate': 'Invoice Date',
                    'DueDate': 'Due Date',
                    'PONumber': 'PO Number',
                    'VendorName': 'Vendor Name',
                    'TotalAmount': 'Total Amount',
                    'TaxAmount': 'Tax Amount',
                    'ItemDescription': 'Item Description',
                    'ItemQuantity': 'Item Quantity',
                    'ItemUnitPrice': 'Item Unit Price'
                };
                populateFieldOptions();
            });
    }

    function populateFieldOptions() {
        const mappedFieldSelects = document.querySelectorAll('.mapped-field');
        mappedFieldSelects.forEach(select => {
            // Clear existing options except the first one
            select.innerHTML = '<option value="">Select Field...</option>';

            // Add field definition options
            Object.keys(fieldDefinitions).forEach(fieldKey => {
                const option = document.createElement('option');
                option.value = fieldKey;
                option.textContent = fieldDefinitions[fieldKey].display_name || fieldKey;
                select.appendChild(option);
            });
        });
    }

    createNewTemplateBtn.addEventListener('click', function () {
        createTemplateModal.classList.add('show');
        populateFieldOptions(); // Ensure options are populated
    });

    function closeModal() {
        createTemplateModal.classList.remove('show');
        createTemplateForm.reset();
        // Reset to single mapping row
        const mappingRows = fieldMappingsContainer.querySelectorAll('.field-mapping-row');
        for (let i = 1; i < mappingRows.length; i++) {
            mappingRows[i].remove();
        }
    }

    cancelCreateTemplate.addEventListener('click', closeModal);

    // Add event listener for the footer cancel button
    const cancelCreateTemplateFooter = document.getElementById('cancelCreateTemplateFooter');
    if (cancelCreateTemplateFooter) {
        cancelCreateTemplateFooter.addEventListener('click', closeModal);
    }

    // Close modal when clicking outside
    createTemplateModal.addEventListener('click', function (event) {
        if (event.target === createTemplateModal) {
            closeModal();
        }
    });

    addMappingBtn.addEventListener('click', function () {
        const newRow = document.createElement('div');
        newRow.className = 'field-mapping-row';
        newRow.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px;';
        newRow.innerHTML = `
            <input type="text" placeholder="Original Header" class="original-header" style="flex: 1; padding: 8px;">
            <select class="mapped-field" style="flex: 1; padding: 8px;">
                <option value="">Select Field...</option>
            </select>
            <button type="button" class="remove-mapping-btn" style="padding: 8px;">Remove</button>
        `;
        fieldMappingsContainer.appendChild(newRow);

        // Populate the new select with field options
        const newSelect = newRow.querySelector('.mapped-field');
        Object.keys(fieldDefinitions).forEach(fieldKey => {
            const option = document.createElement('option');
            option.value = fieldKey;
            option.textContent = fieldDefinitions[fieldKey].display_name || fieldKey;
            newSelect.appendChild(option);
        });
    });

    // Handle remove mapping button clicks
    fieldMappingsContainer.addEventListener('click', function (event) {
        if (event.target.classList.contains('remove-mapping-btn')) {
            const row = event.target.closest('.field-mapping-row');
            if (fieldMappingsContainer.querySelectorAll('.field-mapping-row').length > 1) {
                row.remove();
            } else {
                displayError('At least one mapping row is required.');
            }
        }
    });

    createTemplateForm.addEventListener('submit', function (event) {
        event.preventDefault();

        const templateName = document.getElementById('templateName').value.trim();
        const skipRows = parseInt(document.getElementById('skipRows').value) || 0;

        if (!templateName) {
            displayError('Template name is required.');
            return;
        }

        // Collect field mappings
        const mappingRows = fieldMappingsContainer.querySelectorAll('.field-mapping-row');
        const fieldMappings = [];

        mappingRows.forEach(row => {
            const originalHeader = row.querySelector('.original-header').value.trim();
            const mappedField = row.querySelector('.mapped-field').value;

            if (originalHeader && mappedField) {
                fieldMappings.push({
                    original_header: originalHeader,
                    mapped_field: mappedField
                });
            }
        });

        if (fieldMappings.length === 0) {
            displayError('At least one field mapping is required.');
            return;
        }

        // Create template object
        const templateData = {
            template_name: templateName,
            filename: templateName.replace(/[^a-zA-Z0-9]/g, '_') + '.json',
            creation_timestamp: new Date().toISOString(),
            field_mappings: fieldMappings,
            skip_rows: skipRows
        };

        // Show loading state
        const submitButton = document.querySelector('#createTemplateForm button[type="submit"]');
        const originalText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = '⏳ Creating...';

        // Save template
        fetch('/save_template', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(templateData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' || data.message) {
                    showNotification(data.message || 'Template created successfully!', 'success');
                    closeModal();
                    fetchAndDisplayTemplates(); // Refresh the template list
                } else {
                    displayError(data.error || 'Failed to create template.');
                }
            })
            .catch(error => {
                console.error('Error creating template:', error);
                displayError('Error creating template: ' + error.message);
            })
            .finally(() => {
                // Restore button state
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            });
    });

    // Initial call to fetch and display templates
    fetchAndDisplayTemplates();
});
