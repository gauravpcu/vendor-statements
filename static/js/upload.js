document.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const fileStatusesDiv = document.getElementById('fileStatuses');

    let uploadStartTime;

    window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) {
        const templateName = window.prompt("Enter a name for this mapping template:", `Template for ${fileIdentifier}`);
        if (templateName === null || templateName.trim() === "") {
            if(typeof window.addBotMessage === 'function') window.addBotMessage("Template saving cancelled.");
            return;
        }
        const sanitizedTemplateName = templateName.trim();
        const currentMappings = [];
        const fileEntryElement = contextElement.closest('.file-entry');
        const tableBody = fileEntryElement ? fileEntryElement.querySelector('.mappings-table tbody') : null;
        if (tableBody) {
            tableBody.querySelectorAll('tr').forEach(row => {
                const originalHeader = row.cells[0].textContent;
                const selectElement = row.cells[1].querySelector('select.mapped-field-select');
                const mappedField = selectElement ? selectElement.value : 'N/A';
                if (mappedField !== "N/A") {
                    currentMappings.push({ original_header: originalHeader, mapped_field: mappedField });
                }
            });
        } else {
            alert("Error: Could not gather mappings. Table not found."); return;
        }
        if (currentMappings.length === 0) {
            alert("No actual field mappings to save for this template."); return;
        }
        if(typeof window.addBotMessage === 'function') window.addBotMessage(`Saving template "${sanitizedTemplateName}"...`);
        fetch('/save_template', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ template_name: sanitizedTemplateName, field_mappings: currentMappings }),
        })
        .then(response => response.json())
        .then(saveResult => {
            if (saveResult.status === 'success') {
                if(typeof window.addBotMessage === 'function') window.addBotMessage(`Template "${saveResult.template_name}" saved.`);
                alert(`Template "${saveResult.template_name}" saved successfully!`);
            } else {
                if(typeof window.addBotMessage === 'function') window.addBotMessage(`Error saving template: ${saveResult.error || 'Unknown error'}`);
                alert(`Error saving template: ${saveResult.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            if(typeof window.addBotMessage === 'function') window.addBotMessage(`Network error: ${error.toString()}`);
            alert(`Error saving template: ${error.toString()}`);
        });
    };

    if (uploadForm) {
        uploadForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const files = fileInput.files;
            if (files.length === 0) { /* ... */ return; }
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
                            fileEntryDiv.className = 'file-entry';
                            fileEntryDiv.setAttribute('data-filename', result.filename);
                            fileEntryDiv.mappingChangeCount = 0;
                            fileEntryDiv.promptedToSaveTemplate = false;

                            const statusP = document.createElement('p'); /* ... */
                            statusP.innerHTML = `<strong>File:</strong> ${result.filename} `;
                            const viewLink = document.createElement('a'); /* ... */
                            viewLink.href = `/view_uploaded_file/${encodeURIComponent(result.filename)}`;
                            viewLink.textContent='View Original'; viewLink.className='view-original-link'; viewLink.target='_blank';
                            statusP.appendChild(document.createTextNode(' (')); statusP.appendChild(viewLink); statusP.appendChild(document.createTextNode(')'));
                            statusP.appendChild(document.createElement('br'));
                            let typeDisplay = result.file_type; /* ... */
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

                            const applyPrefsButton = document.createElement('button'); // New button
                            applyPrefsButton.textContent = 'Apply Vendor Preferences';
                            applyPrefsButton.className = 'apply-vendor-prefs-button';
                            applyPrefsButton.setAttribute('data-file-identifier', result.filename);
                            applyPrefsButton.disabled = true;
                            vendorNameContainer.appendChild(applyPrefsButton);
                            fileEntryDiv.appendChild(vendorNameContainer);
                            vendorNameInput.addEventListener('input', function() {
                                applyPrefsButton.disabled = this.value.trim() === '';
                            });

                            if (result.headers && result.headers.length > 0) { /* ... */ }
                            else if (result.headers && result.headers.hasOwnProperty('error')) { /* ... */ }

                            if (result.field_mappings && result.field_mappings.length > 0) {
                                const templateDropdownContainer = document.createElement('div'); /* ... */
                                fileEntryDiv.appendChild(templateDropdownContainer);
                                fetch('/list_templates').then(r=>r.json()).then(d=>{/* ... */});
                                const mappingsTable = document.createElement('table'); /* ... */
                                fileEntryDiv.appendChild(mappingsTable);
                                const tbody = mappingsTable.createTBody();
                                result.field_mappings.forEach(function(mapping, mappingIndex) {
                                    const row = tbody.insertRow();
                                    const cellOriginal = row.insertCell(); cellOriginal.textContent = mapping.original_header;
                                    const cellMapped = row.insertCell();
                                    const selectElement = document.createElement('select'); /* ... */
                                    selectElement.className = 'mapped-field-select';
                                    selectElement.setAttribute('data-original-header', mapping.original_header);
                                    selectElement.id = `map-select-${fileIndex}-${mappingIndex}`;
                                    // ... (populate selectElement options) ...
                                    cellMapped.appendChild(selectElement);
                                    const infoIcon = document.createElement('span'); /* ... */
                                    cellMapped.appendChild(infoIcon);
                                    selectElement.addEventListener('change', function() { /* ... existing change listener ... */
                                        // Prompt to save individual mapping
                                        const cFileEntry = this.closest('.file-entry');
                                        const origHeader = this.getAttribute('data-original-header');
                                        const newMapField = this.value;
                                        const vendorNameInputEl = cFileEntry.querySelector('.vendor-name-input');
                                        const vendorNameVal = vendorNameInputEl ? vendorNameInputEl.value.trim() : '';
                                        let existingPrompt = this.parentNode.querySelector('.remember-mapping-prompt');
                                        if (existingPrompt) existingPrompt.remove();
                                        if (vendorNameVal && newMapField !== "N/A") {
                                            const promptDiv = document.createElement('div');
                                            promptDiv.className = 'remember-mapping-prompt';
                                            promptDiv.innerHTML = `Remember for <strong>${vendorNameVal}</strong>: "<em>${origHeader}</em>" &rarr; "<em>${newMapField}</em>"? `;
                                            const yesBtn = document.createElement('button'); /* ... */
                                            yesBtn.className = 'btn-remember-yes'; yesBtn.textContent = 'Yes';
                                            yesBtn.setAttribute('data-original-header', origHeader);
                                            yesBtn.setAttribute('data-mapped-field', newMapField);
                                            yesBtn.setAttribute('data-vendor-name', vendorNameVal);
                                            const noBtn = document.createElement('button'); /* ... */
                                            noBtn.className = 'btn-remember-no'; noBtn.textContent = 'No';
                                            promptDiv.appendChild(yesBtn); promptDiv.appendChild(noBtn);
                                            this.parentNode.appendChild(promptDiv);
                                        }
                                    });
                                    if (mapping.error) { /* ... */ }
                                    const cellConfidence = row.insertCell(); /* ... */
                                    const cellMethod = row.insertCell(); cellMethod.textContent = mapping.method || 'N/A';
                                    const cellChatHelp = row.insertCell(); /* ... chatHelpButton ... */
                                });

                                applyPrefsButton.addEventListener('click', function() {
                                    const vendorName = vendorNameInput.value.trim();
                                    const fileIdentifier = this.getAttribute('data-file-identifier');
                                    const currentFileEntryDiv = this.closest('.file-entry');
                                    const currentMappings = [];
                                    const tableBody = currentFileEntryDiv.querySelector('.mappings-table tbody');
                                    if (tableBody) {
                                        tableBody.querySelectorAll('tr').forEach(row => {
                                            currentMappings.push({
                                                original_header: row.cells[0].textContent,
                                                mapped_field: row.cells[1].querySelector('select.mapped-field-select').value,
                                                confidence_score: parseFloat(row.cells[2].textContent.replace('%','')) || 0,
                                                method: row.cells[3].textContent
                                            });
                                        });
                                    }
                                    if (typeof window.addBotMessage === 'function') addBotMessage(`Applying preferences for ${vendorName}...`);
                                    fetch('/apply_learned_preferences', {
                                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ vendor_name: vendorName, current_mappings: currentMappings, file_identifier: fileIdentifier })
                                    })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.error) {
                                            if (typeof window.addBotMessage === 'function') addBotMessage(`Error: ${data.error}`);
                                        } else {
                                            const updatedMappings = data.updated_mappings;
                                            const mappingRows = currentFileEntryDiv.querySelectorAll('.mappings-table tbody tr');
                                            mappingRows.forEach(row => {
                                                const originalHeader = row.cells[0].textContent.trim();
                                                const selectElement = row.cells[1].querySelector('select.mapped-field-select');
                                                const confidenceCell = row.cells[2];
                                                const methodCell = row.cells[3];
                                                const newMapping = updatedMappings.find(m => m.original_header === originalHeader);
                                                if (newMapping && selectElement) {
                                                    selectElement.value = newMapping.mapped_field;
                                                    selectElement.dispatchEvent(new Event('change'));
                                                    const score = parseFloat(newMapping.confidence_score);
                                                    confidenceCell.textContent = `${score.toFixed(0)}%`;
                                                    let confClass = 'confidence-low';
                                                    if (score >= 90) confClass = 'confidence-high';
                                                    else if (score >= 80) confClass = 'confidence-medium';
                                                    confidenceCell.className = ''; confidenceCell.classList.add(confClass);
                                                    if (score < 80 || newMapping.error) row.classList.add('row-needs-review');
                                                    else row.classList.remove('row-needs-review');
                                                    methodCell.textContent = newMapping.method || 'N/A';
                                                }
                                            });
                                            if (typeof window.addBotMessage === 'function') addBotMessage(`Preferences for ${data.vendor_name} applied.`);
                                        }
                                    })
                                    .catch(error => {
                                        if (typeof window.addBotMessage === 'function') addBotMessage(`Error: ${error.toString()}`);
                                    });
                                });

                                const processFileButton = document.createElement('button'); /* ... */
                                fileEntryDiv.appendChild(processFileButton);
                                processFileButton.addEventListener('click', function() { /* ... */ });
                                const saveTemplateButton = document.createElement('button'); /* ... */
                                fileEntryDiv.appendChild(saveTemplateButton);
                                saveTemplateButton.addEventListener('click', function(event) { /* ... */ });
                                fileEntryDiv.querySelectorAll('.chatbot-help-button').forEach(button => { /* ... */ });
                                fileEntryDiv.addEventListener('click', function(event) { /* ... remember prompt listener ... */ });
                            }

                            let tooltipElement = document.getElementById('field-description-tooltip'); /* ... */
                            fileEntryDiv.querySelectorAll('.field-tooltip-trigger').forEach(icon => { /* ... */ });
                            window.getCurrentChatbotOriginalHeader = function() { return fileEntryDiv.currentChatbotOriginalHeader; };
                            window.setCurrentChatbotOriginalHeader = function(header) { fileEntryDiv.currentChatbotOriginalHeader = header; };
                            window.clearCurrentChatbotOriginalHeader = function() { fileEntryDiv.currentChatbotOriginalHeader = null; };
                            fileStatusesDiv.appendChild(fileEntryDiv);
                        });
                    } catch (e) { /* ... */ }
                } else { /* ... */ }
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
