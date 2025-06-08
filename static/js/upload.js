document.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const fileStatusesDiv = document.getElementById('fileStatuses');

    let uploadStartTime;

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
        const actionMessage = overwrite ? `Overwriting template "${templateName}"...` : `Attempting to save template "${templateName}"...`;
        displayMessage(actionMessage);
        fetch('/save_template', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ template_name: templateName, field_mappings: mappings, skip_rows: skipRows, overwrite: overwrite }),
        })
        .then(response => response.json().then(data => ({status: response.status, data, responseOk: response.ok })))
        .then(({status, data, responseOk}) => {
            if (responseOk && data.status === 'success') {
                displayMessage(`Template "${data.template_name || templateName}" ${data.message.includes("overwritten") ? "overwritten" : "saved"} successfully as ${data.filename}.`);
            } else if (responseOk && data.status === 'no_conflict_proceed_to_save') {
                executeSaveTemplateRequest(templateName, mappings, skipRows, true, fileIdentifierForContext);
            } else if (status === 409 && data.error_type) {
                if (data.error_type === 'NAME_ALREADY_EXISTS_IN_OTHER_FILE') {
                    displayMessage(`${data.message}`, true);
                } else if (data.error_type === 'FILENAME_CLASH') {
                    let confirmMsg = `A template file named '${data.filename}' already exists.`;
                    if (data.existing_template_name && data.existing_template_name !== "N/A" && data.existing_template_name !== templateName) {
                        confirmMsg += ` (It currently stores a template named: '${data.existing_template_name}').`;
                    }
                    confirmMsg += "\nDo you want to overwrite it?";
                    if (window.confirm(confirmMsg)) {
                        executeSaveTemplateRequest(templateName, mappings, skipRows, true, fileIdentifierForContext);
                    } else { displayMessage("Save operation cancelled by user."); }
                } else { displayMessage(`Conflict: ${data.message || data.error || 'Unknown conflict'}`, true); }
            } else { displayMessage(`Error saving template: ${data.message || data.error || 'Unknown server error.'}`, true); }
        })
        .catch(error => displayMessage(`Network error saving template: ${error.toString()}`, true));
    }

    window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) {
        const templateNamePrompt = window.prompt("Enter a name for this mapping template:", `Template for ${fileIdentifier}`);
        if (templateNamePrompt === null) { displayMessage("Template saving cancelled."); return; }
        const templateName = templateNamePrompt.trim();
        if (templateName === "") { displayMessage("Template name cannot be empty.", true); return; }
        const currentMappings = [];
        const fileEntryElement = contextElement.closest('.file-entry');
        const tableBody = fileEntryElement ? fileEntryElement.querySelector('.mappings-table tbody') : null;
        let skipRowsValue = 0;
        if (fileEntryElement) {
            const skipRowsInput = fileEntryElement.querySelector('.skip-rows-input');
            if (skipRowsInput) { // Check if skipRowsInput exists (it won't for PDF)
                skipRowsValue = parseInt(skipRowsInput.value, 10) || 0;
                if (skipRowsValue < 0) skipRowsValue = 0;
            }
        }
        if (tableBody) {
            tableBody.querySelectorAll('tr').forEach(row => {
                const originalHeader = row.cells[0].textContent;
                const sel = row.cells[1].querySelector('select.mapped-field-select');
                if (sel && sel.value !== "N/A") currentMappings.push({ original_header: originalHeader, mapped_field: sel.value });
            });
        } else { displayMessage("Error: Could not find mapping table.", true); return; }
        if (currentMappings.length === 0) { displayMessage("No actual mappings to save.", true); return; }
        executeSaveTemplateRequest(templateName, currentMappings, skipRowsValue, false, fileIdentifier);
    };

    function renderMappingTable(fileEntryDiv, fileIdentifier, fileType, headers, fieldMappings, fileIndex) {
        const existingTableContainer = fileEntryDiv.querySelector('.mappings-table-container');
        if (existingTableContainer) existingTableContainer.remove();
        const existingTemplateDropdownContainer = fileEntryDiv.querySelector('.template-dropdown-container');
        if (existingTemplateDropdownContainer) existingTemplateDropdownContainer.remove();

        if (!headers || headers.length === 0) {
            const noHeadersMsg = document.createElement('p');
            // Use fieldMappings (which would be an error object from backend if headers failed) for message
            noHeadersMsg.textContent = (fieldMappings && fieldMappings.error) ? fieldMappings.error : (fieldMappings && fieldMappings.message ? fieldMappings.message : "No headers available to map for this file or skip setting.");
            if (fieldMappings && fieldMappings.error) noHeadersMsg.classList.add('failure');

            const refNode = fileEntryDiv.querySelector('.skip-rows-container') || fileEntryDiv.querySelector('.vendor-name-container') || fileEntryDiv.querySelector('.statusP');
            if(refNode) refNode.parentNode.insertBefore(noHeadersMsg, refNode.nextSibling);
            else fileEntryDiv.appendChild(noHeadersMsg);
            return;
        }

        const templateDropdownContainer = document.createElement('div');
        templateDropdownContainer.className = 'template-dropdown-container';
        const templateSelectLabel = document.createElement('label');
        templateSelectLabel.textContent = 'Apply Mapping Template: ';
        const templateSelectId = `apply-template-dropdown-${fileIdentifier.replace(/[^a-zA-Z0-9-_]/g, '')}-${Date.now()}`;
        templateSelectLabel.htmlFor = templateSelectId;
        const templateSelect = document.createElement('select');
        templateSelect.className = 'apply-template-dropdown'; templateSelect.id = templateSelectId;
        const defaultOption = document.createElement('option'); defaultOption.value = "";
        defaultOption.textContent = "-- Select a Template --"; templateSelect.appendChild(defaultOption);
        templateDropdownContainer.appendChild(templateSelectLabel); templateDropdownContainer.appendChild(templateSelect);

        const mappingsTableContainer = document.createElement('div');
        mappingsTableContainer.className = 'mappings-table-container';
        const mappingsTable = document.createElement('table'); mappingsTable.className = 'mappings-table';
        const caption = mappingsTable.createCaption(); caption.textContent = 'Field Mappings';
        const thead = mappingsTable.createTHead(); const headerRow = thead.insertRow();
        const tableHeaders = ["Original Header", "Mapped Field", "Confidence", "Method", "Help"];
        tableHeaders.forEach(txt => {const th=document.createElement('th');th.textContent=txt;headerRow.appendChild(th);});
        const tbody = mappingsTable.createTBody();

        fieldMappings.forEach(function(mapping, mappingIndex) { // Ensure fieldMappings is an array
            const row = tbody.insertRow();
            const cellOriginal = row.insertCell(); cellOriginal.textContent = mapping.original_header;
            const cellMapped = row.insertCell();
            const selectElement = document.createElement('select');
            selectElement.className = 'mapped-field-select';
            selectElement.setAttribute('data-original-header', mapping.original_header);
            selectElement.id = `map-select-${fileIndex}-${mappingIndex}-${Date.now()}`;
            const unmappedOption = document.createElement('option'); unmappedOption.value = "N/A";
            unmappedOption.textContent = "-- Unmapped --"; selectElement.appendChild(unmappedOption);
            if (typeof FIELD_DEFINITIONS === 'object' && FIELD_DEFINITIONS !== null) {
                for (const fn in FIELD_DEFINITIONS) if (FIELD_DEFINITIONS.hasOwnProperty(fn)) {
                    const opt = document.createElement('option'); opt.value = fn; opt.textContent = fn; selectElement.appendChild(opt);
                }
            }
            let cMapField = mapping.mapped_field;
            if (cMapField && cMapField.startsWith("Unknown: ")) cMapField = "N/A";
            selectElement.value = (cMapField && selectElement.querySelector(`option[value="${cMapField}"]`)) ? cMapField : "N/A";
            cellMapped.appendChild(selectElement);
            const infoIcon = document.createElement('span'); infoIcon.className = 'field-tooltip-trigger';
            infoIcon.innerHTML = '&#9432;'; infoIcon.setAttribute('data-field-name', selectElement.value);
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
            const cellConfidence = row.insertCell(); const score = parseFloat(mapping.confidence_score);
            cellConfidence.textContent = `${score.toFixed(0)}%`;
            let confClass = ''; if (score >= 90) confClass = 'confidence-high'; else if (score >= 80) confClass = 'confidence-medium'; else confClass = 'confidence-low';
            cellConfidence.classList.add(confClass); if (score < 80 || mapping.error) row.classList.add('row-needs-review');
            const cellMethod = row.insertCell(); cellMethod.textContent = mapping.method || 'N/A';
            const cellChatHelp = row.insertCell(); const chatBtn = document.createElement('button');
            chatBtn.className = 'chatbot-help-button'; chatBtn.textContent = 'Suggest';
            chatBtn.setAttribute('data-original-header', mapping.original_header);
            chatBtn.setAttribute('data-current-mapped-field', selectElement.value);
            selectElement.addEventListener('change', function() { chatBtn.setAttribute('data-current-mapped-field', this.value);}); // No need to re-add infoIcon listener here
            cellChatHelp.appendChild(chatBtn);
        });
        mappingsTableContainer.appendChild(mappingsTable);

        const skipRowsContainerEl = fileEntryDiv.querySelector('.skip-rows-container');
        const vendorContainerEl = fileEntryDiv.querySelector('.vendor-name-container');
        const headersDisplayContainerEl = fileEntryDiv.querySelector('.headers-display-text-container');

        if (skipRowsContainerEl) { // If CSV/Excel with skip rows UI
            skipRowsContainerEl.after(templateDropdownContainer);
        } else if (vendorContainerEl) { // If PDF or other without skip rows, after vendor
            vendorContainerEl.after(templateDropdownContainer);
        } else if (headersDisplayContainerEl) { // After headers text if it exists
             headersDisplayContainerEl.after(templateDropdownContainer);
        } else { // Fallback to end of fileEntryDiv
            fileEntryDiv.appendChild(templateDropdownContainer);
        }
        templateDropdownContainer.after(mappingsTableContainer); // Table always after template dropdown

        fetch('/list_templates').then(r => r.json()).then(data => {
             if (data.templates && data.templates.length > 0) {
                data.templates.forEach(template => {
                    const option = document.createElement('option'); option.value = template.file_id; option.textContent = template.display_name; templateSelect.appendChild(option);
                });
            } else { templateSelect.disabled = true; defaultOption.textContent = "-- No Templates Available --"; }
        }).catch(e => { console.error('Error fetching templates:', e); templateSelect.disabled = true; defaultOption.textContent = "-- Error Loading Templates --";});

        templateSelect.addEventListener('change', function() {
            const selectedTemplateFileId = this.value;
            const currentFileEntryDiv = this.closest('.file-entry');
            const fileIdent = currentFileEntryDiv.getAttribute('data-filename');
            const currentFileType = currentFileEntryDiv.querySelector('.skip-rows-input')?.getAttribute('data-file-type') ||
                                 (fileIdent.toLowerCase().endsWith('.pdf') ? 'PDF' : 'unknown');

            if (!selectedTemplateFileId) return;
            displayMessage(`Applying template: ${this.options[this.selectedIndex].text}...`);

            fetch(`/get_template/${selectedTemplateFileId}`)
            .then(response => { if (!response.ok) throw new Error(`HTTP error! ${response.status}`); return response.json(); })
            .then(templateData => {
                if (templateData.error) { displayMessage(`Error loading template: ${templateData.error}`, true); this.value = ""; return; }

                const templateSkipRows = templateData.skip_rows !== undefined ? parseInt(templateData.skip_rows, 10) : null;
                const skipRowsInput = currentFileEntryDiv.querySelector('.skip-rows-input');

                if (skipRowsInput && templateSkipRows !== null && skipRowsInput.value !== String(templateSkipRows)) {
                    skipRowsInput.value = templateSkipRows;
                    displayMessage(`Skip rows set to ${templateSkipRows} from template. Reloading headers...`);

                    fetch('/re_extract_headers', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ file_identifier: fileIdent, file_type: currentFileType, skip_rows: templateSkipRows })
                    })
                    .then(reExtractResponse => reExtractResponse.json())
                    .then(reExtractData => {
                        if (reExtractData.success) {
                            displayMessage(reExtractData.message || `Headers reloaded. Now applying template mappings.`);
                            const headersDispDiv = currentFileEntryDiv.querySelector('.headers-display-text-container');
                            if(headersDispDiv) headersDispDiv.innerHTML = (reExtractData.headers && reExtractData.headers.length > 0) ? `<div class="headers-display">Headers: ${reExtractData.headers.join(', ')}</div>` : '<p>No headers found after reload.</p>';

                            // Pass fileIndex to renderMappingTable
                            const allFileEntries = Array.from(fileStatusesDiv.children);
                            const reloadedFileIndex = allFileEntries.indexOf(currentFileEntryDiv);

                            renderMappingTable(currentFileEntryDiv, fileIdent, currentFileType, reExtractData.headers, reExtractData.field_mappings, reloadedFileIndex);

                            const newMappingRows = currentFileEntryDiv.querySelectorAll('.mappings-table tbody tr');
                            newMappingRows.forEach(row => {
                                const originalHeader = row.cells[0].textContent.trim();
                                const mappedFieldSelect = row.cells[1].querySelector('select.mapped-field-select');
                                const foundMappingInTemplate = templateData.field_mappings.find(m => m.original_header === originalHeader);
                                if (foundMappingInTemplate) mappedFieldSelect.value = foundMappingInTemplate.mapped_field;
                                else mappedFieldSelect.value = "N/A";
                                mappedFieldSelect.dispatchEvent(new Event('change'));
                            });
                            displayMessage(`Template "${templateData.template_name}" applied with skip rows ${templateSkipRows}.`);
                        } else { displayMessage(`Failed to reload headers: ${reExtractData.error}`, true); }
                    })
                    .catch(err => displayMessage(`Error reloading headers: ${err.message}`, true));
                } else {
                    const mappingRows = currentFileEntryDiv.querySelectorAll('.mappings-table tbody tr');
                    templateData.field_mappings.forEach(templateMapItem => {
                        mappingRows.forEach(row => {
                            if (row.cells[0].textContent.trim() === templateMapItem.original_header) {
                                const select = row.cells[1].querySelector('select.mapped-field-select');
                                select.value = templateMapItem.mapped_field;
                                select.dispatchEvent(new Event('change'));
                            }
                        });
                    });
                    displayMessage(`Template "${templateData.template_name}" applied.`);
                }
                this.value = "";
            })
            .catch(error => { displayMessage(`Failed to apply template: ${error.message}`, true); this.value = ""; });
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', function (event) { /* ... */ });
        const xhr = new XMLHttpRequest();
        xhr.upload.addEventListener('progress', function (event) { /* ... */ });
        xhr.addEventListener('load', function () { /* ... main XHR load handler ... */ });
        xhr.addEventListener('error', function () { /* ... */ });
        xhr.addEventListener('abort', function () { /* ... */ });
        // This part was outside the if(uploadForm) block, moved it in.
        // xhr.open('POST', '/upload', true);
        // xhr.send(formData);
        // fileStatusesDiv.innerHTML = '<p>Starting upload...</p>';
    }

    // Moved from inside submit event listener to be accessible by other parts if needed,
    // but primarily used by the XHR upload.
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return "N/A";
        if (seconds === 0) return "0s";
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        let timeString = '';
        if (h > 0) timeString += `${h}h `;
        if (m > 0) timeString += `${m}m `;
        if (s >= 0) timeString += `${s}s`;
        return timeString.trim();
    }

    // Delegated listener for Reload Headers button (and other file-entry specific buttons)
    fileStatusesDiv.addEventListener('click', function(event) {
        const target = event.target;
        if (target.classList.contains('reload-headers-button')) {
            // ... (reload headers logic as implemented in previous step, using renderMappingTable)
        }
        if (target.classList.contains('process-file-button')) {
            // ... (process file data listener logic)
        }
        if (target.classList.contains('btn-remember-yes') || target.classList.contains('btn-remember-no')) {
            // ... (remember mapping prompt listener logic)
        }
        // ... (chatbot help button listener if delegated here)
    });

});
if (typeof window.addBotMessage !== 'function') { /* ... default addBotMessage ... */ }
