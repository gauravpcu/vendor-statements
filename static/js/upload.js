document.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const fileStatusesDiv = document.getElementById('fileStatuses');

    let uploadStartTime;

    // Function to trigger the save template workflow
    // contextElement is the element from which to find the .file-entry parent (e.g., the button itself)
    window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) {
        const templateName = window.prompt("Enter a name for this mapping template:", `Template for ${fileIdentifier}`);
        if (templateName === null || templateName.trim() === "") {
            if(typeof window.addBotMessage === 'function') window.addBotMessage("Template saving cancelled.");
            return;
        }

        const sanitizedTemplateName = templateName.trim();
        const currentMappings = [];
        const fileEntryElement = contextElement.closest('.file-entry'); // Find parent file-entry
        const tableBody = fileEntryElement ? fileEntryElement.querySelector('.mappings-table tbody') : null;

        if (tableBody) {
            tableBody.querySelectorAll('tr').forEach(row => {
                const originalHeader = row.cells[0].textContent;
                const selectElement = row.cells[1].querySelector('select.mapped-field-select');
                const mappedField = selectElement ? selectElement.value : 'N/A';
                if (mappedField !== "N/A") {
                    currentMappings.push({
                        original_header: originalHeader,
                        mapped_field: mappedField
                    });
                }
            });
        }

        if (currentMappings.length === 0) {
            alert("No actual field mappings to save for this template.");
            return;
        }

        console.log("Save Template Triggered!");
        console.log("Template Name:", sanitizedTemplateName);
        console.log("Gathered Mappings for Template:", currentMappings);

        if(typeof window.addBotMessage === 'function') window.addBotMessage(`Saving template "${sanitizedTemplateName}"...`);

        fetch('/save_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                template_name: sanitizedTemplateName,
                field_mappings: currentMappings
            }),
        })
        .then(response => response.json())
        .then(saveResult => {
            if (saveResult.status === 'success') {
                if(typeof window.addBotMessage === 'function') window.addBotMessage(`Template "${saveResult.template_name}" saved as ${saveResult.filename}.`);
                alert(`Template "${saveResult.template_name}" saved successfully!`);
            } else {
                if(typeof window.addBotMessage === 'function') window.addBotMessage(`Error saving template: ${saveResult.error || 'Unknown error'}`);
                alert(`Error saving template: ${saveResult.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error saving template:', error);
            if(typeof window.addBotMessage === 'function') window.addBotMessage(`Network or system error saving template: ${error.toString()}`);
            alert(`Error saving template: ${error.toString()}`);
        });
    };


    if (uploadForm) {
        uploadForm.addEventListener('submit', function (event) {
            event.preventDefault();

            const files = fileInput.files;
            if (files.length === 0) {
                fileStatusesDiv.innerHTML = '<p class="failure">Please select files to upload.</p>';
                return;
            }

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files[]', files[i]);
            }

            const xhr = new XMLHttpRequest();
            uploadStartTime = Date.now();

            xhr.upload.addEventListener('progress', function (event) {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    overallProgressBar.style.width = percentComplete.toFixed(2) + '%';
                    overallProgressBar.textContent = percentComplete.toFixed(2) + '%';

                    const elapsedTime = (Date.now() - uploadStartTime) / 1000;
                    if (percentComplete > 0 && elapsedTime > 0) {
                        const totalTime = (elapsedTime / percentComplete) * 100;
                        const remainingTime = totalTime - elapsedTime;
                        etaDisplay.textContent = formatTime(remainingTime);
                    } else {
                        etaDisplay.textContent = 'Calculating...';
                    }
                }
            });

            xhr.addEventListener('load', function () {
                overallProgressBar.style.width = '100%';
                overallProgressBar.textContent = '100%';
                etaDisplay.textContent = formatTime(0);

                fileStatusesDiv.innerHTML = '';
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const results = JSON.parse(xhr.responseText);
                        results.forEach(function (result, fileIndex) {
                            const fileEntryDiv = document.createElement('div');
                            fileEntryDiv.className = 'file-entry';
                            fileEntryDiv.setAttribute('data-filename', result.filename);

                            // Initialize mapping change counter and prompt flag for this file entry
                            fileEntryDiv.mappingChangeCount = 0;
                            fileEntryDiv.promptedToSaveTemplate = false;


                            const statusP = document.createElement('p');
                            statusP.innerHTML = `<strong>File:</strong> ${result.filename} `;

                            const viewLink = document.createElement('a');
                            viewLink.href = `/view_uploaded_file/${encodeURIComponent(result.filename)}`;
                            viewLink.textContent = 'View Original';
                            viewLink.className = 'view-original-link';
                            viewLink.target = '_blank';
                            statusP.appendChild(document.createTextNode(' ('));
                            statusP.appendChild(viewLink);
                            statusP.appendChild(document.createTextNode(')'));

                            statusP.appendChild(document.createElement('br'));
                            let typeDisplay = result.file_type;
                            if (result.file_type && result.file_type.startsWith("error_")) {
                                typeDisplay = `Error (${result.file_type.split('_')[1]})`;
                            } else if (!result.success && !(FIELD_DEFINITIONS[result.file_type] && FIELD_DEFINITIONS[result.file_type].expected_type)) {
                                typeDisplay = `Unsupported (${result.file_type || 'unknown'})`;
                            }
                            const messageSpan = document.createElement('span');
                            messageSpan.textContent = `${result.message} (Type: ${typeDisplay})`;
                            messageSpan.className = result.success ? 'success-inline' : 'failure-inline';
                            statusP.appendChild(messageSpan);

                            fileEntryDiv.appendChild(statusP);

                            if (result.headers && result.headers.length > 0) {
                                const headersDiv = document.createElement('div');
                                headersDiv.className = 'headers-display';
                                headersDiv.textContent = 'Headers: ' + result.headers.join(', ');
                                fileEntryDiv.appendChild(headersDiv);
                            } else if (result.headers && result.headers.hasOwnProperty('error')) {
                                const headersErrorDiv = document.createElement('div');
                                headersErrorDiv.className = 'headers-error failure';
                                headersErrorDiv.textContent = 'Headers Error: ' + result.headers.error;
                                fileEntryDiv.appendChild(headersErrorDiv);
                            }

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
                                const defaultOption = document.createElement('option');
                                defaultOption.value = "";
                                defaultOption.textContent = "-- Select a Template --";
                                templateSelect.appendChild(defaultOption);
                                templateDropdownContainer.appendChild(templateSelectLabel);
                                templateDropdownContainer.appendChild(templateSelect);
                                fileEntryDiv.appendChild(templateDropdownContainer);

                                fetch('/list_templates')
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.templates && data.templates.length > 0) {
                                            data.templates.forEach(template => {
                                                const option = document.createElement('option');
                                                option.value = template.file_id;
                                                option.textContent = template.display_name;
                                                templateSelect.appendChild(option);
                                            });
                                        } else {
                                            templateSelect.disabled = true;
                                            defaultOption.textContent = "-- No Templates Available --";
                                        }
                                    })
                                    .catch(error => {
                                        console.error('Error fetching templates:', error);
                                        templateSelect.disabled = true;
                                        defaultOption.textContent = "-- Error Loading Templates --";
                                    });

                                const mappingsTable = document.createElement('table');
                                mappingsTable.className = 'mappings-table';
                                const caption = mappingsTable.createCaption();
                                caption.textContent = 'Field Mappings';
                                const thead = mappingsTable.createTHead();
                                const headerRow = thead.insertRow();
                                const tableHeaders = ["Original Header", "Mapped Field", "Confidence", "Method", "Help"];
                                tableHeaders.forEach(function(headerText) {
                                    const th = document.createElement('th');
                                    th.textContent = headerText;
                                    headerRow.appendChild(th);
                                });
                                const tbody = mappingsTable.createTBody();
                                result.field_mappings.forEach(function(mapping, mappingIndex) {
                                    const row = tbody.insertRow();
                                    const cellOriginal = row.insertCell();
                                    cellOriginal.textContent = mapping.original_header;

                                    const cellMapped = row.insertCell();
                                    const selectElement = document.createElement('select');
                                    selectElement.className = 'mapped-field-select';
                                    selectElement.setAttribute('data-original-header', mapping.original_header);
                                    selectElement.id = `map-select-${fileIndex}-${mappingIndex}`;
                                    const unmappedOption = document.createElement('option');
                                    unmappedOption.value = "N/A";
                                    unmappedOption.textContent = "-- Unmapped --";
                                    selectElement.appendChild(unmappedOption);
                                    if (typeof FIELD_DEFINITIONS === 'object' && FIELD_DEFINITIONS !== null) {
                                        for (const fieldName in FIELD_DEFINITIONS) {
                                            if (FIELD_DEFINITIONS.hasOwnProperty(fieldName)) {
                                                const option = document.createElement('option');
                                                option.value = fieldName;
                                                option.textContent = fieldName;
                                                selectElement.appendChild(option);
                                            }
                                        }
                                    } else {
                                        console.error("FIELD_DEFINITIONS is not available or not an object:", FIELD_DEFINITIONS);
                                    }
                                    let currentMappedField = mapping.mapped_field;
                                    if (currentMappedField && currentMappedField.startsWith("Unknown: ")) {
                                        currentMappedField = "N/A";
                                    }
                                    if (currentMappedField && selectElement.querySelector(`option[value="${currentMappedField}"]`)) {
                                        selectElement.value = currentMappedField;
                                    } else {
                                        selectElement.value = "N/A";
                                    }
                                    cellMapped.appendChild(selectElement);
                                    const infoIcon = document.createElement('span');
                                    infoIcon.className = 'field-tooltip-trigger';
                                    infoIcon.innerHTML = '&#9432;';
                                    infoIcon.setAttribute('data-field-name', selectElement.value);
                                    cellMapped.appendChild(infoIcon);

                                    selectElement.addEventListener('change', function() {
                                        infoIcon.setAttribute('data-field-name', this.value);
                                        const helpButton = row.querySelector('.chatbot-help-button');
                                        if (helpButton) {
                                            helpButton.setAttribute('data-current-mapped-field', this.value);
                                        }
                                        // Track mapping changes
                                        const currentFileEntry = this.closest('.file-entry');
                                        if (currentFileEntry) {
                                            currentFileEntry.mappingChangeCount = (currentFileEntry.mappingChangeCount || 0) + 1;
                                            // console.log(`File ${currentFileEntry.getAttribute('data-filename')} changes: ${currentFileEntry.mappingChangeCount}`);
                                            if (currentFileEntry.mappingChangeCount >= 3 && !currentFileEntry.promptedToSaveTemplate) {
                                                if (typeof window.promptToSaveTemplate === 'function') {
                                                    window.promptToSaveTemplate(currentFileEntry.getAttribute('data-filename'));
                                                    currentFileEntry.promptedToSaveTemplate = true;
                                                }
                                            }
                                        }
                                    });
                                    if (mapping.error) {
                                        const errorSpan = document.createElement('span');
                                        errorSpan.className = 'failure-inline';
                                        errorSpan.style.display = 'block';
                                        errorSpan.textContent = `Error: ${mapping.error}`;
                                        cellMapped.appendChild(errorSpan);
                                    }

                                    const cellConfidence = row.insertCell();
                                    const score = parseFloat(mapping.confidence_score);
                                    cellConfidence.textContent = `${score.toFixed(0)}%`;
                                    let confidenceClass = '';
                                    if (score >= 90) {
                                        confidenceClass = 'confidence-high';
                                    } else if (score >= 80) {
                                        confidenceClass = 'confidence-medium';
                                    } else {
                                        confidenceClass = 'confidence-low';
                                    }
                                    cellConfidence.classList.add(confidenceClass);
                                    if (score < 80 || mapping.error) {
                                        row.classList.add('row-needs-review');
                                    }
                                    const cellMethod = row.insertCell();
                                    cellMethod.textContent = mapping.method || 'N/A';
                                    const cellChatHelp = row.insertCell();
                                    const chatHelpButton = document.createElement('button');
                                    chatHelpButton.className = 'chatbot-help-button';
                                    chatHelpButton.textContent = 'Suggest';
                                    chatHelpButton.setAttribute('data-original-header', mapping.original_header);
                                    chatHelpButton.setAttribute('data-current-mapped-field', selectElement.value);
                                    selectElement.addEventListener('change', function() {
                                        chatHelpButton.setAttribute('data-current-mapped-field', this.value);
                                    });
                                    cellChatHelp.appendChild(chatHelpButton);
                                });
                                fileEntryDiv.appendChild(mappingsTable);

                                templateSelect.addEventListener('change', function() {
                                    const selectedTemplateFileId = this.value;
                                    const currentFileEntryDiv = this.closest('.file-entry');
                                    if (!selectedTemplateFileId) return;
                                    if (typeof window.addBotMessage === 'function') {
                                        window.addBotMessage(`Fetching template: ${this.options[this.selectedIndex].text}...`);
                                    }
                                    fetch(`/get_template/${selectedTemplateFileId}`)
                                        .then(response => {
                                            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                                            return response.json();
                                        })
                                        .then(templateData => {
                                            if (templateData.error) {
                                                if (typeof window.addBotMessage === 'function') window.addBotMessage(`Error loading template: ${templateData.error}`);
                                                this.value = ""; return;
                                            }
                                            const templateMappings = templateData.field_mappings;
                                            const mappingRows = currentFileEntryDiv.querySelectorAll('.mappings-table tbody tr');
                                            mappingRows.forEach(row => {
                                                const originalHeaderCell = row.cells[0];
                                                const mappedFieldSelect = row.cells[1].querySelector('select.mapped-field-select');
                                                const originalHeader = originalHeaderCell.textContent.trim();
                                                const foundMapping = templateMappings.find(m => m.original_header === originalHeader);
                                                if (foundMapping) mappedFieldSelect.value = foundMapping.mapped_field;
                                                else mappedFieldSelect.value = "N/A";
                                                mappedFieldSelect.dispatchEvent(new Event('change'));
                                            });
                                            if (typeof window.addBotMessage === 'function') window.addBotMessage(`Template "${templateData.template_name}" applied.`);
                                            this.value = "";
                                        })
                                        .catch(error => {
                                            console.error('Error applying template:', error);
                                            if (typeof window.addBotMessage === 'function') window.addBotMessage(`Failed to apply template: ${error.message}`);
                                            this.value = "";
                                        });
                                });

                                const processFileButton = document.createElement('button');
                                processFileButton.textContent = 'Process File Data';
                                processFileButton.className = 'process-file-button';
                                processFileButton.setAttribute('data-file-identifier', result.filename);
                                processFileButton.setAttribute('data-file-type', result.file_type);
                                fileEntryDiv.appendChild(processFileButton);
                                processFileButton.addEventListener('click', function() {
                                    const fileIdentifier = this.getAttribute('data-file-identifier');
                                    const fileType = this.getAttribute('data-file-type');
                                    const currentMappings = [];
                                    const tableBody = this.closest('.file-entry').querySelector('.mappings-table tbody');
                                    if (tableBody) {
                                        tableBody.querySelectorAll('tr').forEach(row => {
                                            const originalHeader = row.cells[0].textContent;
                                            const selectElement = row.cells[1].querySelector('select.mapped-field-select');
                                            const mappedField = selectElement ? selectElement.value : 'N/A';
                                            const confidenceText = row.cells[2].textContent;
                                            const confidenceScore = parseFloat(confidenceText.replace('%','')) || 0;
                                            currentMappings.push({
                                                original_header: originalHeader,
                                                mapped_field: mappedField,
                                                confidence_score: confidenceScore
                                            });
                                        });
                                    }
                                    console.log("Finalized Mappings for processing:", currentMappings);
                                    if(typeof window.addBotMessage === 'function') addBotMessage(`Processing file: ${fileIdentifier}...`);
                                    fetch('/process_file_data', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                            file_identifier: fileIdentifier,
                                            file_type: fileType,
                                            finalized_mappings: currentMappings
                                        })
                                    })
                                    .then(response => response.json())
                                    .then(data => {
                                        console.log('Process File Response:', data);
                                        const fileEntryDiv = this.closest('.file-entry');
                                        let dataDisplayContainer = fileEntryDiv.querySelector('.extracted-data-container');
                                        if (!dataDisplayContainer) {
                                            dataDisplayContainer = document.createElement('div');
                                            dataDisplayContainer.className = 'extracted-data-container';
                                            fileEntryDiv.appendChild(dataDisplayContainer);
                                        }
                                        dataDisplayContainer.innerHTML = '';
                                        if (data.error) {
                                            if(typeof window.addBotMessage === 'function') addBotMessage(`Error processing file ${fileIdentifier}: ${data.error}`);
                                            const errorP = document.createElement('p');
                                            errorP.className = 'failure';
                                            errorP.textContent = `Error extracting data: ${data.error}`;
                                            dataDisplayContainer.appendChild(errorP);
                                        } else if (data.data && data.data.length > 0) {
                                            if(typeof window.addBotMessage === 'function') addBotMessage(`Successfully processed ${fileIdentifier}. ${data.message || ''} Displaying ${data.data.length} extracted records.`);
                                            const table = document.createElement('table');
                                            table.className = 'extracted-data-table';
                                            const thead = table.createTHead();
                                            const headerRow = thead.insertRow();
                                            const headers = Object.keys(data.data[0]);
                                            headers.forEach(headerText => {
                                                const th = document.createElement('th');
                                                th.textContent = headerText;
                                                headerRow.appendChild(th);
                                            });
                                            const tbody = table.createTBody();
                                            data.data.forEach(record => {
                                                const row = tbody.insertRow();
                                                headers.forEach(mapped_field_name => {
                                                    const cell = row.insertCell();
                                                    const cellValue = record[mapped_field_name];
                                                    cell.textContent = cellValue !== undefined && cellValue !== null ? cellValue : '';
                                                    if (FIELD_DEFINITIONS && FIELD_DEFINITIONS[mapped_field_name] && cellValue !== null && cellValue !== "") {
                                                        const expectedType = FIELD_DEFINITIONS[mapped_field_name].expected_type;
                                                        let isValid = true;
                                                        const valueStr = String(cellValue).trim();
                                                        switch (expectedType) {
                                                            case 'date':
                                                                if (!/^\d{5,}$/.test(valueStr) && isNaN(new Date(valueStr).getTime())) isValid = false;
                                                                break;
                                                            case 'number': case 'currency':
                                                                const numericValue = valueStr.replace(/[\$\€\£\¥,\s]/g, '');
                                                                if (isNaN(parseFloat(numericValue)) || !isFinite(parseFloat(numericValue))) isValid = false;
                                                                break;
                                                            case 'percentage':
                                                                const percValue = valueStr.replace(/[%,\s]/g, '');
                                                                if (isNaN(parseFloat(percValue)) || !isFinite(parseFloat(percValue))) isValid = false;
                                                                break;
                                                            case 'string': break;
                                                            default: break;
                                                        }
                                                        if (!isValid) cell.classList.add('data-validation-error');
                                                    }
                                                });
                                            });
                                            dataDisplayContainer.appendChild(table);
                                            dataDisplayContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                                        } else {
                                            if(typeof window.addBotMessage === 'function') addBotMessage(`No data extracted for ${fileIdentifier}.`);
                                            const noDataP = document.createElement('p');
                                            noDataP.textContent = 'No data was extracted or the file is empty.';
                                            dataDisplayContainer.appendChild(noDataP);
                                        }
                                    })
                                    .catch(error => {
                                        console.error('Error processing file:', error);
                                        if(typeof window.addBotMessage === 'function') addBotMessage(`Error processing file ${fileIdentifier}: ${error.toString()}`);
                                        alert(`Error processing file: ${error.toString()}`);
                                    });
                                });

                                const saveTemplateButton = document.createElement('button');
                                saveTemplateButton.textContent = 'Save Mappings as Template';
                                saveTemplateButton.className = 'save-mappings-template-button';
                                saveTemplateButton.setAttribute('data-file-identifier', result.filename);
                                fileEntryDiv.appendChild(saveTemplateButton);
                                saveTemplateButton.addEventListener('click', function(event) {
                                    event.preventDefault();
                                    const fileIdentifier = this.getAttribute('data-file-identifier');
                                    // Call the refactored function, passing `this` (the button) as contextElement
                                    window.triggerSaveTemplateWorkflow(fileIdentifier, this);
                                });

                                let currentChatbotOriginalHeader = null;
                                fileEntryDiv.querySelectorAll('.chatbot-help-button').forEach(button => {
                                    button.addEventListener('click', function() {
                                        const originalHeader = this.getAttribute('data-original-header');
                                        const currentMappedField = this.getAttribute('data-current-mapped-field');
                                        currentChatbotOriginalHeader = originalHeader;
                                        const chatbotPanel = document.getElementById('chatbotPanel');
                                        if (typeof window.toggleChatbot === 'function' && chatbotPanel && chatbotPanel.classList.contains('hidden')) {
                                            window.toggleChatbot();
                                        }
                                        if (typeof window.addBotMessage === 'function') {
                                            window.addBotMessage(`Looking for suggestions for header: "${originalHeader}" (currently mapped to: "${currentMappedField}")...`);
                                            fetch('/chatbot_suggest_mapping', {
                                                method: 'POST',
                                                headers: { 'Content-Type': 'application/json' },
                                                body: JSON.stringify({
                                                    original_header: originalHeader,
                                                    current_mapped_field: currentMappedField
                                                }),
                                            })
                                            .then(response => {
                                                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                                                return response.json();
                                            })
                                            .then(suggestions => {
                                                if (suggestions && suggestions.length > 0 && suggestions[0].suggested_field !== 'N/A') {
                                                    const suggestionsHtmlContainer = document.createElement('div');
                                                    suggestionsHtmlContainer.className = 'suggestions-list';
                                                    suggestions.forEach(suggestion => {
                                                        const suggestionDiv = document.createElement('div');
                                                        suggestionDiv.className = 'chatbot-suggestion';
                                                        suggestionDiv.setAttribute('data-suggested-field', suggestion.suggested_field);
                                                        const fieldSpan = document.createElement('span');
                                                        fieldSpan.className = 'suggestion-field';
                                                        fieldSpan.textContent = suggestion.suggested_field;
                                                        const reasonSpan = document.createElement('span');
                                                        reasonSpan.className = 'suggestion-reason';
                                                        reasonSpan.textContent = suggestion.reason || 'No specific reason provided.';
                                                        suggestionDiv.appendChild(fieldSpan);
                                                        suggestionDiv.appendChild(reasonSpan);
                                                        suggestionsHtmlContainer.appendChild(suggestionDiv);
                                                    });
                                                    window.addBotMessage(suggestionsHtmlContainer);
                                                } else if (suggestions && suggestions.length > 0 && suggestions[0].suggested_field === 'N/A') {
                                                    window.addBotMessage(suggestions[0].reason || "Couldn't find alternatives.");
                                                } else {
                                                    window.addBotMessage("Couldn't find alternative suggestions.");
                                                }
                                            })
                                            .catch(error => {
                                                console.error('Error fetching suggestions:', error);
                                                window.addBotMessage(`Error getting suggestions: ${error.message}`);
                                            });
                                        } else {
                                            console.error("addBotMessage function not found.");
                                        }
                                        const chatbotInput = document.getElementById('chatbotInput');
                                        const chatbotSendButton = document.getElementById('chatbotSendButton');
                                        if(chatbotInput) chatbotInput.disabled = false;
                                        if(chatbotSendButton) chatbotSendButton.disabled = false;
                                    });
                                });
                            }

                            let tooltipElement = document.getElementById('field-description-tooltip');
                            if (!tooltipElement) {
                                tooltipElement = document.createElement('div');
                                tooltipElement.id = 'field-description-tooltip';
                                tooltipElement.className = 'tooltip-hidden';
                                document.body.appendChild(tooltipElement);
                            }
                            fileEntryDiv.querySelectorAll('.field-tooltip-trigger').forEach(icon => {
                                icon.addEventListener('mouseover', function(event) {
                                    const fieldName = this.getAttribute('data-field-name');
                                    let tooltipContent = 'No information available.';
                                    if (fieldName && fieldName !== "N/A" && FIELD_DEFINITIONS[fieldName]) {
                                        const definition = FIELD_DEFINITIONS[fieldName];
                                        const description = definition.description || 'No description provided.';
                                        const expectedType = definition.expected_type || 'Not specified.';
                                        tooltipContent = `Description: ${description}\nExpected Type: ${expectedType}`;
                                        tooltipElement.className = 'tooltip-visible';
                                        const rect = this.getBoundingClientRect();
                                        tooltipElement.style.left = (rect.left + window.scrollX + rect.width / 2) + 'px';
                                        tooltipElement.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                                        tooltipElement.style.transform = 'translateX(-50%)';
                                    } else if (fieldName === "N/A") {
                                        tooltipContent = 'This header is currently unmapped.';
                                        tooltipElement.className = 'tooltip-visible';
                                        const rect = this.getBoundingClientRect();
                                        tooltipElement.style.left = (rect.left + window.scrollX + rect.width / 2) + 'px';
                                        tooltipElement.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                                        tooltipElement.style.transform = 'translateX(-50%)';
                                    } else {
                                        tooltipElement.className = 'tooltip-hidden';
                                        return;
                                    }
                                    tooltipElement.innerText = tooltipContent;
                                });
                                icon.addEventListener('mouseout', function() {
                                    tooltipElement.className = 'tooltip-hidden';
                                    tooltipElement.style.transform = '';
                                });
                                icon.addEventListener('click', function() {
                                    if (tooltipElement.classList.contains('tooltip-visible')) {
                                        tooltipElement.className = 'tooltip-hidden';
                                        tooltipElement.style.transform = '';
                                    } else {
                                        const mouseoverEvent = new MouseEvent('mouseover');
                                        this.dispatchEvent(mouseoverEvent);
                                    }
                                });
                            });

                            window.getCurrentChatbotOriginalHeader = function() { // Used by chatbot.js
                                return fileEntryDiv.currentChatbotOriginalHeader; // Store on fileEntryDiv
                            };
                            window.setCurrentChatbotOriginalHeader = function(header) { // Used by chatbot-help-button
                                fileEntryDiv.currentChatbotOriginalHeader = header;
                            };
                            window.clearCurrentChatbotOriginalHeader = function() {
                                fileEntryDiv.currentChatbotOriginalHeader = null;
                            };
                            fileStatusesDiv.appendChild(fileEntryDiv);
                        });
                    } catch (e) {
                        fileStatusesDiv.innerHTML = `<p class="failure">Error parsing server response: ${e.toString()}</p>`;
                        console.error("Error parsing JSON:", e);
                        console.error("Server response:", xhr.responseText);
                    }
                } else { // xhr.status error
                    fileStatusesDiv.innerHTML = `<p class="failure">Upload failed. Server responded with status ${xhr.status}: ${xhr.statusText}</p>`;
                     try {
                        const results = JSON.parse(xhr.responseText);
                        results.forEach(function (result, index) {
                            const fileEntryDiv = document.createElement('div');
                            fileEntryDiv.className = 'file-entry';
                            const statusP = document.createElement('p');
                            let errorTypeDisplay = result.file_type || 'N/A';
                            if (result.file_type && result.file_type.startsWith("error_")) {
                                errorTypeDisplay = `Error (${result.file_type.split('_')[1]})`;
                            }
                            statusP.textContent = `${result.filename}: ${result.message} (Type: ${errorTypeDisplay})`;
                            statusP.className = 'failure';
                            fileEntryDiv.appendChild(statusP);
                            fileStatusesDiv.appendChild(fileEntryDiv);
                        });
                    } catch (e) {
                        console.error("Error parsing JSON error response:", e);
                    }
                }
            });

            xhr.addEventListener('error', function () { /* ... */ });
            xhr.addEventListener('abort', function () { /* ... */ });
            xhr.open('POST', '/upload', true);
            xhr.send(formData);
            fileStatusesDiv.innerHTML = '<p>Starting upload...</p>';
        });
    }

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
});
// Ensure addBotMessage is globally available if not already (it should be from chatbot.js)
// Ensure promptToSaveTemplate is globally available for chatbot.js to call
// window.promptToSaveTemplate = function(fileIdentifier) { ... } // To be defined in chatbot.js
// window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) { ... } // Defined above

// Helper for addBotMessage if not already robust in chatbot.js
if (typeof window.addBotMessage !== 'function') {
    window.addBotMessage = function(content) {
        const chatbotMessagesDiv = document.getElementById('chatbotMessages');
        if (chatbotMessagesDiv) {
            const messageContainer = document.createElement('div');
            messageContainer.classList.add('bot-message');
            if (typeof content === 'string') {
                messageContainer.textContent = content;
            } else if (content instanceof HTMLElement) {
                messageContainer.appendChild(content);
            }
            chatbotMessagesDiv.appendChild(messageContainer);
            chatbotMessagesDiv.scrollTop = chatbotMessagesDiv.scrollHeight;
        } else {
            console.warn("Chatbot message area not found, logging to console:", content);
            // console.log("Bot:", content);
        }
    };
}
