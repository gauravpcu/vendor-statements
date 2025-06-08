document.addEventListener('DOMContentLoaded', function () {
    console.log("[upload.js] DOMContentLoaded fired."); // New Log

    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const fileStatusesDiv = document.getElementById('fileStatuses');

    let uploadStartTime;
    window.extractedDataCache = window.extractedDataCache || {};

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
            } else if (status === 409 && body.error_type === 'NAME_ALREADY_EXISTS_IN_OTHER_FILE'){
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

    window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) {
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
        
        // Clear the container with visual indication
        containerElement.innerHTML = '<div style="padding: 10px; background-color: #e8f4ff; border-radius: 5px; margin-bottom: 10px;">Building mapping table...</div>';
        
        // Short delay to ensure the clearing is visible
        setTimeout(() => {
            // Clear again before adding the new table
            containerElement.innerHTML = '';
            
            const table = document.createElement('table');
            table.className = 'mapping-table';
            const thead = table.createTHead();
            const tbody = table.createTBody();
            const headerRow = thead.insertRow();
            headerRow.innerHTML = '<th>Original Header</th><th>Mapped Field</th><th>Confidence</th><th>Action</th>';

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
            helpButton.className = 'chatbot-help-button';
            helpButton.dataset.originalHeader = header;
            helpButton.dataset.currentMapping = select.value; // Set initial current mapping
            helpButton.dataset.fileIdentifier = fileIdentifier;
            actionCell.appendChild(helpButton);

            select.addEventListener('change', function() {
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

            helpButton.addEventListener('click', function() {
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
                .then(suggestionsArray => { // MODIFIED: Handle direct array of suggestions
                    if (suggestionsArray && suggestionsArray.length > 0) {
                        if (suggestionsArray.length === 1 && suggestionsArray[0].suggested_field === 'N/A') {
                            window.addBotMessage(`No alternative suggestions found for "${originalHeader}". Reason: ${suggestionsArray[0].reason || 'Not specified'}`);
                        } else {
                            let suggestionsMessage = `Suggested alternatives for "${originalHeader}":\\n`;
                            suggestionsArray.forEach(suggestion => {
                                if(suggestion.suggested_field !== 'N/A') { // Only show actual suggestions
                                    suggestionsMessage += `- ${suggestion.suggested_field} (Reason: ${suggestion.reason || 'N/A'})\\n`;
                                }
                            });
                            if (suggestionsMessage === `Suggested alternatives for "${originalHeader}":\\n`) { // No actual suggestions were added
                                window.addBotMessage(`No alternative suggestions found for "${originalHeader}".`);
                            } else {
                                window.addBotMessage(suggestionsMessage);
                            }
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
        
        }, 50); // Close the setTimeout
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
                        if(overallProgressBar) {
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
                    if(overallProgressBar) {
                        overallProgressBar.style.width = '100%';
                        overallProgressBar.textContent = '100%';
                    }
                    if(etaDisplay) etaDisplay.textContent = formatTime(0);

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

                                let skipRowsInputHTML = '';
                                if (fileResult.file_type === 'CSV' || fileResult.file_type === 'XLSX' || fileResult.file_type === 'XLS') {
                                    skipRowsInputHTML = `
                                        <div class="skip-rows-container">
                                            <label for="skipRows-${fileIdentifierSafe}">Rows to Skip (Header):</label>
                                            <input type="number" id="skipRows-${fileIdentifierSafe}" name="skipRows-${fileIdentifierSafe}" value="0" min="0" class="skip-rows-input">
                                            <button type="button" id="applySkipRows-${fileIdentifierSafe}" class="apply-skip-rows-btn">Apply</button>
                                        </div>
                                    `;
                                }
                                
                                // Add a container for template selection
                                const templateSelectionHTML = `
                                    <div class="template-selection-container">
                                        <label for="templateSelect-${fileIdentifierSafe}">Apply Template:</label>
                                        <select id="templateSelect-${fileIdentifierSafe}" class="template-select" data-file-identifier="${fileResult.filename}">
                                            <option value="">-- Select a Template --</option>
                                        </select>
                                    </div>
                                `;

                                fileEntryDiv.innerHTML = `
                                    <div class="file-header">
                                        <h3>${fileResult.filename} (Type: ${fileResult.file_type})</h3>
                                        <p class="status-${fileResult.success ? 'success' : 'error'}">${fileResult.message}</p>
                                    </div>
                                    ${skipRowsInputHTML}
                                    ${templateSelectionHTML} 
                                    <div class="mapping-controls">
                                        <button class="process-file-button" data-file-identifier="${fileResult.filename}" data-file-type="${fileResult.file_type}" data-file-index="${index}" ${!fileResult.success ? 'disabled' : ''}>Process File Data</button>
                                        <button class="save-template-button" data-file-identifier="${fileResult.filename}" ${!fileResult.success ? 'disabled' : ''}>Save as Template</button>
                                        <button class="view-file-button" data-file-identifier="${fileResult.filename}" ${!fileResult.success ? 'disabled' : ''}>View Uploaded File</button>
                                        <button class="download-processed-button" data-file-identifier="${fileResult.filename}" style="display:none;" disabled>Download Processed Data</button>
                                    </div>
                                    <div class="mapping-table-container" id="mapping-table-container-${fileIdentifierSafe}"></div>
                                    <div class="data-preview-area" id="data-preview-${fileIdentifierSafe}"></div>
                                    <div class="validation-summary-area" id="validation-summary-${fileIdentifierSafe}"></div>
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
                                            // Pass FIELD_DEFINITIONS to renderMappingTable
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
                if(overallProgressBar) {
                    overallProgressBar.style.width = '0%';
                    overallProgressBar.textContent = '0%';
                }
                if(etaDisplay) etaDisplay.textContent = 'N/A';
                fileStatusesDiv.innerHTML = '<p class="failure">Upload failed due to a client-side error.</p>';
            }
        });
    }

    // Delegated event listener for dynamically added buttons
    fileStatusesDiv.addEventListener('click', function(event) {
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
            const mappingSelects = fileEntryElement.querySelectorAll('.mapping-table .mapping-select');
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
    fileStatusesDiv.addEventListener('change', function(event) {
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
                data.forEach(template => {
                    const option = document.createElement('option');
                    option.value = template.filename; // Use filename as value
                    option.textContent = template.template_name; // Display template_name
                    selectElement.appendChild(option);
                });
                console.log("[populateTemplateDropdown] Template options added");
            })
            .catch(error => {
                console.error('[populateTemplateDropdown] Error fetching templates list:', error);
                displayMessage(`Error fetching templates: ${error.message}`, true);
            });
    }

    function applyTemplate(fileIdentifier, templateFilename, fileEntryElement) {
        console.log(`[applyTemplate] Applying template '${templateFilename}' to file '${fileIdentifier}'`);
        fetch(`/get_template_details/${encodeURIComponent(templateFilename)}`)
            .then(response => {
                console.log("[applyTemplate] Response from get_template_details:", response);
                if (!response.ok) {
                    throw new Error(`Failed to fetch template details: ${response.statusText}`);
                }
                return response.json();
            })
            .then(templateDetails => {
                console.log("[applyTemplate] Template details received:", templateDetails);
                if (templateDetails.error) {
                    console.error("Error fetching template details:", templateDetails.error);
                    displayMessage(`Error applying template: ${templateDetails.error}`, true);
                    return;
                }

                console.log("[applyTemplate] Template details received:", templateDetails);

                // Apply skip_rows
                const fileIdentifierSafe = fileIdentifier.replace(/[^a-zA-Z0-9]/g, '_');
                const skipRowsInput = fileEntryElement.querySelector(`#skipRows-${fileIdentifierSafe}`);
                if (skipRowsInput && templateDetails.skip_rows !== undefined) {
                    skipRowsInput.value = templateDetails.skip_rows;
                    console.log(`[applyTemplate] Set skip_rows to: ${templateDetails.skip_rows}`);
                } else if (templateDetails.skip_rows !== undefined) {
                    console.warn(`[applyTemplate] skipRowsInput not found for ${fileIdentifierSafe}, but template has skip_rows: ${templateDetails.skip_rows}`);
                }


                // Apply field mappings
                const mappingSelects = fileEntryElement.querySelectorAll('.mapping-table .mapping-select');
                mappingSelects.forEach(select => {
                    const originalHeader = select.dataset.originalHeader;
                    const mapping = templateDetails.field_mappings.find(m => m.original_header === originalHeader);
                    if (mapping) {
                        select.value = mapping.mapped_field;
                        // Trigger change event for consistency if other listeners depend on it
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    } else {
                        select.value = ''; // Or '__IGNORE__' or some default
                         select.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
                displayMessage(`Template "${templateDetails.template_name || templateFilename}" applied to ${fileIdentifier}.`);
                console.log(`[applyTemplate] Finished applying template '${templateFilename}' to '${fileIdentifier}'`);
            })
            .catch(error => {
                console.error('Error applying template:', error);
                displayMessage(`Error applying template ${templateFilename}: ${error.message}`, true);
            });
    }

    // After populating template dropdown and adding event listeners, add the skip rows apply button event listener
    function addSkipRowsEventListener(fileIdentifierSafe, fileIdentifier, fileType) {
        console.log(`[addSkipRowsEventListener] Setting up skip rows listener for ${fileIdentifierSafe}`);
        
        // More aggressive approach - check every 100ms for a total of 2 seconds
        let attempts = 0;
        const maxAttempts = 20;
        
        function tryAttachListener() {
            console.log(`[addSkipRowsEventListener] Attempt ${attempts+1} to find button for ${fileIdentifierSafe}`);
            const applySkipRowsBtn = document.querySelector(`#applySkipRows-${fileIdentifierSafe}`);
            
            if (applySkipRowsBtn) {
                console.log(`[addSkipRowsEventListener] Found button for ${fileIdentifierSafe}`, applySkipRowsBtn);
                console.log(`[addSkipRowsEventListener] Button HTML:`, applySkipRowsBtn.outerHTML);
                
                // Add a visible indicator that we found the button
                applySkipRowsBtn.style.border = "2px solid green";
                
                // Add click event in a more direct way
                applySkipRowsBtn.onclick = function(event) {
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
                applySkipRowsBtn.addEventListener('click', function(event) {
                    console.log(`[applySkipRows] CLICK EVENT LISTENER triggered for ${fileIdentifierSafe}`, event);
                });
                
                // Add a visual hint to make it obvious the button should be clickable
                applySkipRowsBtn.style.cursor = "pointer";
                
                console.log(`[addSkipRowsEventListener] Successfully attached event handlers to button for ${fileIdentifierSafe}`);
            } else {
                console.error(`[addSkipRowsEventListener] Button not found for ${fileIdentifierSafe} on attempt ${attempts+1}`);
                
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
            applyBtn.textContent = "Processing...";
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
                applyBtn.textContent = "Apply";
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
                            renderMappingTable(mappingTableContainer, fileIdentifier, fileType, result.headers, result.field_mappings, FIELD_DEFINITIONS, 0);
                            
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
                applyBtn.textContent = "Apply";
            }
        });
    }
});