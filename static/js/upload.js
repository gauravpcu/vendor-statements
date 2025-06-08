document.addEventListener('DOMContentLoaded', function () {
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
        // ... (implementation as before)
    }

    window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) {
        // ... (implementation as before)
    };

    function renderMappingTable(fileEntryDiv, fileIdentifier, fileType, headers, fieldMappings, fileIndex) {
        // ... (implementation as before - this should include re-attaching listener to .chatbot-help-button or ensuring delegation works)
        // For this fix, we'll assume the delegated listener on fileStatusesDiv correctly handles new .chatbot-help-buttons.
    }

    let advTooltipElement; // Moved to be accessible by the delegated event listener
    function ensureAdvTooltipElement() {
        if (!advTooltipElement) {
            advTooltipElement = document.createElement('div');
            advTooltipElement.id = 'advanced-validation-tooltip';
            advTooltipElement.className = 'tooltip-hidden';
            document.body.appendChild(advTooltipElement);
        }
    }
    ensureAdvTooltipElement();

    function showAdvTooltip(event) { /* ... */ }
    function hideAdvTooltip() { /* ... */ }


    if (uploadForm) {
        uploadForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const files = fileInput.files;
            if (files.length === 0) {
                displayMessage("Please select files to upload.", true);
                return;
            }
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
                            fileEntryDiv.currentChatbotOriginalHeader = null; // Initialize context here

                            const statusP = document.createElement('p');
                            statusP.innerHTML = `<strong>File:</strong> ${result.filename} `;
                            const viewLink = document.createElement('a');
                            viewLink.href = `/view_uploaded_file/${encodeURIComponent(result.filename)}`;
                            viewLink.textContent='View Original'; viewLink.className='view-original-link'; viewLink.target='_blank';
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
                            vendorNameInput.addEventListener('input', function() { applyPrefsButton.disabled = this.value.trim() === ''; });

                            if (["CSV", "XLSX", "XLS"].includes(result.file_type)) {
                                const skipRowsContainer = document.createElement('div');
                                skipRowsContainer.className = 'skip-rows-container';
                                const skipRowsLabel = document.createElement('label'); skipRowsLabel.textContent = 'Skip rows at top:';
                                const skipRowsInputId = `skip-rows-input-${result.filename.replace(/[^a-zA-Z0-9-_]/g, '')}`;
                                skipRowsLabel.htmlFor = skipRowsInputId;
                                const skipRowsInput = document.createElement('input');
                                skipRowsInput.type = 'number'; skipRowsInput.className = 'skip-rows-input';
                                skipRowsInput.id = skipRowsInputId; skipRowsInput.min = '0'; skipRowsInput.value = '0';
                                skipRowsInput.setAttribute('data-file-identifier', result.filename);
                                skipRowsInput.setAttribute('data-file-type', result.file_type);
                                const reloadHeadersButton = document.createElement('button');
                                reloadHeadersButton.textContent = 'Reload Headers'; reloadHeadersButton.className = 'reload-headers-button';
                                skipRowsContainer.appendChild(skipRowsLabel); skipRowsContainer.appendChild(skipRowsInput);
                                skipRowsContainer.appendChild(reloadHeadersButton);
                                fileEntryDiv.appendChild(skipRowsContainer);
                            }

                            const headersDisplayDiv = document.createElement('div');
                            headersDisplayDiv.className = 'headers-display-text-container';
                            fileEntryDiv.appendChild(headersDisplayDiv);
                            if (result.headers && result.headers.length > 0) {
                                headersDisplayDiv.innerHTML = `<div class="headers-display">Headers: ${result.headers.join(', ')}</div>`;
                            } else if (result.headers && result.headers.hasOwnProperty('error')) {
                                headersDisplayDiv.innerHTML = `<div class="headers-error failure">Headers Error: ${result.headers.error}</div>`;
                            } else if (result.message && result.message.includes("No headers were found/extracted")) {
                                headersDisplayDiv.innerHTML = `<p>${result.message}</p>`;
                            }

                            if (result.field_mappings) {
                               renderMappingTable(fileEntryDiv, result.filename, result.file_type, result.headers || [], result.field_mappings, fileIndex);
                            }

                            const processFileButton = document.createElement('button'); /* ... */
                            processFileButton.textContent = 'Process File Data';
                            processFileButton.className = 'process-file-button';
                            processFileButton.setAttribute('data-file-identifier', result.filename);
                            processFileButton.setAttribute('data-file-type', result.file_type);
                            fileEntryDiv.appendChild(processFileButton);

                            const saveTemplateButton = document.createElement('button'); /* ... */
                            saveTemplateButton.textContent = 'Save Mappings as Template';
                            saveTemplateButton.className = 'save-mappings-template-button';
                            saveTemplateButton.setAttribute('data-file-identifier', result.filename);
                            fileEntryDiv.appendChild(saveTemplateButton);

                            fileStatusesDiv.appendChild(fileEntryDiv);
                        });
                    } catch (e) { displayMessage(`Error parsing server response: ${e.toString()}`, true); }
                } else { displayMessage(`Upload failed: Server status ${xhr.status}`, true); }
            });
            xhr.addEventListener('error', function () { displayMessage('Upload network error.', true); });
            xhr.addEventListener('abort', function () { displayMessage('Upload aborted.', true);});
            xhr.open('POST', '/upload', true);
            xhr.send(formData);
            fileStatusesDiv.innerHTML = '<p>Starting upload...</p>';
        });
    }

    fileStatusesDiv.addEventListener('click', function(event) {
        const target = event.target;
        const currentFileEntryDiv = target.closest('.file-entry');
        if (!currentFileEntryDiv) return; // Click was not inside a file-entry

        const fileIdentifier = currentFileEntryDiv.getAttribute('data-filename');

        if (target.classList.contains('reload-headers-button')) {
            // ... (reload headers logic as before) ...
        } else if (target.classList.contains('process-file-button')) {
            // ... (process file data listener logic as before) ...
        } else if (target.classList.contains('save-mappings-template-button')) {
            event.preventDefault();
            window.triggerSaveTemplateWorkflow(fileIdentifier, target);
        } else if (target.classList.contains('btn-remember-yes') || target.classList.contains('btn-remember-no')) {
            // ... (remember mapping prompt listener logic as before) ...
        } else if (target.classList.contains('export-to-excel-button')) {
            // ... (export to excel logic as before) ...
        } else if (target.classList.contains('chatbot-help-button')) {
            const originalHeader = target.getAttribute('data-original-header');
            const currentMappedField = target.getAttribute('data-current-mapped-field');

            if(currentFileEntryDiv) currentFileEntryDiv.currentChatbotOriginalHeader = originalHeader;

            const chatbotPanel = document.getElementById('chatbotPanel');
            if (typeof window.toggleChatbot === 'function' && chatbotPanel && chatbotPanel.classList.contains('hidden')) {
                window.toggleChatbot();
            }
            if (typeof window.addBotMessage === 'function') {
                window.addBotMessage(`Looking for suggestions for header: "${originalHeader}" (currently mapped to: "${currentMappedField}")...`);
                fetch('/chatbot_suggest_mapping', { /* ... fetch suggestions ... */ })
                .then( /* ... display suggestions ... */ );
            }
            // ** THE FIX IS HERE **
            const chatbotInput = document.getElementById('chatbotInput');
            const chatbotSendButton = document.getElementById('chatbotSendButton');
            if(chatbotInput) chatbotInput.disabled = false;
            if(chatbotSendButton) chatbotSendButton.disabled = false;
        }

        // Tooltip handling for advanced validation messages
        if (target.hasAttribute('data-adv-validation-message')) { // If the clicked cell itself has the message
            showAdvTooltip(event);
        } else { // Check if a parent up to the cell might have it (if content inside cell was clicked)
            const parentCellWithAdv = target.closest('td[data-adv-validation-message]');
            if (parentCellWithAdv) {
                 // Create a synthetic event object for showAdvTooltip if needed, or pass parentCellWithAdv
                showAdvTooltip({target: parentCellWithAdv}); // Simulate event on the cell
            }
        }
    });

    // Separate mouseover/mouseout for tooltips on dynamically added cells
    fileStatusesDiv.addEventListener('mouseover', function(event) {
        const target = event.target;
        if (target.hasAttribute('data-adv-validation-message')) {
            showAdvTooltip(event);
        } else {
            const parentCellWithAdv = target.closest('td[data-adv-validation-message]');
            if (parentCellWithAdv) {
                showAdvTooltip({target: parentCellWithAdv});
            }
        }
    });
    fileStatusesDiv.addEventListener('mouseout', function(event) {
        const target = event.target;
         if (target.hasAttribute('data-adv-validation-message') || target.closest('td[data-adv-validation-message]')) {
            hideAdvTooltip();
        }
    });


    // Helper to get current chatbot original header (now accesses property on fileEntryDiv)
    window.getCurrentChatbotOriginalHeader = function() {
        // This needs a way to know *which* fileEntryDiv's context is active.
        // This global approach for currentChatbotOriginalHeader is problematic if multiple file entries exist.
        // For now, it will rely on the last `chatbot-help-button` click setting it on its `fileEntryDiv`.
        // A more robust solution would pass context or use a class to mark active fileEntryDiv.
        // This function cannot reliably get the correct fileEntryDiv.currentChatbotOriginalHeader globally.
        // The context should be managed more locally or passed explicitly.
        // The `setCurrentChatbotOriginalHeader` below is better.
        console.warn("getCurrentChatbotOriginalHeader is problematic globally. Context should be managed locally.");
        return null;
    };
    window.setCurrentChatbotOriginalHeader = function(header, fileEntryElement) { // Called by chatbot-help-button
        if(fileEntryElement) fileEntryElement.currentChatbotOriginalHeader = header;
    };
    window.clearCurrentChatbotOriginalHeader = function(fileEntryElement) { // Needs context
        if(fileEntryElement) fileEntryElement.currentChatbotOriginalHeader = null;
    };


    function formatTime(seconds) { /* ... */ }
});
if (typeof window.addBotMessage !== 'function') { /* ... default addBotMessage ... */ }
