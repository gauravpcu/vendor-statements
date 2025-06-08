document.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const fileStatusesDiv = document.getElementById('fileStatuses');

    let uploadStartTime;

    // Centralized function for adding messages to the chatbot, if chatbot.js isn't loaded or window.addBotMessage isn't set
    function displayMessage(message, isError = false) {
        if (typeof window.addBotMessage === 'function') {
            // Prepend error type for actual errors
            const prefix = isError ? "Error: " : "";
            window.addBotMessage(prefix + message);
        } else {
            // Fallback to alert if addBotMessage isn't available (e.g. if chatbot.js didn't load)
            console.warn("window.addBotMessage not found, using alert.");
            alert(message);
        }
    }

    // Refactored function to handle the full save template workflow, including conflict resolution
    function executeSaveTemplateRequest(templateName, mappings, overwrite = false, fileIdentifierForContext = null) {
        const actionMessage = overwrite ? `Overwriting template "${templateName}"...` : `Attempting to save template "${templateName}"...`;
        displayMessage(actionMessage);

        fetch('/save_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                template_name: templateName,
                field_mappings: mappings,
                overwrite: overwrite
            }),
        })
        .then(response => {
            const status = response.status;
            return response.json().then(data => ({ status, data, responseOk: response.ok }));
        })
        .then(({ status, data, responseOk }) => {
            if (responseOk) { // Covers 200, 201
                if (data.status === 'success') {
                    displayMessage(`Template "${data.template_name || templateName}" ${data.message.includes("overwritten") ? "overwritten" : "saved"} successfully as ${data.filename}.`);
                } else if (data.status === 'no_conflict_proceed_to_save') {
                    // This means the filename is available, proceed to save by calling with overwrite: true
                    executeSaveTemplateRequest(templateName, mappings, true, fileIdentifierForContext);
                } else { // Should ideally not happen if backend adheres to contract
                    displayMessage(`Template save: ${data.message || 'Completed with no specific status.'}`, !data.status || data.status !== 'success');
                }
            } else { // Handle 4xx, 5xx responses
                const errorMessage = data.message || data.error || 'Unknown error saving template.';
                if (status === 409) { // Conflict
                    if (data.error_type === 'NAME_ALREADY_EXISTS_IN_OTHER_FILE') {
                        displayMessage(`Error: ${errorMessage}`, true);
                    } else if (data.error_type === 'FILENAME_CLASH') {
                        let confirmMsg = `A template file that would be named '${data.filename}' already exists.`;
                        if (data.existing_template_name && data.existing_template_name !== "N/A" && data.existing_template_name !== templateName) {
                            confirmMsg += ` (It currently stores a template named: '${data.existing_template_name}').`;
                        }
                        confirmMsg += "\nDo you want to overwrite it?";
                        if (window.confirm(confirmMsg)) {
                            executeSaveTemplateRequest(templateName, mappings, true, fileIdentifierForContext);
                        } else {
                            displayMessage("Save operation cancelled by user.");
                        }
                    } else { // Other 409 or unexpected 409 content
                         displayMessage(`Conflict: ${errorMessage}`, true);
                    }
                } else { // Other non-OK statuses (400, 500, etc.)
                    displayMessage(`Error saving template: ${errorMessage}`, true);
                }
            }
        })
        .catch(error => {
            console.error('Error during save template request:', error);
            displayMessage(`Network or system error saving template: ${error.toString()}`, true);
        });
    }

    window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) {
        const templateNamePrompt = window.prompt("Enter a name for this mapping template:", `Template for ${fileIdentifier}`);
        if (templateNamePrompt === null) { // User cancelled prompt
            displayMessage("Template saving cancelled.");
            return;
        }
        const templateName = templateNamePrompt.trim();
        if (templateName === "") {
            displayMessage("Template name cannot be empty. Saving cancelled.", true);
            return;
        }

        const currentMappings = [];
        const fileEntryElement = contextElement.closest('.file-entry');
        const tableBody = fileEntryElement ? fileEntryElement.querySelector('.mappings-table tbody') : null;

        if (tableBody) {
            tableBody.querySelectorAll('tr').forEach(row => {
                const originalHeader = row.cells[0].textContent;
                const selectElement = row.cells[1].querySelector('select.mapped-field-select');
                const mappedField = selectElement ? selectElement.value : 'N/A';
                if (mappedField !== "N/A") { // Only include actual mappings
                    currentMappings.push({ original_header: originalHeader, mapped_field: mappedField });
                }
            });
        } else {
            displayMessage("Error: Could not gather mappings. Table not found.", true); return;
        }
        if (currentMappings.length === 0) {
            displayMessage("No actual field mappings to save for this template.", true); return;
        }

        executeSaveTemplateRequest(templateName, currentMappings, false, fileIdentifier);
    };

    if (uploadForm) {
        uploadForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const files = fileInput.files;
            if (files.length === 0) {
                displayMessage("Please select files to upload.", true);
                return;
            }
            // ... (rest of submit handler as before, using `displayMessage` for user feedback)
            const formData = new FormData();
            for (let i = 0; i < files.length; i++) formData.append('files[]', files[i]);
            const xhr = new XMLHttpRequest();
            uploadStartTime = Date.now();
            xhr.upload.addEventListener('progress', function (event) { /* ... */ });

            xhr.addEventListener('load', function () {
                overallProgressBar.style.width = '100%';overallProgressBar.textContent='100%';etaDisplay.textContent=formatTime(0);
                fileStatusesDiv.innerHTML = '';
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const results = JSON.parse(xhr.responseText);
                        results.forEach(function (result, fileIndex) {
                            const fileEntryDiv = document.createElement('div');
                            // ... (setup fileEntryDiv, statusP, vendorNameContainer, applyPrefsButton etc. as before)
                            // ...
                            // Ensure all user-facing messages from this part also use displayMessage or addBotMessage
                            // For example, when applying templates or processing files.
                            // Example for applying template:
                            // if (typeof window.addBotMessage === 'function') window.addBotMessage(...); else alert(...);
                            // should become:
                            // displayMessage(...);
                            // ...
                            // (The full integration of displayMessage throughout this large function is implied here for brevity)

                            // --- Start of structure from previous step ---
                            fileEntryDiv.className = 'file-entry';
                            fileEntryDiv.setAttribute('data-filename', result.filename);
                            fileEntryDiv.mappingChangeCount = 0;
                            fileEntryDiv.promptedToSaveTemplate = false;

                            const statusP = document.createElement('p');
                            statusP.innerHTML = `<strong>File:</strong> ${result.filename} `;
                            const viewLink = document.createElement('a');
                            viewLink.href = `/view_uploaded_file/${encodeURIComponent(result.filename)}`;
                            viewLink.textContent = 'View Original'; viewLink.className = 'view-original-link'; viewLink.target = '_blank';
                            statusP.appendChild(document.createTextNode(' (')); statusP.appendChild(viewLink); statusP.appendChild(document.createTextNode(')'));
                            statusP.appendChild(document.createElement('br'));
                            let typeDisplay = result.file_type;
                            if (result.file_type && result.file_type.startsWith("error_")) typeDisplay = `Error (${result.file_type.split('_')[1]})`;
                            else if (!result.success && !(FIELD_DEFINITIONS[result.file_type] && FIELD_DEFINITIONS[result.file_type].expected_type)) typeDisplay = `Unsupported (${result.file_type || 'unknown'})`;
                            const messageSpan = document.createElement('span');
                            messageSpan.textContent = `${result.message} (Type: ${typeDisplay})`;
                            messageSpan.className = result.success ? 'success-inline' : 'failure-inline';
                            statusP.appendChild(messageSpan); fileEntryDiv.appendChild(statusP);

                            const vendorNameContainer = document.createElement('div');
                            vendorNameContainer.className = 'vendor-name-container';
                            const vendorNameLabel = document.createElement('label');
                            vendorNameLabel.textContent = 'Vendor Name (Optional): ';
                            const vendorNameInputId = `vendor-name-input-${result.filename.replace(/[^a-zA-Z0-9-_]/g, '')}`;
                            vendorNameLabel.htmlFor = vendorNameInputId;
                            const vendorNameInput = document.createElement('input');
                            vendorNameInput.type = 'text'; vendorNameInput.className = 'vendor-name-input';
                            vendorNameInput.id = vendorNameInputId; vendorNameInput.placeholder = 'Enter vendor name';
                            vendorNameInput.setAttribute('data-file-identifier', result.filename);
                            vendorNameContainer.appendChild(vendorNameLabel); vendorNameContainer.appendChild(vendorNameInput);

                            const applyPrefsButton = document.createElement('button');
                            applyPrefsButton.textContent = 'Apply Vendor Preferences';
                            applyPrefsButton.className = 'apply-vendor-prefs-button';
                            applyPrefsButton.setAttribute('data-file-identifier', result.filename);
                            applyPrefsButton.disabled = true;
                            vendorNameContainer.appendChild(applyPrefsButton);
                            fileEntryDiv.appendChild(vendorNameContainer);
                            vendorNameInput.addEventListener('input', function() {
                                applyPrefsButton.disabled = this.value.trim() === '';
                            });

                            if (result.headers && result.headers.length > 0) { /* ... headers display ... */ }
                            else if (result.headers && result.headers.hasOwnProperty('error')) { /* ... headers error ... */ }

                            if (result.field_mappings && result.field_mappings.length > 0) {
                                const templateDropdownContainer = document.createElement('div');
                                templateDropdownContainer.className = 'template-dropdown-container';
                                const templateSelectLabel = document.createElement('label');
                                templateSelectLabel.textContent = 'Apply Mapping Template: ';
                                const templateSelectId = `apply-template-dropdown-${result.filename.replace(/[^a-zA-Z0-9-_]/g, '')}`;
                                templateSelectLabel.htmlFor = templateSelectId;
                                const templateSelect = document.createElement('select');
                                templateSelect.className = 'apply-template-dropdown';
                                templateSelect.id = templateSelectId;
                                const defaultOption = document.createElement('option'); defaultOption.value = "";
                                defaultOption.textContent = "-- Select a Template --"; templateSelect.appendChild(defaultOption);
                                templateDropdownContainer.appendChild(templateSelectLabel); templateDropdownContainer.appendChild(templateSelect);
                                fileEntryDiv.appendChild(templateDropdownContainer);

                                fetch('/list_templates').then(r => r.json()).then(data => {
                                    if (data.templates && data.templates.length > 0) {
                                        data.templates.forEach(template => {
                                            const option = document.createElement('option'); option.value = template.file_id; option.textContent = template.display_name; templateSelect.appendChild(option);
                                        });
                                    } else { templateSelect.disabled = true; defaultOption.textContent = "-- No Templates Available --"; }
                                }).catch(error => { console.error('Error fetching templates:', error); templateSelect.disabled = true; defaultOption.textContent = "-- Error Loading Templates --";});

                                const mappingsTable = document.createElement('table'); mappingsTable.className = 'mappings-table';
                                const caption = mappingsTable.createCaption(); caption.textContent = 'Field Mappings';
                                const thead = mappingsTable.createTHead(); const headerRow = thead.insertRow();
                                const tableHeaders = ["Original Header", "Mapped Field", "Confidence", "Method", "Help"];
                                tableHeaders.forEach(txt => {const th=document.createElement('th'); th.textContent=txt; headerRow.appendChild(th);});
                                const tbody = mappingsTable.createTBody();
                                result.field_mappings.forEach(function(mapping, mappingIndex) {
                                    const row = tbody.insertRow();
                                    const cellOriginal = row.insertCell(); cellOriginal.textContent = mapping.original_header;
                                    const cellMapped = row.insertCell();
                                    const selectElement = document.createElement('select');
                                    selectElement.className = 'mapped-field-select';
                                    selectElement.setAttribute('data-original-header', mapping.original_header);
                                    selectElement.id = `map-select-${fileIndex}-${mappingIndex}`;
                                    const unmappedOption = document.createElement('option');
                                    unmappedOption.value = "N/A"; unmappedOption.textContent = "-- Unmapped --";
                                    selectElement.appendChild(unmappedOption);
                                    if (typeof FIELD_DEFINITIONS === 'object' && FIELD_DEFINITIONS !== null) {
                                        for (const fn in FIELD_DEFINITIONS) if (FIELD_DEFINITIONS.hasOwnProperty(fn)) {
                                            const opt = document.createElement('option'); opt.value = fn; opt.textContent = fn; selectElement.appendChild(opt);
                                        }
                                    }
                                    let cMapField = mapping.mapped_field;
                                    if (cMapField && cMapField.startsWith("Unknown: ")) cMapField = "N/A";
                                    selectElement.value = (cMapField && selectElement.querySelector(`option[value="${cMapField}"]`)) ? cMapField : "N/A";
                                    cellMapped.appendChild(selectElement);
                                    const infoIcon = document.createElement('span');
                                    infoIcon.className = 'field-tooltip-trigger'; infoIcon.innerHTML = '&#9432;';
                                    infoIcon.setAttribute('data-field-name', selectElement.value);
                                    cellMapped.appendChild(infoIcon);

                                    selectElement.addEventListener('change', function() {
                                        infoIcon.setAttribute('data-field-name', this.value);
                                        const helpBtn = row.querySelector('.chatbot-help-button');
                                        if (helpBtn) helpBtn.setAttribute('data-current-mapped-field', this.value);
                                        const cFileEntry = this.closest('.file-entry');
                                        const origHeader = this.getAttribute('data-original-header');
                                        const newMapField = this.value;
                                        if (cFileEntry) {
                                            cFileEntry.mappingChangeCount = (cFileEntry.mappingChangeCount || 0) + 1;
                                            if (cFileEntry.mappingChangeCount >= 3 && !cFileEntry.promptedToSaveTemplate) {
                                                if (typeof window.promptToSaveTemplate === 'function') {
                                                    window.promptToSaveTemplate(cFileEntry.getAttribute('data-filename'));
                                                    cFileEntry.promptedToSaveTemplate = true;
                                                }
                                            }
                                            const vendorNameInputEl = cFileEntry.querySelector('.vendor-name-input');
                                            const vendorNameVal = vendorNameInputEl ? vendorNameInputEl.value.trim() : '';
                                            let existingPrompt = this.parentNode.querySelector('.remember-mapping-prompt');
                                            if (existingPrompt) existingPrompt.remove();
                                            if (vendorNameVal && newMapField !== "N/A") {
                                                const promptDiv = document.createElement('div');
                                                promptDiv.className = 'remember-mapping-prompt';
                                                promptDiv.innerHTML = `Remember for <strong>${vendorNameVal}</strong>: "<em>${origHeader}</em>" &rarr; "<em>${newMapField}</em>"? `;
                                                const yesBtn = document.createElement('button');
                                                yesBtn.className = 'btn-remember-yes'; yesBtn.textContent = 'Yes';
                                                yesBtn.setAttribute('data-original-header', origHeader);
                                                yesBtn.setAttribute('data-mapped-field', newMapField);
                                                yesBtn.setAttribute('data-vendor-name', vendorNameVal);
                                                const noBtn = document.createElement('button');
                                                noBtn.className = 'btn-remember-no'; noBtn.textContent = 'No';
                                                promptDiv.appendChild(yesBtn); promptDiv.appendChild(noBtn);
                                                this.parentNode.appendChild(promptDiv);
                                            }
                                        }
                                    });
                                    if (mapping.error) {const errSpan = document.createElement('span'); errSpan.className='failure-inline'; errSpan.style.display='block'; errSpan.textContent=`Error: ${mapping.error}`; cellMapped.appendChild(errSpan);}
                                    const cellConfidence = row.insertCell();
                                    const score = parseFloat(mapping.confidence_score);
                                    cellConfidence.textContent = `${score.toFixed(0)}%`;
                                    let confidenceClass = '';
                                    if (score >= 90) confidenceClass = 'confidence-high';
                                    else if (score >= 80) confidenceClass = 'confidence-medium';
                                    else confidenceClass = 'confidence-low';
                                    cellConfidence.classList.add(confidenceClass);
                                    if (score < 80 || mapping.error) row.classList.add('row-needs-review');
                                    const cellMethod = row.insertCell(); cellMethod.textContent = mapping.method || 'N/A';
                                    const cellChatHelp = row.insertCell();
                                    const chatHelpButton = document.createElement('button');
                                    chatHelpButton.className = 'chatbot-help-button'; chatHelpButton.textContent = 'Suggest';
                                    chatHelpButton.setAttribute('data-original-header', mapping.original_header);
                                    chatHelpButton.setAttribute('data-current-mapped-field', selectElement.value);
                                    selectElement.addEventListener('change', function() { chatHelpButton.setAttribute('data-current-mapped-field', this.value);});
                                    cellChatHelp.appendChild(chatHelpButton);
                                });
                                fileEntryDiv.appendChild(mappingsTable);
                                templateSelect.addEventListener('change', function() { /* ... apply template logic ... */ });
                                applyPrefsButton.addEventListener('click', function() { /* ... apply vendor prefs logic ... */ });
                                const processFileButton = document.createElement('button'); /* ... setup and listener ... */
                                fileEntryDiv.appendChild(processFileButton);
                                const saveTemplateButton = document.createElement('button'); /* ... setup ... */
                                fileEntryDiv.appendChild(saveTemplateButton);
                                saveTemplateButton.addEventListener('click', function(event) { event.preventDefault(); window.triggerSaveTemplateWorkflow(this.getAttribute('data-file-identifier'), this); });
                                fileEntryDiv.querySelectorAll('.chatbot-help-button').forEach(button => { /* ... chatbot help listener ... */ });
                                fileEntryDiv.addEventListener('click', function(event) { /* ... remember prompt listener ... */ });
                            }
                            let tooltipElement = document.getElementById('field-description-tooltip'); /* ... */
                            fileEntryDiv.querySelectorAll('.field-tooltip-trigger').forEach(icon => { /* ... tooltip listeners ... */ });
                            window.getCurrentChatbotOriginalHeader = function() { return fileEntryDiv.currentChatbotOriginalHeader; };
                            window.setCurrentChatbotOriginalHeader = function(header) { fileEntryDiv.currentChatbotOriginalHeader = header; };
                            window.clearCurrentChatbotOriginalHeader = function() { fileEntryDiv.currentChatbotOriginalHeader = null; };
                            fileStatusesDiv.appendChild(fileEntryDiv);
                        });
                    } catch (e) { /* ... error handling ... */ }
                } else { /* ... error handling ... */ }
            });
            xhr.addEventListener('error', function () { /* ... */ });
            xhr.addEventListener('abort', function () { /* ... */ });
            xhr.open('POST', '/upload', true);
            xhr.send(formData);
            fileStatusesDiv.innerHTML = '<p>Starting upload...</p>';
        });
    }
    function formatTime(seconds) { /* ... */ }
});
if (typeof window.addBotMessage !== 'function') { /* ... */ }
