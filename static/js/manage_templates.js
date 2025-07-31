document.addEventListener('DOMContentLoaded', function() {
    const templatesTableContainer = document.getElementById('templatesTableContainer');
    const loadingMessage = document.getElementById('loadingMessage');
    const errorMessageDiv = document.getElementById('errorMessage');

    function displayError(message) {
        if (loadingMessage) loadingMessage.style.display = 'none';
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
        // Clear previous table if any
        const existingTable = templatesTableContainer.querySelector('table');
        if (existingTable) existingTable.remove();
    }

    function displaySuccessMessage(message) {
        // For now, using alert. Could be a temporary div.
        alert(message);
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
                    templatesTableContainer.innerHTML = '<p>No templates found.</p>'; // Replace everything
                    return;
                }

                const table = document.createElement('table');
                table.innerHTML = `
                    <thead>
                        <tr>
                            <th>Template Name</th>
                            <th>Filename</th>
                            <th>Created On</th>
                            <th>Actions</th>
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
                    deleteButton.classList.add('delete-template-btn'); // Class for styling and event delegation
                    deleteButton.dataset.filename = template.file_id;
                    deleteButton.textContent = 'Delete';
                    actionsTd.appendChild(deleteButton);
                    tr.appendChild(actionsTd);

                    tbody.appendChild(tr);
                });

                // Make sure loading message is gone before adding table
                const currentLoadingMsg = document.getElementById('loadingMessage');
                if(currentLoadingMsg) currentLoadingMsg.remove();

                templatesTableContainer.appendChild(table);
            })
            .catch(error => {
                console.error('Error fetching templates:', error);
                displayError('Failed to load templates. ' + error.message);
            });
    }

    // Event listener for delete buttons (using event delegation)
    templatesTableContainer.addEventListener('click', function(event) {
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
                        displaySuccessMessage(result.data.message || 'Template deleted successfully.');
                        fetchAndDisplayTemplates(); // Refresh the list
                    } else {
                        // Server responded with an error status code (4xx, 5xx)
                        const errorMsg = result.data.error || `Failed to delete template. Status: ${result.status}`;
                        alert(`Error: ${errorMsg}`); // Using alert for error feedback from delete
                        // Optionally, call fetchAndDisplayTemplates() even on error if the list might have changed
                        // or if some deletions might succeed while others fail (though less likely with single delete)
                    }
                })
                .catch(error => {
                    // Network error or issue with parsing the JSON response itself
                    console.error('Error deleting template:', error);
                    alert('An unexpected error occurred while trying to delete the template. ' + error.message);
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
    if (typeof FIELD_DEFINITIONS !== 'undefined') {
        fieldDefinitions = FIELD_DEFINITIONS;
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

    createNewTemplateBtn.addEventListener('click', function() {
        createTemplateModal.style.display = 'block';
        populateFieldOptions(); // Ensure options are populated
    });

    cancelCreateTemplate.addEventListener('click', function() {
        createTemplateModal.style.display = 'none';
        createTemplateForm.reset();
        // Reset to single mapping row
        const mappingRows = fieldMappingsContainer.querySelectorAll('.field-mapping-row');
        for (let i = 1; i < mappingRows.length; i++) {
            mappingRows[i].remove();
        }
    });

    // Close modal when clicking outside
    createTemplateModal.addEventListener('click', function(event) {
        if (event.target === createTemplateModal) {
            createTemplateModal.style.display = 'none';
        }
    });

    addMappingBtn.addEventListener('click', function() {
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
    fieldMappingsContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('remove-mapping-btn')) {
            const row = event.target.closest('.field-mapping-row');
            if (fieldMappingsContainer.querySelectorAll('.field-mapping-row').length > 1) {
                row.remove();
            } else {
                displayError('At least one mapping row is required.');
            }
        }
    });

    createTemplateForm.addEventListener('submit', function(event) {
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
                displaySuccessMessage(data.message || 'Template created successfully!');
                createTemplateModal.style.display = 'none';
                createTemplateForm.reset();
                fetchAndDisplayTemplates(); // Refresh the template list
            } else {
                displayError(data.error || 'Failed to create template.');
            }
        })
        .catch(error => {
            console.error('Error creating template:', error);
            displayError('Error creating template: ' + error.message);
        });
    });

    // Initial call to fetch and display templates
    fetchAndDisplayTemplates();
});
