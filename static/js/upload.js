document.addEventListener('DOMContentLoaded', function () {
    console.log("[upload.js] DOMContentLoaded fired."); // New Log

    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const fileStatusesDiv = document.getElementById('fileStatuses');

    let uploadStartTime;
    window.extractedDataCache = window.extractedDataCache || {};

    // Make upload area clickable
    if (uploadArea) {
        uploadArea.addEventListener('click', function (e) {
            // Only trigger file input if not clicking on the file input itself
            if (e.target !== fileInput) {
                fileInput.click();
            }
        });

        // Drag and drop functionality
        uploadArea.addEventListener('dragover', function (e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', function (e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', function (e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');

            const files = e.dataTransfer.files;
            fileInput.files = files;
            updateFileDisplay();
        });
    }

    // Update file display when files are selected
    if (fileInput) {
        fileInput.addEventListener('change', updateFileDisplay);
    }

    function updateFileDisplay() {
        const files = fileInput.files;
        if (files.length > 0 && uploadArea) {
            const fileList = Array.from(files).map(file => file.name).join(', ');
            const uploadText = uploadArea.querySelector('.upload-text');
            if (uploadText) {
                uploadText.innerHTML = `<strong>${files.length} file(s) selected:</strong><br><small>${fileList}</small>`;
            }
        }
    }

    function showFilePreview(fileIdentifier) {
        console.log(`[showFilePreview] Showing preview for: ${fileIdentifier}`);

        // Show loading message
        displayMessage(`Loading preview for ${fileIdentifier}...`);

        fetch(`/preview_file/${encodeURIComponent(fileIdentifier)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to load preview: ${response.statusText}`);
                }
                return response.json();
            })
            .then(previewData => {
                console.log(`[showFilePreview] Preview data received:`, previewData);
                displayFilePreview(previewData);
            })
            .catch(error => {
                console.error(`[showFilePreview] Error loading preview:`, error);
                displayMessage(`Error loading preview for ${fileIdentifier}: ${error.message}`, true);
            });
    }

    function displayFilePreview(previewData) {
        // Create preview modal showing extracted text content
        // Create preview modal/container
        const previewContainer = document.createElement('div');
        previewContainer.className = 'file-preview-modal';
        previewContainer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        `;

        const previewContent = document.createElement('div');
        previewContent.className = 'file-preview-content';
        previewContent.style.cssText = `
            background: white;
            border-radius: 12px;
            max-width: 90%;
            max-height: 90%;
            overflow-y: auto;
            padding: 24px;
            position: relative;
        `;

        // Close button
        const closeButton = document.createElement('button');
        closeButton.innerHTML = '✕';
        closeButton.style.cssText = `
            position: absolute;
            top: 12px;
            right: 12px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #666;
        `;
        closeButton.onclick = () => document.body.removeChild(previewContainer);

        // File info header
        const fileInfo = document.createElement('div');
        fileInfo.innerHTML = `
            <h3 style="margin: 0 0 16px 0; color: #2c3e50;">📄 ${previewData.filename}</h3>
            <div style="display: flex; gap: 20px; margin-bottom: 20px; font-size: 14px; color: #666;">
                <span>📊 Size: ${formatFileSize(previewData.file_size)}</span>
                <span>📋 Type: ${previewData.file_type.toUpperCase()}</span>
                <span>📈 Rows: ${previewData.total_rows || 'Unknown'}</span>
                <span>🏷️ Headers: ${previewData.headers ? previewData.headers.length : 0}</span>
            </div>
        `;

        previewContent.appendChild(closeButton);
        previewContent.appendChild(fileInfo);

        // Headers section
        if (previewData.headers && previewData.headers.length > 0) {
            const headersSection = document.createElement('div');
            headersSection.innerHTML = `
                <h4 style="color: #2c3e50; margin: 20px 0 10px 0;">🏷️ Detected Headers</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
                    ${previewData.headers.map(header =>
                `<span style="background: #e3f2fd; color: #1976d2; padding: 4px 8px; border-radius: 4px; font-size: 12px;">${header}</span>`
            ).join('')}
                </div>
            `;
            previewContent.appendChild(headersSection);
        }

        // Extracted Text section - NEW SECTION
        if (previewData.extracted_text && previewData.extracted_text.trim()) {
            const extractedTextSection = document.createElement('div');
            
            // Header with copy button
            const headerDiv = document.createElement('div');
            headerDiv.className = 'extracted-text-header';
            headerDiv.innerHTML = `
                <h4 style="color: #2c3e50; margin: 0;">📄 Extracted Text Content</h4>
                <button class="extracted-text-copy-btn" onclick="copyExtractedText(this)">📋 Copy</button>
            `;
            
            const descriptionP = document.createElement('p');
            descriptionP.style.cssText = 'font-size: 12px; color: #666; margin: 8px 0 12px 0;';
            descriptionP.textContent = 'This shows the parsed and structured text content from the file.';

            const textContainer = document.createElement('div');
            textContainer.className = 'extracted-text-container';
            textContainer.textContent = previewData.extracted_text;
            textContainer.dataset.extractedText = previewData.extracted_text; // Store for copying

            extractedTextSection.appendChild(headerDiv);
            extractedTextSection.appendChild(descriptionP);
            extractedTextSection.appendChild(textContainer);
            previewContent.appendChild(extractedTextSection);
        }

        // Sample data section
        if (previewData.data_rows && previewData.data_rows.length > 0) {
            const dataSection = document.createElement('div');
            dataSection.innerHTML = `
                <h4 style="color: #2c3e50; margin: 20px 0 10px 0;">📊 Sample Data (First 5 rows)</h4>
            `;

            const table = document.createElement('table');
            table.style.cssText = `
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
                margin-bottom: 20px;
            `;

            // Table header
            if (previewData.headers && previewData.headers.length > 0) {
                const thead = document.createElement('thead');
                const headerRow = document.createElement('tr');
                previewData.headers.forEach(header => {
                    const th = document.createElement('th');
                    th.textContent = header;
                    th.style.cssText = `
                        background: #f8f9fa;
                        padding: 8px;
                        border: 1px solid #dee2e6;
                        font-weight: 600;
                        color: #495057;
                    `;
                    headerRow.appendChild(th);
                });
                thead.appendChild(headerRow);
                table.appendChild(thead);
            }

            // Table body
            const tbody = document.createElement('tbody');
            previewData.data_rows.forEach((row, index) => {
                const tr = document.createElement('tr');
                tr.style.backgroundColor = index % 2 === 0 ? '#fff' : '#f8f9fa';

                if (previewData.headers) {
                    previewData.headers.forEach(header => {
                        const td = document.createElement('td');
                        td.textContent = row[header] || '';
                        td.style.cssText = `
                            padding: 8px;
                            border: 1px solid #dee2e6;
                            max-width: 150px;
                            overflow: hidden;
                            text-overflow: ellipsis;
                            white-space: nowrap;
                        `;
                        tr.appendChild(td);
                    });
                } else {
                    // Handle case where headers aren't available
                    Object.values(row).forEach(value => {
                        const td = document.createElement('td');
                        td.textContent = value || '';
                        td.style.cssText = `
                            padding: 8px;
                            border: 1px solid #dee2e6;
                            max-width: 150px;
                            overflow: hidden;
                            text-overflow: ellipsis;
                            white-space: nowrap;
                        `;
                        tr.appendChild(td);
                    });
                }
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);

            dataSection.appendChild(table);
            previewContent.appendChild(dataSection);
        }

        // Raw preview for Excel files
        if (previewData.raw_preview && previewData.raw_preview.length > 0) {
            const rawSection = document.createElement('div');
            rawSection.innerHTML = `
                <h4 style="color: #2c3e50; margin: 20px 0 10px 0;">🔍 Raw File Structure (First 15 rows)</h4>
                <p style="font-size: 12px; color: #666; margin-bottom: 10px;">This shows the actual file structure to help identify where headers are located.</p>
            `;

            const rawTable = document.createElement('table');
            rawTable.style.cssText = `
                width: 100%;
                border-collapse: collapse;
                font-size: 11px;
                font-family: monospace;
            `;

            previewData.raw_preview.forEach((row, rowIndex) => {
                const tr = document.createElement('tr');
                tr.style.backgroundColor = rowIndex % 2 === 0 ? '#fff' : '#f8f9fa';

                // Add row number
                const rowNumTd = document.createElement('td');
                rowNumTd.textContent = rowIndex;
                rowNumTd.style.cssText = `
                    padding: 4px 8px;
                    border: 1px solid #dee2e6;
                    background: #e9ecef;
                    font-weight: bold;
                    text-align: center;
                    min-width: 30px;
                `;
                tr.appendChild(rowNumTd);

                Object.values(row).forEach(value => {
                    const td = document.createElement('td');
                    td.textContent = value || '';
                    td.style.cssText = `
                        padding: 4px 8px;
                        border: 1px solid #dee2e6;
                        max-width: 120px;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    `;
                    tr.appendChild(td);
                });
                rawTable.appendChild(tr);
            });

            rawSection.appendChild(rawTable);
            previewContent.appendChild(rawSection);
        }

        previewContainer.appendChild(previewContent);
        document.body.appendChild(previewContainer);

        // Close on background click
        previewContainer.addEventListener('click', (e) => {
            if (e.target === previewContainer) {
                document.body.removeChild(previewContainer);
            }
        });
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Global function for copying extracted text
    window.copyExtractedText = function(button) {
        const textContainer = button.closest('.extracted-text-header').nextElementSibling.nextElementSibling;
        const textToCopy = textContainer.dataset.extractedText;
        
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = button.textContent;
                button.textContent = '✅ Copied!';
                button.style.background = '#28a745';
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '#007bff';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                fallbackCopyTextToClipboard(textToCopy, button);
            });
        } else {
            fallbackCopyTextToClipboard(textToCopy, button);
        }
    };

    function fallbackCopyTextToClipboard(text, button) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                const originalText = button.textContent;
                button.textContent = '✅ Copied!';
                button.style.background = '#28a745';
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '#007bff';
                }, 2000);
            } else {
                button.textContent = '❌ Failed';
                button.style.background = '#dc3545';
                setTimeout(() => {
                    button.textContent = '📋 Copy';
                    button.style.background = '#007bff';
                }, 2000);
            }
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
            button.textContent = '❌ Failed';
            button.style.background = '#dc3545';
            setTimeout(() => {
                button.textContent = '📋 Copy';
                button.style.background = '#007bff';
            }, 2000);
        }
        
        document.body.removeChild(textArea);
    }

    function getFileIcon(fileType) {
        const icons = {
            'PDF': '📄',
            'XLSX': '📊',
            'XLS': '📊',
            'CSV': '📋',
            'TXT': '📝'
        };
        return icons[fileType] || '📁';
    }

    function displayMessage(message, isError = false) {
        if (typeof window.addBotMessage === 'function') {
            const prefix = isError ? "Error: " : "";
            window.addBotMessage(prefix + message);
        } else {
            console.warn("addBotMessage not found for:", message);
            alert((isError ? "Error: " : "") + message);
        }
    }

    function executeSaveTemplateRequest(templateName, mappings, skipRows, overwrite = false, fileIdentifierForContext = null) {
        console.log("[executeSaveTemplateRequest] Called with:", {
            templateName,
            mappings,
            skipRows,
            overwrite,
            fileIdentifierForContext
        });

        const payload = {
            template_name: templateName,
            field_mappings: mappings,
            skip_rows: parseInt(skipRows, 10) || 0, // Ensure skip_rows is an integer
            overwrite: overwrite
        };
        console.log("[executeSaveTemplateRequest] Payload for /save_template:", JSON.stringify(payload));

        fetch('/save_template', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        })
            .then(response => {
                console.log("[executeSaveTemplateRequest] Raw response from /save_template:", response);
                return response.json().then(data => ({ status: response.status, body: data }));
            })
            .then(({ status, body }) => {
                console.log("[executeSaveTemplateRequest] Parsed response from /save_template:", { status, body });
                if (status === 409 && body.status === 'conflict') {
                    if (confirm(body.message)) {
                        console.log("[executeSaveTemplateRequest] User confirmed overwrite for:", templateName);
                        executeSaveTemplateRequest(templateName, mappings, skipRows, true, fileIdentifierForContext); // Call again with overwrite = true
                    } else {
                        console.log("[executeSaveTemplateRequest] User cancelled overwrite for:", templateName);
                        displayMessage(`Template '${templateName}' was not saved.`);
                    }
                } else if (status === 409 && body.error_type === 'NAME_ALREADY_EXISTS_IN_OTHER_FILE') {
                    console.error("[executeSaveTemplateRequest] Error saving template:", body.message);
                    displayMessage(`Error: ${body.message}`, true);
                } else if (status >= 200 && status < 300 && body.status === 'success') {
                    console.log("[executeSaveTemplateRequest] Template saved successfully:", body.message);
                    displayMessage(body.message);
                    if (fileIdentifierForContext) {
                        // Optionally, update UI for the specific file if needed
                        console.log("[executeSaveTemplateRequest] Template context file ID:", fileIdentifierForContext);
                    }
                } else {
                    console.error("[executeSaveTemplateRequest] Error saving template, status:", status, "Body:", body);
                    const errorMessage = body.error || body.message || "Could not save template due to an unknown server error.";
                    displayMessage(`Error saving template '${templateName}': ${errorMessage}`, true);
                }
            })
            .catch(error => {
                console.error("[executeSaveTemplateRequest] Fetch error for /save_template:", error);
                displayMessage(`Network or unexpected error while saving template '${templateName}': ${error.message}`, true);
            });
    }

    window.triggerSaveTemplateWorkflow = function (fileIdentifier, contextElement) {
        console.log("[triggerSaveTemplateWorkflow] Called for fileIdentifier:", fileIdentifier, "Context Element:", contextElement);
        const fileEntryElement = contextElement.closest('.file-entry');
        if (!fileEntryElement) {
            console.error("[triggerSaveTemplateWorkflow] Could not find parent .file-entry for context element.");
            displayMessage("Error: Could not find file context for saving template.", true);
            return;
        }

        const templateName = prompt("Enter a name for this template:");
        if (!templateName || templateName.trim() === "") {
            console.log("[triggerSaveTemplateWorkflow] User cancelled or entered empty template name.");
            return;
        }

        const currentMappings = [];
        const mappingRows = fileEntryElement.querySelectorAll('.mapping-table tbody tr');
        mappingRows.forEach(row => {
            const originalHeader = row.cells[0].textContent;
            const mappedFieldSelect = row.cells[1].querySelector('select');
            const mappedField = mappedFieldSelect ? mappedFieldSelect.value : null;
            const confidence = row.cells[2].textContent; // This is display text like "80%"

            // We need to store the raw confidence score if available, or derive it
            // For simplicity, let's assume the backend recalculates confidence or it's not critical for template saving here
            // Or, if we stored it in a data attribute on the element, we could retrieve it.
            // For now, just sending what's easily available.
            if (mappedField && mappedField !== '__IGNORE__' && mappedField !== '__CREATE_NEW__') { // Only save actual mappings
                currentMappings.push({
                    original_header: originalHeader,
                    mapped_field: mappedField,
                    // confidence: parseFloat(confidence) / 100 || 0 // Example if confidence was just number
                });
            }
        });

        if (currentMappings.length === 0) {
            console.warn("[triggerSaveTemplateWorkflow] No valid mappings found to save for template.");
            displayMessage("No field mappings to save for this template.", true);
            return;
        }

        const skipRowsInput = fileEntryElement.querySelector(`input[id^="skipRows-"]`);
        const skipRows = skipRowsInput ? parseInt(skipRowsInput.value, 10) : 0;
        if (isNaN(skipRows) || skipRows < 0) {
            console.warn("[triggerSaveTemplateWorkflow] Invalid skip_rows value, defaulting to 0. Value:", skipRowsInput ? skipRowsInput.value : 'N/A');
            skipRows = 0;
        }

        console.log("[triggerSaveTemplateWorkflow] Preparing to save template:", { templateName, currentMappings, skipRows, fileIdentifier });
        executeSaveTemplateRequest(templateName.trim(), currentMappings, skipRows, false, fileIdentifier);
    };

    // Modified function signature to accept fieldDefinitionsObject
    function renderMappingTable(containerElement, fileIdentifier, fileType, headers, fieldMappings, fieldDefinitionsObject, fileIndex) {
        console.log('[renderMappingTable] Called with containerElement:', containerElement);

        if (!containerElement) {
            console.error('[renderMappingTable] containerElement is null or undefined!');
            return;
        }

        // Clear the container
        containerElement.innerHTML = ''; // Clear previous content directly

        // Create the new header and actions box
        const headerActionsBox = document.createElement('div');
        headerActionsBox.className = 'mapping-header-actions-box';

        // Add pseudo-headers
        const headerTitles = ['Original Header', 'Mapped Field', 'Confidence', 'Action'];
        headerTitles.forEach(title => {
            const headerSpan = document.createElement('span');
            headerSpan.className = 'pseudo-table-header';
            headerSpan.textContent = title;
            headerActionsBox.appendChild(headerSpan);
        });

        containerElement.appendChild(headerActionsBox); // Add the new box to the container

        // Create the table for mapping rows (without its own thead)
        const table = document.createElement('table');
        table.className = 'mapping-table-rows-only'; // New class for styling
        const tbody = table.createTBody();

        headers.forEach((header, index) => {
            const row = tbody.insertRow();
            const originalHeaderCell = row.insertCell();
            originalHeaderCell.textContent = header;

            const mappedFieldCell = row.insertCell();
            const select = document.createElement('select');
            select.className = 'mapping-select';
            select.dataset.originalHeader = header;
            select.dataset.fileIdentifier = fileIdentifier; // For context

            // Add an initial blank/unmapped option
            const unmappedOption = document.createElement('option');
            unmappedOption.value = '';
            unmappedOption.textContent = '--- Select Field ---';
            select.appendChild(unmappedOption);

            // Add "Create New Field" option
            const createNewOption = document.createElement('option');
            createNewOption.value = '__CREATE_NEW__';
            createNewOption.textContent = '--- Create New Field ---';
            select.appendChild(createNewOption);

            // Add "Ignore this Field" option
            const ignoreOption = document.createElement('option');
            ignoreOption.value = '__IGNORE__';
            ignoreOption.textContent = '--- Ignore this Field ---';
            select.appendChild(ignoreOption);

            // Use the passed fieldDefinitionsObject
            for (const fieldName in fieldDefinitionsObject) {
                const option = document.createElement('option');
                option.value = fieldName;
                option.textContent = fieldName;
                if (fieldMappings[index] && fieldMappings[index].mapped_field === fieldName) {
                    option.selected = true;
                }
                select.appendChild(option);
            }
            mappedFieldCell.appendChild(select);

            const confidenceCell = row.insertCell();
            // Diagnostic logging for confidence score
            const mappingEntry = fieldMappings[index];
            console.log(`[renderMappingTable] Header: '${header}', Index: ${index}, Mapping Entry:`, JSON.stringify(mappingEntry));

            let confidenceText = 'N/A'; // MODIFIED: Default to N/A
            if (mappingEntry) {
                console.log(`[renderMappingTable] Confidence Score for '${header}':`, mappingEntry.confidence_score, "Type:", typeof mappingEntry.confidence_score);
                // MODIFIED: Added isNaN check
                if (typeof mappingEntry.confidence_score === 'number' && !isNaN(mappingEntry.confidence_score)) {
                    confidenceText = mappingEntry.confidence_score.toFixed(0) + '%';
                } else if (mappingEntry.confidence_score !== undefined && mappingEntry.confidence_score !== null) {
                    console.warn(`[renderMappingTable] Unexpected confidence_score for '${header}':`, mappingEntry.confidence_score, "Type:", typeof mappingEntry.confidence_score, "- Displaying N/A.");
                }
            }
            confidenceCell.textContent = confidenceText; // MODIFIED: Use the determined confidenceText

            const actionCell = row.insertCell();
            const helpButton = document.createElement('button');
            helpButton.textContent = 'Suggest Alternatives';
            helpButton.className = 'chatbot-help-button btn btn-info btn-sm'; // Added .btn .btn-info .btn-sm
            helpButton.dataset.originalHeader = header;
            helpButton.dataset.currentMapping = select.value; // Set initial current mapping
            helpButton.dataset.fileIdentifier = fileIdentifier;
            actionCell.appendChild(helpButton);

            select.addEventListener('change', function () {
                helpButton.dataset.currentMapping = this.value; // Update on change
                // If "Create New Field" is selected
                if (this.value === '__CREATE_NEW__') {
                    const newFieldName = prompt(`Enter the name for the new field that will map to "${header}":`);
                    if (newFieldName && newFieldName.trim() !== "") {
                        const newFieldKey = newFieldName.trim().toUpperCase().replace(/\s+/g, '_');

                        // Check if this new field key already exists in fieldDefinitionsObject
                        if (fieldDefinitionsObject.hasOwnProperty(newFieldKey)) {
                            alert(`A field with the key "${newFieldKey}" already exists. Please choose a different name or select the existing field.`);
                            this.value = ''; // Reset dropdown
                            helpButton.dataset.currentMapping = '';
                            return;
                        }

                        // Add to global FIELD_DEFINITIONS (client-side) and the passed fieldDefinitionsObject
                        FIELD_DEFINITIONS[newFieldKey] = { description: "User-created field", aliases: [header], data_type: "text", validation_rules: {} };
                        fieldDefinitionsObject[newFieldKey] = FIELD_DEFINITIONS[newFieldKey]; // ensure consistency if it's a copy

                        // Add as a new option to ALL select elements
                        document.querySelectorAll('.mapping-select').forEach(s => {
                            const option = document.createElement('option');
                            option.value = newFieldKey;
                            option.textContent = newFieldKey;
                            // Insert before the "Create New Field" option
                            const createNewOpt = Array.from(s.options).find(opt => opt.value === '__CREATE_NEW__');
                            if (createNewOpt) {
                                s.insertBefore(option, createNewOpt);
                            } else { // Fallback if "Create New Field" option isn't found (should not happen)
                                s.appendChild(option);
                            }
                        });

                        this.value = newFieldKey; // Select the newly created field
                        helpButton.dataset.currentMapping = newFieldKey;
                        displayMessage(`New field "${newFieldKey}" created and selected for "${header}".`);
                    } else {
                        this.value = ''; // Reset if user cancels or enters empty name
                        helpButton.dataset.currentMapping = '';
                    }
                }
            });

            helpButton.addEventListener('click', function () {
                const originalHeader = this.dataset.originalHeader;
                const currentMapping = this.dataset.currentMapping; // This is the currently selected value in the dropdown
                const fileIdentifier = this.dataset.fileIdentifier;

                console.log(`[Suggest Alternatives] Clicked for: Header='${originalHeader}', CurrentMap='${currentMapping}', File='${fileIdentifier}'`);

                const anySelect = document.querySelector('.mapping-select');
                let standardFieldNames = [];
                if (anySelect) {
                    standardFieldNames = Array.from(anySelect.options)
                        .map(opt => opt.value)
                        .filter(val => val && val !== '__CREATE_NEW__' && val !== '__IGNORE__');
                }

                if (standardFieldNames.length === 0) {
                    displayMessage("Could not retrieve standard field names to suggest alternatives.", true);
                    return;
                }

                if (typeof window.openChatbotPanel !== 'function' || typeof window.addBotMessage !== 'function') {
                    console.error("Chatbot functions (openChatbotPanel or addBotMessage) are not available.");
                    displayMessage("Chatbot functionality is not available to display suggestions.", true);
                    return;
                }

                window.openChatbotPanel();
                window.addBotMessage(`Suggesting alternatives for header: "${originalHeader}" (currently mapped to: ${currentMapping || 'N/A'})...`);

                fetch('/chatbot_suggest_mapping', { // MODIFIED: Corrected endpoint
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        original_header: originalHeader,
                        current_mapped_field: currentMapping, // MODIFIED: Corrected key
                        standard_field_names: standardFieldNames // Kept for potential future use, backend currently ignores it
                    })
                })
                    .then(response => {
                        if (!response.ok) {
                            // Try to get error message from response body if possible
                            return response.json().then(errData => {
                                throw new Error(errData.error || `Server error: ${response.status}`);
                            }).catch(() => { // If parsing error body fails
                                throw new Error(`Server error: ${response.status}`);
                            });
                        }
                        return response.json();
                    })
                    .then(suggestionsArray => {
                        if (suggestionsArray && suggestionsArray.length > 0) {
                            if (suggestionsArray.length === 1 && suggestionsArray[0].suggested_field === 'N/A') {
                                window.addBotMessage(`No alternative suggestions found for "${originalHeader}". ${suggestionsArray[0].reason || ''}`);
                                return;
                            }

                            // Check for auto-apply suggestions
                            const autoApplySuggestion = suggestionsArray.find(s => s.auto_apply === true);

                            if (autoApplySuggestion) {
                                // Auto-apply the best suggestion
                                const confidence = Math.round((autoApplySuggestion.confidence || 0) * 100);
                                window.addBotMessage(`🎯 High confidence match found! Auto-applying "${autoApplySuggestion.suggested_field}" (${confidence}% confidence)`);

                                // Apply the mapping automatically
                                const allSelects = document.querySelectorAll(`.mapping-select[data-original-header="${originalHeader}"]`);
                                if (allSelects.length > 0) {
                                    allSelects.forEach(selectElement => {
                                        selectElement.value = autoApplySuggestion.suggested_field;
                                        selectElement.dispatchEvent(new Event('change'));
                                    });
                                    window.addBotMessage(`✅ Applied "${autoApplySuggestion.suggested_field}" to "${originalHeader}". Reason: ${autoApplySuggestion.reason}`);
                                }
                            }

                            // Create interactive suggestions container
                            const suggestionsContainer = document.createElement('div');
                            suggestionsContainer.className = 'suggestions-container';

                            const headerText = document.createElement('div');
                            headerText.innerHTML = `<strong>💡 Suggestions for "${originalHeader}":</strong>`;
                            suggestionsContainer.appendChild(headerText);

                            const suggestionsList = document.createElement('div');
                            suggestionsList.className = 'suggestions-list';

                            suggestionsArray.forEach((suggestion, index) => {
                                if (suggestion.suggested_field !== 'N/A') {
                                    const suggestionElement = document.createElement('div');
                                    suggestionElement.className = 'chatbot-suggestion';
                                    suggestionElement.setAttribute('data-suggested-field', suggestion.suggested_field);

                                    const confidence = Math.round((suggestion.confidence || 0) * 100);
                                    const confidenceColor = confidence > 80 ? '#28a745' : confidence > 60 ? '#ffc107' : '#6c757d';

                                    suggestionElement.innerHTML = `
                                    <div class="suggestion-field">${suggestion.suggested_field}</div>
                                    <div class="suggestion-reason">${suggestion.reason || 'No reason provided'}</div>
                                    <div class="suggestion-confidence" style="color: ${confidenceColor};">
                                        ${confidence}% confidence ${suggestion.auto_apply ? '(Auto-applied)' : ''}
                                    </div>
                                `;

                                    if (suggestion.auto_apply) {
                                        suggestionElement.style.backgroundColor = '#d4edda';
                                        suggestionElement.style.borderColor = '#28a745';
                                    }

                                    suggestionsList.appendChild(suggestionElement);
                                }
                            });

                            suggestionsContainer.appendChild(suggestionsList);
                            window.addBotMessage(suggestionsContainer);

                            if (!autoApplySuggestion) {
                                window.addBotMessage("Click on any suggestion above to apply it to your mapping.");
                            }
                        } else {
                            window.addBotMessage(`No alternative suggestions found for "${originalHeader}".`);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching suggestions:', error);
                        window.addBotMessage(`Network error while fetching suggestions for "${originalHeader}": ${error.message}`, true);
                    });
            });

        });

        // fileEntryDiv.appendChild(table); // Changed: append to the containerElement
        containerElement.appendChild(table);

        // Removed the setTimeout wrapper as direct manipulation should be fine now
    }

    if (uploadForm) {
        console.log("[upload.js] uploadForm element found:", uploadForm); // New Log
        uploadForm.addEventListener('submit', function (event) {
            console.log("[upload.js] Submit event triggered on uploadForm."); // New Log
            event.preventDefault(); // Ensure this is the very first line
            console.log("[upload.js] event.preventDefault() CALLED."); // New Log

            try {
                const files = fileInput.files;
                if (files.length === 0) {
                    displayMessage("Please select files to upload.", true);
                    return;
                }

                console.log("Preparing FormData..."); // Diagnostic log
                const formData = new FormData();
                for (let i = 0; i < files.length; i++) {
                    formData.append('files[]', files[i]);
                }

                console.log("Setting up XMLHttpRequest..."); // Diagnostic log
                const xhr = new XMLHttpRequest();
                uploadStartTime = Date.now();
                console.log("[upload.js] XHR object created. Upload start time:", uploadStartTime); // New Log

                // Local formatTime function for progress events
                function formatTime(seconds) {
                    if (isNaN(seconds) || seconds < 0) return 'N/A';
                    const mins = Math.floor(seconds / 60);
                    const secs = Math.floor(seconds % 60);
                    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                }

                xhr.upload.addEventListener('progress', function (event) {
                    console.log("[upload.js] XHR progress event:", event); // New Log
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        if (overallProgressBar) {
                            overallProgressBar.style.width = percentComplete.toFixed(2) + '%';
                            overallProgressBar.textContent = percentComplete.toFixed(2) + '%';
                        }

                        // Update the ETA display if available
                        if (etaDisplay && uploadStartTime) {
                            const elapsedMs = Date.now() - uploadStartTime;
                            if (elapsedMs > 0 && percentComplete > 0) {
                                // Calculate remaining time based on elapsed time and percentage
                                const totalTimeEstimateMs = (elapsedMs / percentComplete) * 100;
                                const remainingTimeSeconds = (totalTimeEstimateMs - elapsedMs) / 1000;
                                etaDisplay.textContent = formatTime(remainingTimeSeconds);
                            }
                        }
                    }
                });

                // Internal helper function for formatting time display
                function formatTime(seconds) {
                    if (isNaN(seconds) || seconds < 0) return 'N/A';
                    const mins = Math.floor(seconds / 60);
                    const secs = Math.floor(seconds % 60);
                    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                }

                xhr.addEventListener('load', function () {
                    console.log("[upload.js] XHR load event triggered. Status:", xhr.status, "Response Text:", xhr.responseText.substring(0, 500) + "..."); // New Log + truncate response
                    if (overallProgressBar) {
                        overallProgressBar.style.width = '100%';
                        overallProgressBar.textContent = '100%';
                    }
                    if (etaDisplay) etaDisplay.textContent = formatTime(0);

                    fileStatusesDiv.innerHTML = ''; // Clear previous statuses
                    console.log("[upload.js] fileStatusesDiv cleared and ready for new content.");
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const results = JSON.parse(xhr.responseText);
                            console.log("Upload results:", results); // Diagnostic log

                            // Ensure FIELD_DEFINITIONS is available globally or passed appropriately
                            if (typeof FIELD_DEFINITIONS === 'undefined') {
                                console.error('FIELD_DEFINITIONS is not defined. Cannot render mapping tables.');
                                displayMessage('Critical error: Field definitions not loaded. Please refresh.', true);
                                return;
                            }

                            console.log("[RESULTS PROCESSING] Starting results processing, count:", results.length);
                            results.forEach((fileResult, index) => {
                                const fileEntryDiv = document.createElement('div');
                                fileEntryDiv.className = 'file-entry';
                                const fileIdentifierSafe = fileResult.filename.replace(/[^a-zA-Z0-9]/g, '_');
                                fileEntryDiv.id = `file-entry-${fileIdentifierSafe}`;
                                console.log(`[File Result ${index}] Processing fileResult:`, fileResult);

                                // --- Updated grouped controls logic for single-line display ---
                                let settingsItems = [];

                                // 1. Rows to Skip input (conditional)
                                if (fileResult.file_type === 'CSV' || fileResult.file_type === 'XLSX' || fileResult.file_type === 'XLS') {
                                    settingsItems.push(`
                                        <span class="setting-item skip-rows-group">
                                            <label for="skipRows-${fileIdentifierSafe}">Rows to Skip (Header):</label>
                                            <input type="number" id="skipRows-${fileIdentifierSafe}" name="skipRows-${fileIdentifierSafe}" value="${fileResult.skip_rows !== undefined ? fileResult.skip_rows : 0}" min="0" class="skip-rows-input">
                                        </span>
                                    `);
                                }

                                // 2. Template Selection dropdown (conditional on success)
                                if (fileResult.success) {
                                    settingsItems.push(`
                                        <span class="setting-item template-select-group">
                                            <label for="templateSelect-${fileIdentifierSafe}">Template:</label>
                                            <select id="templateSelect-${fileIdentifierSafe}" class="template-select modern-select" data-file-identifier="${fileResult.filename}" data-file-identifier-safe="${fileIdentifierSafe}" data-file-type="${fileResult.file_type}">
                                                <option value="">-- Select a Template --</option>
                                            </select>
                                        </span>
                                    `);
                                }

                                // 3. Apply Settings button (conditional)
                                if (fileResult.file_type === 'CSV' || fileResult.file_type === 'XLSX' || fileResult.file_type === 'XLS') {
                                    // This button will be a direct flex item in file-settings-box
                                    settingsItems.push(`
                                        <button type="button" id="applySkipRows-${fileIdentifierSafe}" class="apply-settings-button apply-skip-rows-btn btn btn-secondary btn-sm">Apply Settings</button>
                                    `);
                                }

                                const settingsBoxHTML = settingsItems.length > 0 ? `<div class="file-settings-box">${settingsItems.join('')}</div>` : '';
                                // --- End of updated grouped controls logic ---

                                // --- Create Save Template Button Box (Re-introduced) ---
                                const saveTemplateButtonHTML = fileResult.success ? `
                                    <div class="save-template-box">
                                        <button class="save-template-button btn btn-warning" data-file-identifier="${fileResult.filename}">Save as Template</button>
                                    </div>
                                ` : '';
                                // --- End Create Save Template Button Box ---


                                // Enhanced file info display
                                const fileIcon = getFileIcon(fileResult.file_type);
                                const statusIcon = fileResult.success ? '✅' : '❌';
                                const templateInfo = fileResult.applied_template_name ?
                                    `<div class="template-applied">🎯 Template: <strong>${fileResult.applied_template_name}</strong> (Skip ${fileResult.skip_rows} rows)</div>` : '';

                                fileEntryDiv.innerHTML = `
                                    <div class="file-header-enhanced">
                                        <div class="file-info-row">
                                            <div class="file-icon-large">${fileIcon}</div>
                                            <div class="file-details">
                                                <h3 class="file-name-enhanced">${fileResult.filename}</h3>
                                                <div class="file-meta-row">
                                                    <span class="file-type-badge ${fileResult.file_type.toLowerCase()}">${fileResult.file_type}</span>
                                                    <span class="headers-count">📋 ${fileResult.headers ? fileResult.headers.length : 0} headers</span>
                                                    <span class="mappings-count">🔗 ${fileResult.field_mappings ? fileResult.field_mappings.length : 0} mappings</span>
                                                    <span class="file-status-badge ${fileResult.success ? 'success' : 'error'}">${statusIcon} ${fileResult.success ? 'Ready' : 'Failed'}</span>
                                                </div>
                                                ${templateInfo}
                                            </div>
                                        </div>
                                        <div class="file-message ${fileResult.success ? 'success' : 'error'}">
                                            ${fileResult.message}
                                        </div>
                                    </div>
                                    ${settingsBoxHTML}
                                    <div class="mapping-controls-box">
                                        <button class="process-file-button btn btn-success" data-file-identifier="${fileResult.filename}" data-file-type="${fileResult.file_type}" data-file-index="${index}" ${!fileResult.success ? 'disabled' : ''}>🚀 Process File Data</button>
                                        <button class="preview-file-button btn btn-info" data-file-identifier="${fileResult.filename}" ${!fileResult.success ? 'disabled' : ''}>👁️ Preview File</button>
                                        <button class="view-file-button btn btn-secondary" data-file-identifier="${fileResult.filename}" ${!fileResult.success ? 'disabled' : ''}>📄 View Raw File</button>
                                        <button class="download-processed-button btn btn-primary" data-file-identifier="${fileResult.filename}" style="display:none;" disabled>📥 Download Results</button>
                                    </div>
                                    ${saveTemplateButtonHTML}
                                    <div class="mapping-table-container" id="mapping-table-container-${fileIdentifierSafe}"></div>
                                    <div class="data-preview-area" id="data-preview-${fileIdentifierSafe}"></div>
                                    <div class="validation-summary-area" id="validation-summary-${fileIdentifierSafe}\"></div>
                                `;

                                // Append to fileStatusesDiv first
                                fileStatusesDiv.appendChild(fileEntryDiv);
                                console.log(`[File Result ${index}] appended fileEntryDiv to fileStatusesDiv`);

                                if (fileResult.success && fileResult.headers && fileResult.headers.length > 0) {
                                    console.log(`[File Result ${index}] File has headers, rendering mapping table`);

                                    // Force browser to process DOM updates before querying elements
                                    setTimeout(() => {
                                        const mappingTableContainer = document.querySelector(`#mapping-table-container-${fileIdentifierSafe}`);
                                        console.log(`[File Result ${index}] mappingTableContainer:`, mappingTableContainer);

                                        // Make sure we have all the necessary data and elements
                                        if (!mappingTableContainer) {
                                            console.error(`[File Result ${index}] Failed to find mapping table container for ${fileIdentifierSafe}`);
                                            displayMessage(`Error: Failed to create mapping UI for ${fileResult.filename}`, true);
                                            return;
                                        }

                                        if (!FIELD_DEFINITIONS) {
                                            console.error(`[File Result ${index}] FIELD_DEFINITIONS is not available`);
                                            displayMessage(`Error: Field definitions not loaded. Please refresh.`, true);
                                            return;
                                        }

                                        try {
                                            // Pass FIELD_DEFINITIONS to renderMappingTable (removed fileResult.success)
                                            renderMappingTable(mappingTableContainer, fileResult.filename, fileResult.file_type, fileResult.headers, fileResult.field_mappings, FIELD_DEFINITIONS, index);
                                            console.log(`[File Result ${index}] mapping table rendered`);
                                        } catch (err) {
                                            console.error(`[File Result ${index}] Error rendering mapping table:`, err);
                                            displayMessage(`Error: Could not create mapping interface for ${fileResult.filename}. See console for details.`, true);
                                        }
                                    }, 50); // Short delay to ensure DOM is ready
                                }

                                // For all successful files, try to populate the template dropdown
                                // Do this last after all HTML elements are created and added to the DOM
                                if (fileResult.success) {
                                    setTimeout(() => {
                                        const templateSelect = document.querySelector(`#templateSelect-${fileIdentifierSafe}`);
                                        console.log(`[File Result ${index}] templateSelect found:`, templateSelect);
                                        if (templateSelect) {
                                            populateTemplateDropdown(templateSelect, fileResult.filename);
                                            console.log(`[File Result ${index}] populateTemplateDropdown called`);

                                            // If a template was auto-applied by backend, select it in the dropdown
                                            if (fileResult.applied_template_filename) {
                                                // Wait a brief moment for populateTemplateDropdown to potentially finish
                                                setTimeout(() => {
                                                    if (Array.from(templateSelect.options).some(opt => opt.value === fileResult.applied_template_filename)) {
                                                        templateSelect.value = fileResult.applied_template_filename;
                                                        console.log(`[File Result ${index}] Auto-selected template '${fileResult.applied_template_filename}' in dropdown.`);
                                                    } else {
                                                        console.warn(`[File Result ${index}] Auto-applied template '${fileResult.applied_template_filename}' not found in dropdown options after population.`);
                                                    }
                                                }, 200); // Adjust delay if needed
                                            }
                                        } else {
                                            console.error(`[File Result ${index}] templateSelect not found!`);
                                        }

                                        // Add event listener for skip rows button if applicable
                                        if (fileResult.file_type === 'CSV' || fileResult.file_type === 'XLSX' || fileResult.file_type === 'XLS') {
                                            addSkipRowsEventListener(fileIdentifierSafe, fileResult.filename, fileResult.file_type);
                                        }
                                    }, 100);
                                }

                                if (fileResult.success && fileResult.headers && fileResult.headers.length > 0) {
                                    // Already handled above
                                } else if (fileResult.success) {
                                    const noHeadersMsg = document.createElement('p');
                                    noHeadersMsg.textContent = 'No headers were extracted from this file. Manual processing might be required or the file might be empty/unsuitable.';
                                    fileEntryDiv.appendChild(noHeadersMsg);
                                } else if (!fileResult.success) {
                                    const errorP = document.createElement('p');
                                    errorP.textContent = `Error: ${fileResult.message}`;
                                    errorP.style.color = 'red';
                                    fileEntryDiv.appendChild(errorP);
                                }
                                fileStatusesDiv.appendChild(fileEntryDiv);
                            });
                        } catch (e_parse) {
                            console.error("Error parsing server response JSON:", e_parse, xhr.responseText);
                            displayMessage(`Error parsing server response: ${e_parse.message}`, true);
                        }
                    } else {
                        console.error("XHR load error - Status:", xhr.status, "Response:", xhr.responseText);
                        displayMessage(`Upload failed: Server status ${xhr.status}. ${xhr.responseText}`, true);
                    }
                });

                xhr.addEventListener('error', function (event) {
                    console.error("[upload.js] XHR error event triggered.", event); // New Log
                    displayMessage('Upload network error. Please check your connection.', true);
                    fileStatusesDiv.innerHTML = '<p class="failure">Upload failed due to a network error.</p>'; // More specific message
                });
                xhr.addEventListener('abort', function (event) {
                    console.warn("[upload.js] XHR abort event triggered.", event); // New Log
                    displayMessage('Upload aborted by the user or a network issue.', true);
                    fileStatusesDiv.innerHTML = '<p class="warning">Upload aborted.</p>'; // More specific message
                });

                xhr.open('POST', '/upload', true);
                console.log("[upload.js] XHR request opened for POST to /upload."); // New Log
                xhr.send(formData);
                console.log("[upload.js] XHR send called. formData:", formData); // New Log
                fileStatusesDiv.innerHTML = '<p>Starting upload...</p>';

            } catch (e) { // Catch errors in the main submit handler logic (FormData, XHR setup)
                console.error("Error in uploadForm submit handler:", e);
                alert("An error occurred during upload preparation: " + e.message);
                // Optionally, reset UI elements like progress bar here if needed
                if (overallProgressBar) {
                    overallProgressBar.style.width = '0%';
                    overallProgressBar.textContent = '0%';
                }
                if (etaDisplay) etaDisplay.textContent = 'N/A';
                fileStatusesDiv.innerHTML = '<p class="failure">Upload failed due to a client-side error.</p>';
            }
        });
    }

    // Delegated event listener for dynamically added buttons
    fileStatusesDiv.addEventListener('click', function (event) {
        const target = event.target;
        console.log("[fileStatusesDiv Click Delegate] Clicked on:", target);

        if (target.classList.contains('process-file-button')) {
            console.log("[Process File Button Clicked] Target dataset:", target.dataset);
            console.log("[Process File Button Clicked] Target:", target);

            const fileIdentifier = target.dataset.fileIdentifier;
            const fileType = target.dataset.fileType;
            // Ensure fileIndex is correctly retrieved or passed if needed by skipRows logic
            const fileIndexAttribute = target.getAttribute('data-file-index'); // Get the attribute directly
            const fileEntryElement = target.closest('.file-entry');

            console.log("[Process File Button] fileIdentifier:", fileIdentifier);
            console.log("[Process File Button] fileType:", fileType);
            console.log("[Process File Button] fileIndexAttribute:", fileIndexAttribute);
            console.log("[Process File Button] fileEntryElement:", fileEntryElement);

            if (!fileEntryElement) {
                console.error("[Process File Button] Could not find parent .file-entry.");
                displayMessage("Error: Could not find file context for processing.", true);
                return;
            }

            const finalizedMappings = [];
            // MODIFIED: Changed selector to use .mapping-table-rows-only
            const mappingSelects = fileEntryElement.querySelectorAll('.mapping-table-rows-only .mapping-select');
            console.log("[Process File Button] Found mappingSelects count:", mappingSelects.length); // Log how many selects were found

            mappingSelects.forEach(select => {
                if (select.value && select.value !== '__IGNORE__' && select.value !== '__CREATE_NEW__') {
                    finalizedMappings.push({
                        original_header: select.dataset.originalHeader,
                        mapped_field: select.value
                    });
                }
            });

            // Corrected skipRows input selector using the fileIndexAttribute
            // Use the safe identifier based on filename just like in the upload results handler
            const fileIdentifierSafe = fileIdentifier.replace(/[^a-zA-Z0-9]/g, '_');
            console.log("[Process File Button] fileIdentifierSafe:", fileIdentifierSafe);

            // Try to find the skip rows input using the safe identifier
            const skipRowsInput = fileEntryElement.querySelector(`input[id="skipRows-${fileIdentifierSafe}"]`);
            console.log("[Process File Button] skipRowsInput found:", skipRowsInput);

            let skipRows = 0;
            if (skipRowsInput) {
                skipRows = parseInt(skipRowsInput.value, 10);
                if (isNaN(skipRows) || skipRows < 0) {
                    console.warn(`[Process File Button] Invalid skip_rows for ${fileIdentifier}: ${skipRowsInput.value}. Defaulting to 0.`);
                    skipRows = 0;
                }
            } else {
                // If input not found, log appropriately.
                // This might happen if file_type doesn't generate skipRows input (e.g. PDF)
                if (fileType === 'CSV' || fileType === 'XLSX' || fileType === 'XLS') {
                    console.warn(`[Process File Button] skipRows input not found for ${fileIdentifier} with safe identifier ${fileIdentifierSafe}. Defaulting to 0.`);
                } else {
                    console.log(`[Process File Button] No skipRows input expected for file type ${fileType}. Defaulting to 0.`);
                }
            }

            console.log(`[Process File Button] Processing ${fileIdentifier} (Type: ${fileType}, Skip: ${skipRows}) with mappings:`, finalizedMappings);

            fetch('/process_file_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_identifier: fileIdentifier,
                    finalized_mappings: finalizedMappings,
                    file_type: fileType,
                    skip_rows: skipRows
                })
            })
                .then(response => {
                    console.log("[Process File Button] Raw response from /process_file_data:", response);
                    return response.json().then(data => ({ status: response.status, body: data }));
                })
                .then(({ status, body }) => {
                    console.log("[Process File Button] Parsed response from /process_file_data:", { status, body });
                    if (status >= 200 && status < 300 && body.data) {
                        displayMessage(body.message || `Successfully processed ${fileIdentifier}.`);
                        console.log(`[Process File Button] Data for ${fileIdentifier}:`, body.data);

                        // Cache the processed data
                        window.extractedDataCache = window.extractedDataCache || {};
                        window.extractedDataCache[fileIdentifier] = body.data;

                        const dataDisplayDiv = document.createElement('div');
                        dataDisplayDiv.className = 'processed-data-display';
                        dataDisplayDiv.innerHTML = `<h3>Processed Data for ${fileIdentifier}</h3><pre>${JSON.stringify(body.data, null, 2)}</pre>`;
                        // Check if a display area for this file already exists, if so, replace it, otherwise append.
                        let existingDataDisplay = fileEntryElement.querySelector('.processed-data-display');
                        if (existingDataDisplay) {
                            existingDataDisplay.replaceWith(dataDisplayDiv);
                        } else {
                            fileEntryElement.appendChild(dataDisplayDiv);
                        }

                        // Show and enable the download button
                        const downloadBtn = fileEntryElement.querySelector('.download-processed-button');
                        if (downloadBtn) {
                            downloadBtn.style.display = 'inline-block';
                            downloadBtn.disabled = false;
                        }

                    } else {
                        const errorMsg = body.error || body.message || "Unknown error processing file.";
                        console.error(`[Process File Button] Error processing ${fileIdentifier}: ${errorMsg}`);
                        displayMessage(`Error processing ${fileIdentifier}: ${errorMsg}`, true);
                    }
                })
                .catch(error => {
                    console.error(`[Process File Button] Fetch error for /process_file_data for ${fileIdentifier}:`, error);
                    displayMessage(`Network or unexpected error while processing ${fileIdentifier}: ${error.message}`, true);
                });
        } else if (target.classList.contains('save-template-button')) {
            console.log("[Save Template Button Clicked] Target dataset:", target.dataset);
            const fileIdentifier = target.dataset.fileIdentifier;
            window.triggerSaveTemplateWorkflow(fileIdentifier, target);
        } else if (target.classList.contains('chatbot-help-button')) {
            // ... (chatbot help button logic as before)
            console.log("[Chatbot Help Button Clicked] Target dataset:", target.dataset);
            const originalHeader = target.dataset.originalHeader;
            const currentMappedField = target.dataset.currentMapping; // This should be updated by select change
            const fileEntryElement = target.closest('.file-entry');
            const fileIdentifier = target.dataset.fileIdentifier;

            if (!fileEntryElement) {
                console.error("[Chatbot Help Button] Could not find parent .file-entry.");
                return;
            }
            // Store context for the chatbot
            window.setCurrentChatbotContext(originalHeader, currentMappedField, fileEntryElement, fileIdentifier);
            // Open/focus chatbot panel and inform user
            if (typeof window.openChatbotPanel === 'function') {
                window.openChatbotPanel();
                window.addBotMessage(`I can help with suggestions for mapping "${originalHeader}". What are you looking for?`);
            } else {
                console.warn("openChatbotPanel or addBotMessage not available.")
            }
        } else if (target.classList.contains('preview-file-button')) {
            const fileIdentifier = target.dataset.fileIdentifier;
            console.log(`[Preview File Button Clicked] File Identifier: ${fileIdentifier}`);
            showFilePreview(fileIdentifier);
        } else if (target.classList.contains('view-file-button')) {
            const fileIdentifier = target.dataset.fileIdentifier;
            console.log(`[View File Button Clicked] File Identifier: ${fileIdentifier}`);
            // Assuming the backend serves the file at a specific URL, e.g., /view_uploaded_file/<filename>
            // Adjust the URL as per your backend route
            window.open(`/view_uploaded_file/${encodeURIComponent(fileIdentifier)}`, '_blank');
        } else if (target.classList.contains('download-processed-button')) {
            const fileIdentifier = target.dataset.fileIdentifier;
            console.log(`[Download Processed Button Clicked] File Identifier: ${fileIdentifier}`);

            const processedData = window.extractedDataCache ? window.extractedDataCache[fileIdentifier] : null;

            if (!processedData) {
                displayMessage(`No processed data found for ${fileIdentifier} to download. Please process the file first.`, true);
                console.error(`[Download Processed Button] No data in cache for ${fileIdentifier}`);
                return;
            }

            console.log(`[Download Processed Button] Data for ${fileIdentifier} from cache:`, processedData);

            // Disable button to prevent multiple clicks during download
            target.disabled = true;
            target.textContent = 'Preparing Download...';

            fetch('/download_processed_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_identifier: fileIdentifier,
                    data_to_download: processedData
                })
            })
                .then(response => {
                    if (!response.ok) {
                        // Try to parse error message from server if available
                        return response.json().then(errBody => {
                            throw new Error(errBody.error || `Server error: ${response.status}`);
                        }).catch(() => {
                            // Fallback if error body is not JSON or no specific error message
                            throw new Error(`Server error: ${response.status}`);
                        });
                    }
                    // Get filename from content-disposition header if possible
                    const contentDisposition = response.headers.get('content-disposition');
                    let filename = `processed_${fileIdentifier}.csv`; // Default filename
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
                        if (filenameMatch && filenameMatch.length > 1) {
                            filename = filenameMatch[1];
                        }
                    }
                    return response.blob().then(blob => ({ blob, filename }));
                })
                .then(({ blob, filename }) => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    displayMessage(`Download started for ${filename}.`);
                    target.disabled = false; // Re-enable button
                    target.textContent = 'Download Processed Data';
                })
                .catch(error => {
                    console.error(`[Download Processed Button] Error fetching or processing download for ${fileIdentifier}:`, error);
                    displayMessage(`Error preparing download for ${fileIdentifier}: ${error.message}`, true);
                    target.disabled = false; // Re-enable button on error
                    target.textContent = 'Download Processed Data';
                });
        }
    });

    // Listener for template selection changes
    fileStatusesDiv.addEventListener('change', function (event) {
        const target = event.target;
        if (target.classList.contains('template-select')) {
            const templateFilename = target.value;
            const fileIdentifier = target.dataset.fileIdentifier;
            const fileEntryElement = target.closest('.file-entry');

            if (!fileEntryElement) {
                console.error("[Template Select] Could not find parent .file-entry.");
                return;
            }

            if (templateFilename) {
                console.log(`[Template Select] Template '${templateFilename}' selected for file '${fileIdentifier}'`);
                applyTemplate(fileIdentifier, templateFilename, fileEntryElement);
            } else {
                // Optionally, clear mappings if "Select a Template" is chosen
                // This might require re-rendering the mapping table with default/auto-mappings
                // For now, we do nothing, or you could re-trigger auto-mapping if desired.
                console.log(`[Template Select] No template selected for file '${fileIdentifier}'`);
            }
        }
    });

    function populateTemplateDropdown(selectElement, fileIdentifier) {
        console.log("[populateTemplateDropdown] Called with:", selectElement, fileIdentifier);
        if (!selectElement) {
            console.error("[populateTemplateDropdown] selectElement is null or undefined");
            return;
        }
        console.log("[populateTemplateDropdown] Fetching templates from /list_templates");
        fetch('/list_templates')
            .then(response => {
                console.log("[populateTemplateDropdown] Response from /list_templates:", response);
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("[populateTemplateDropdown] Parsed response from /list_templates:", data);
                if (data.error) {
                    console.error("[populateTemplateDropdown] Error fetching templates:", data.error);
                    return;
                }
                // Clear existing options except the first placeholder
                console.log("[populateTemplateDropdown] Clearing existing options");
                while (selectElement.options.length > 1) {
                    selectElement.remove(1);
                }
                console.log("[populateTemplateDropdown] Adding template options:", data);

                // Handle the API response format
                const templates = data.templates || [];

                if (Array.isArray(templates)) {
                    templates.forEach(template => {
                        const option = document.createElement('option');
                        // Use filename as value and template_name as display text
                        option.value = template.filename;
                        option.textContent = template.template_name;
                        selectElement.appendChild(option);
                    });
                    console.log(`[populateTemplateDropdown] Added ${templates.length} template options`);
                } else {
                    console.error("[populateTemplateDropdown] Templates data is not an array:", templates);
                }
                console.log("[populateTemplateDropdown] Template options added");
            })
            .catch(error => {
                console.error('[populateTemplateDropdown] Error fetching templates list:', error);
                displayMessage(`Error fetching templates: ${error.message}`, true);
            });
    }

    function applyTemplate(fileIdentifier, templateFilename, fileEntryElement) {
        console.log(`[applyTemplate] Applying template '${templateFilename}' to file '${fileIdentifier}'`);

        // Get file type from the file entry element
        const fileTypeElement = fileEntryElement.querySelector('.file-type');
        const fileType = fileTypeElement ? fileTypeElement.textContent.trim() : 'unknown';

        if (fileType === 'unknown') {
            console.error(`[applyTemplate] Could not determine file type for ${fileIdentifier}`);
            displayMessage(`Error: Could not determine file type for ${fileIdentifier}`, true);
            return;
        }

        // Show loading state
        const templateSelect = fileEntryElement.querySelector('.template-select');
        if (templateSelect) {
            templateSelect.disabled = true;
        }
        displayMessage(`Applying template "${templateFilename}" to ${fileIdentifier}...`);

        // Use the new apply_template route
        fetch('/apply_template', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                template_filename: templateFilename,
                file_identifier: fileIdentifier,
                file_type: fileType
            })
        })
            .then(response => {
                console.log("[applyTemplate] Response from apply_template:", response);
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.error || `Failed to apply template: ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(result => {
                console.log("[applyTemplate] Template application result:", result);

                if (!result.success) {
                    throw new Error(result.error || 'Template application failed');
                }

                // Update the UI with the new data
                const fileIdentifierSafe = fileIdentifier.replace(/[^a-zA-Z0-9]/g, '_');

                // Update skip_rows input
                const skipRowsInput = fileEntryElement.querySelector(`#skipRows-${fileIdentifierSafe}`);
                if (skipRowsInput && result.skip_rows !== undefined) {
                    skipRowsInput.value = result.skip_rows;
                    console.log(`[applyTemplate] Set skip_rows to: ${result.skip_rows}`);
                }

                // Update headers and mappings table
                const mappingTableContainer = fileEntryElement.querySelector('.mapping-table-container');
                if (mappingTableContainer && result.headers && result.field_mappings) {
                    // Clear existing table and show loading message
                    mappingTableContainer.innerHTML = '<div style="padding: 20px; background-color: #f1f8ff; color: blue; text-align: center;">Updating mapping table with template...</div>';

                    // Rebuild the mapping table with new headers and mappings
                    setTimeout(() => {
                        try {
                            console.log(`[applyTemplate] Rendering new mapping table with ${result.headers.length} headers`);
                            renderMappingTable(mappingTableContainer, fileIdentifier, fileType, result.headers, result.field_mappings, FIELD_DEFINITIONS, 0);
                            console.log(`[applyTemplate] Updated mapping table successfully`);
                        } catch (renderErr) {
                            console.error(`[applyTemplate] Error rendering mapping table:`, renderErr);
                            displayMessage(`Error updating mapping table: ${renderErr.message}`, true);
                        }
                    }, 100);
                }

                // Update file status message
                const statusElement = fileEntryElement.querySelector('.file-status');
                if (statusElement) {
                    statusElement.textContent = result.message;
                    statusElement.className = 'file-status success';
                }

                displayMessage(`Template "${result.template_name}" applied successfully to ${fileIdentifier}.`);
                console.log(`[applyTemplate] Successfully applied template '${templateFilename}' to '${fileIdentifier}'`);
            })
            .catch(error => {
                console.error('Error applying template:', error);
                displayMessage(`Error applying template ${templateFilename}: ${error.message}`, true);
            })
            .finally(() => {
                // Re-enable template select
                if (templateSelect) {
                    templateSelect.disabled = false;
                }
            });
    }

    // After populating template dropdown and adding event listeners, add the skip rows apply button event listener
    function addSkipRowsEventListener(fileIdentifierSafe, fileIdentifier, fileType) {
        console.log(`[addSkipRowsEventListener] Setting up skip rows listener for ${fileIdentifierSafe}`);

        // More aggressive approach - check every 100ms for a total of 2 seconds
        let attempts = 0;
        const maxAttempts = 20;

        function tryAttachListener() {
            console.log(`[addSkipRowsEventListener] Attempt ${attempts + 1} to find button for ${fileIdentifierSafe}`);
            const applySkipRowsBtn = document.querySelector(`#applySkipRows-${fileIdentifierSafe}`);

            if (applySkipRowsBtn) {
                console.log(`[addSkipRowsEventListener] Found button for ${fileIdentifierSafe}`, applySkipRowsBtn);
                console.log(`[addSkipRowsEventListener] Button HTML:`, applySkipRowsBtn.outerHTML);

                // Add a visible indicator that we found the button
                applySkipRowsBtn.style.border = "2px solid green";

                // Add click event in a more direct way
                applySkipRowsBtn.onclick = function (event) {
                    console.log(`[applySkipRows] BUTTON CLICKED for ${fileIdentifierSafe}`, event);

                    const skipRowsInput = document.querySelector(`#skipRows-${fileIdentifierSafe}`);
                    if (skipRowsInput) {
                        const skipRows = parseInt(skipRowsInput.value, 10) || 0;
                        console.log(`[applySkipRows] Applying new skip rows value: ${skipRows} for file: ${fileIdentifier}`);

                        // Call the reprocessFile function with the new skip rows value
                        reprocessFileWithSkipRows(fileIdentifier, fileType, skipRows);
                    } else {
                        console.error(`[applySkipRows] Could not find skip rows input for ${fileIdentifierSafe}`);
                    }
                };

                // Also add the traditional event listener as backup
                applySkipRowsBtn.addEventListener('click', function (event) {
                    console.log(`[applySkipRows] CLICK EVENT LISTENER triggered for ${fileIdentifierSafe}`, event);
                });

                // Add a visual hint to make it obvious the button should be clickable
                applySkipRowsBtn.style.cursor = "pointer";

                console.log(`[addSkipRowsEventListener] Successfully attached event handlers to button for ${fileIdentifierSafe}`);
            } else {
                console.error(`[addSkipRowsEventListener] Button not found for ${fileIdentifierSafe} on attempt ${attempts + 1}`);

                // Try again if we haven't reached max attempts
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(tryAttachListener, 100);
                } else {
                    console.error(`[addSkipRowsEventListener] Gave up looking for button after ${maxAttempts} attempts`);
                }
            }
        }

        // Start the first attempt
        setTimeout(tryAttachListener, 100);
    }

    // Function to reprocess a file with a new skip rows value
    function reprocessFileWithSkipRows(fileIdentifier, fileType, skipRows) {
        console.log(`[reprocessFileWithSkipRows] Starting reprocessing for ${fileIdentifier} with ${skipRows} rows to skip`);

        // Show loading indicator and disable the button
        displayMessage(`Reprocessing ${fileIdentifier} with ${skipRows} rows to skip...`, false);
        const fileIdentifierSafe = fileIdentifier.replace(/[^a-zA-Z0-9]/g, '_');
        const applyBtn = document.querySelector(`#applySkipRows-${fileIdentifierSafe}`);
        if (applyBtn) {
            applyBtn.disabled = true;
            applyBtn.textContent = "Processing..."; // Keep text, btn classes handle style
        }

        console.log(`[reprocessFileWithSkipRows] Sending request to server for ${fileIdentifier}`);

        // Send request to server to reprocess the file
        fetch('/reprocess_file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_identifier: fileIdentifier,
                file_type: fileType,
                skip_rows: skipRows
            })
        })
            .then(response => {
                console.log(`[reprocessFileWithSkipRows] Got response with status: ${response.status}`);

                // Re-enable the button regardless of outcome
                if (applyBtn) {
                    applyBtn.disabled = false;
                    applyBtn.textContent = "Apply Settings"; // Reset to original text
                }

                if (!response.ok) {
                    throw new Error(`Server responded with status: ${response.status}`);
                }
                return response.json();
            })
            .then(result => {
                console.log(`[reprocessFileWithSkipRows] Success:`, result);

                if (result.success) {
                    // Update the relevant mapping table with new headers and data
                    const mappingTableContainer = document.querySelector(`#mapping-table-container-${fileIdentifierSafe}`);

                    if (mappingTableContainer && result.headers && result.headers.length > 0) {
                        console.log(`[reprocessFileWithSkipRows] Updating mapping table with new headers:`, result.headers);

                        // Forcefully clear the existing mapping table and add a temporary indicator
                        mappingTableContainer.innerHTML = '<div style="padding: 20px; background-color: #f1f8ff; color: blue; text-align: center;">Updating mapping table with new headers...</div>';

                        // Update the mapping table with the new data after a visible delay
                        setTimeout(() => {
                            try {
                                // Remove any existing table elements that might have been recreated
                                mappingTableContainer.querySelectorAll('.mapping-table').forEach(table => table.remove());

                                // Directly call renderMappingTable with full context
                                console.log(`[reprocessFileWithSkipRows] Rendering new mapping table for ${fileIdentifier}`);
                                renderMappingTable(mappingTableContainer, fileIdentifier, fileType, result.headers, result.field_mappings, FIELD_DEFINITIONS, 0, true);

                                // Force a UI update by slightly resizing the container
                                setTimeout(() => {
                                    mappingTableContainer.style.padding = '1px';
                                    setTimeout(() => {
                                        mappingTableContainer.style.padding = '0px';
                                        displayMessage(`Successfully reprocessed ${fileIdentifier} with ${skipRows} rows skipped. Headers and mappings updated.`, false);
                                    }, 50);
                                }, 50);
                            } catch (renderErr) {
                                console.error(`[reprocessFileWithSkipRows] Error rendering mapping table:`, renderErr);
                                displayMessage(`Error updating mapping table after reprocessing: ${renderErr.message}`, true);
                            }
                        }, 300); // Increased delay for visibility
                    } else {
                        if (!result.headers || result.headers.length === 0) {
                            displayMessage(`Reprocessing complete but no headers were found with ${skipRows} rows skipped. Try a different value.`, true);
                        } else {
                            displayMessage(`Reprocessing complete but couldn't update the UI. Please refresh the page.`, true);
                        }
                    }
                } else {
                    displayMessage(`Error reprocessing file: ${result.message}`, true);
                }
            })
            .catch(error => {
                console.error(`[reprocessFileWithSkipRows] Error:`, error);
                displayMessage(`Error reprocessing file: ${error.message}`, true);

                // Re-enable the button if it wasn't already done in the response handler
                if (applyBtn) {
                    applyBtn.disabled = false;
                    applyBtn.textContent = "Apply Settings"; // Reset to original text
                }
            });
    }
});