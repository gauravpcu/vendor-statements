document.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const fileStatusesDiv = document.getElementById('fileStatuses');

    let uploadStartTime;
    const supportedTypes = ["PDF", "XLSX", "XLS", "CSV"];

    if (uploadForm) {
        uploadForm.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent default form submission

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

                    const elapsedTime = (Date.now() - uploadStartTime) / 1000; // seconds
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

                fileStatusesDiv.innerHTML = ''; // Clear previous statuses
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const results = JSON.parse(xhr.responseText);
                        results.forEach(function (result, index) {
                            const fileEntryDiv = document.createElement('div');
                            fileEntryDiv.className = 'file-entry';
                            fileEntryDiv.setAttribute('data-filename', result.filename); // Store filename for easy access

                            const statusP = document.createElement('p');
                            statusP.innerHTML = `<strong>File:</strong> ${result.filename} `; // Display filename

                            // Add "View Original" link
                            const viewLink = document.createElement('a');
                            viewLink.href = `/view_uploaded_file/${encodeURIComponent(result.filename)}`;
                            viewLink.textContent = 'View Original';
                            viewLink.className = 'view-original-link';
                            viewLink.target = '_blank';
                            statusP.appendChild(document.createTextNode(' (')); // Add opening parenthesis
                            statusP.appendChild(viewLink);
                            statusP.appendChild(document.createTextNode(')')); // Add closing parenthesis

                            // Append original status message and type display
                            statusP.appendChild(document.createElement('br')); // Line break
                            let typeDisplay = result.file_type;
                            if (result.file_type && result.file_type.startsWith("error_")) {
                                typeDisplay = `Error (${result.file_type.split('_')[1]})`;
                            } else if (!result.success && !supportedTypes.includes(result.file_type ? result.file_type.toUpperCase() : "")){
                                typeDisplay = `Unsupported (${result.file_type || 'unknown'})`;
                            }
                            const messageSpan = document.createElement('span');
                            messageSpan.textContent = `${result.message} (Type: ${typeDisplay})`;
                            messageSpan.className = result.success ? 'success-inline' : 'failure-inline'; // Use inline styling classes
                            statusP.appendChild(messageSpan);

                            fileEntryDiv.appendChild(statusP);

                            // Display headers if available
                            if (result.headers && result.headers.length > 0) {
                                const headersDiv = document.createElement('div');
                                headersDiv.className = 'headers-display';
                                headersDiv.textContent = 'Headers: ' + result.headers.join(', ');
                                fileEntryDiv.appendChild(headersDiv);
                            } else if (result.headers && result.headers.hasOwnProperty('error')) { // Check if headers itself is an error object
                                const headersErrorDiv = document.createElement('div');
                                headersErrorDiv.className = 'headers-error failure'; // Use failure class for styling
                                headersErrorDiv.textContent = 'Headers Error: ' + result.headers.error; // Clarified label
                                fileEntryDiv.appendChild(headersErrorDiv);
                            }

                            // Display field mappings if available
                            if (result.field_mappings && result.field_mappings.length > 0) {
                                const mappingsTable = document.createElement('table');
                                mappingsTable.className = 'mappings-table';

                                const caption = mappingsTable.createCaption();
                                caption.textContent = 'Field Mappings';

                                const thead = mappingsTable.createTHead();
                                const headerRow = thead.insertRow();
                                const headers = ["Original Header", "Mapped Field", "Confidence", "Method"];
                                headers.forEach(function(headerText) {
                                    const th = document.createElement('th');
                                    th.textContent = headerText;
                                    headerRow.appendChild(th);
                                });

                                const tbody = mappingsTable.createTBody();
                                result.field_mappings.forEach(function(mapping, mappingIndex) { // Added mappingIndex
                                    const row = tbody.insertRow();

                                    const cellOriginal = row.insertCell();
                                    cellOriginal.textContent = mapping.original_header;

                                    const cellMapped = row.insertCell();
                                    const selectElement = document.createElement('select');
                                    selectElement.className = 'mapped-field-select';
                                    selectElement.setAttribute('data-original-header', mapping.original_header);
                                    // Unique ID for the select element, useful for later direct manipulation if needed
                                    selectElement.id = `map-select-${fileIndex}-${mappingIndex}`;

                                    // Add default/unmapped option
                                    const unmappedOption = document.createElement('option');
                                    unmappedOption.value = "N/A"; // Or an empty string
                                    unmappedOption.textContent = "-- Unmapped --";
                                    selectElement.appendChild(unmappedOption);

                                    // Populate with standard fields from FIELD_DEFINITIONS
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

                                    // Set selected value based on backend mapping
                                    let currentMappedField = mapping.mapped_field;
                                    if (currentMappedField && currentMappedField.startsWith("Unknown: ")) {
                                        currentMappedField = "N/A"; // Treat "Unknown: ..." as "N/A" for selection
                                    }
                                    if (currentMappedField && selectElement.querySelector(`option[value="${currentMappedField}"]`)) {
                                        selectElement.value = currentMappedField;
                                    } else {
                                        selectElement.value = "N/A"; // Default to unmapped if not found or truly "N/A"
                                    }

                                    cellMapped.appendChild(selectElement);

                                    // Add info icon for tooltip
                                    const infoIcon = document.createElement('span');
                                    infoIcon.className = 'field-tooltip-trigger';
                                    infoIcon.innerHTML = '&#9432;'; // Circled 'i' character
                                    infoIcon.setAttribute('data-field-name', selectElement.value); // Set initial field name
                                    cellMapped.appendChild(infoIcon);

                                    // Update icon's data-field-name when dropdown changes
                                    selectElement.addEventListener('change', function() {
                                        infoIcon.setAttribute('data-field-name', this.value);
                                        // Also update the help button's current mapped field if it exists
                                        const helpButton = row.querySelector('.chatbot-help-button');
                                        if (helpButton) {
                                            helpButton.setAttribute('data-current-mapped-field', this.value);
                                        }
                                    });


                                    if (mapping.error) { // If there was an error in mapping this specific field
                                        const errorSpan = document.createElement('span');
                                        errorSpan.className = 'failure-inline';
                                        errorSpan.style.display = 'block'; // Make it appear on a new line
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
                                    } else { // score < 80
                                        confidenceClass = 'confidence-low';
                                    }
                                    cellConfidence.classList.add(confidenceClass);

                                    // Add a visual cue to the row if confidence is low or there's an error
                                    if (score < 80 || mapping.error) {
                                        row.classList.add('row-needs-review');
                                    }

                                    const cellMethod = row.insertCell();
                                    cellMethod.textContent = mapping.method || 'N/A';

                                    // Add Chatbot Help button cell
                                    const cellChatHelp = row.insertCell();
                                    const chatHelpButton = document.createElement('button');
                                    chatHelpButton.className = 'chatbot-help-button';
                                    chatHelpButton.textContent = 'Suggest';
                                    chatHelpButton.setAttribute('data-original-header', mapping.original_header);
                                    chatHelpButton.setAttribute('data-current-mapped-field', selectElement.value); // Get current selection

                                    // Update data attribute when selection changes
                                    selectElement.addEventListener('change', function() {
                                        chatHelpButton.setAttribute('data-current-mapped-field', this.value);
                                    });

                                    cellChatHelp.appendChild(chatHelpButton);
                                });
                                fileEntryDiv.appendChild(mappingsTable);

                                // Add "Process File" button for this file entry
                                const processFileButton = document.createElement('button');
                                processFileButton.textContent = 'Process File Data';
                                processFileButton.className = 'process-file-button';
                                // Store necessary info on the button - result.filename is assumed to be the identifier
                                processFileButton.setAttribute('data-file-identifier', result.filename);
                                processFileButton.setAttribute('data-file-type', result.file_type); // Assuming result.file_type holds CSV, XLSX etc.
                                fileEntryDiv.appendChild(processFileButton);

                                processFileButton.addEventListener('click', function() {
                                    const fileIdentifier = this.getAttribute('data-file-identifier');
                                    const fileType = this.getAttribute('data-file-type');
                                    const currentMappings = [];

                                    // Find the table associated with this button's fileEntryDiv
                                    const tableBody = this.closest('.file-entry').querySelector('.mappings-table tbody');
                                    if (tableBody) {
                                        tableBody.querySelectorAll('tr').forEach(row => {
                                            const originalHeader = row.cells[0].textContent; // Assuming first cell is original header
                                            const selectElement = row.cells[1].querySelector('select.mapped-field-select');
                                            const mappedField = selectElement ? selectElement.value : 'N/A';
                                            // Confidence isn't strictly needed by backend for this step, but good to gather
                                            const confidenceText = row.cells[2].textContent;
                                            const confidenceScore = parseFloat(confidenceText.replace('%','')) || 0;

                                            currentMappings.push({
                                                original_header: originalHeader,
                                                mapped_field: mappedField,
                                                confidence_score: confidenceScore // Or some default/current value
                                            });
                                        });
                                    }

                                    console.log("Finalized Mappings for processing:", currentMappings);
                                    addBotMessage(`Processing file: ${fileIdentifier}...`); // Using bot message for feedback

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
                                            const fileEntryDiv = this.closest('.file-entry'); // Get the parent file-entry div
                                            let dataDisplayContainer = fileEntryDiv.querySelector('.extracted-data-container');

                                            if (!dataDisplayContainer) {
                                                dataDisplayContainer = document.createElement('div');
                                                dataDisplayContainer.className = 'extracted-data-container';
                                                fileEntryDiv.appendChild(dataDisplayContainer);
                                            }
                                            dataDisplayContainer.innerHTML = ''; // Clear previous data

                                        if (data.error) {
                                            addBotMessage(`Error processing file ${fileIdentifier}: ${data.error}`);
                                                const errorP = document.createElement('p');
                                                errorP.className = 'failure';
                                                errorP.textContent = `Error extracting data: ${data.error}`;
                                                dataDisplayContainer.appendChild(errorP);
                                            } else if (data.data && data.data.length > 0) {
                                                addBotMessage(`Successfully processed ${fileIdentifier}. ${data.message || ''} Displaying ${data.data.length} extracted records.`);

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
                                                    headers.forEach(mapped_field_name => { // headers are the mapped_field_names
                                                        const cell = row.insertCell();
                                                        const cellValue = record[mapped_field_name];
                                                        cell.textContent = cellValue !== undefined && cellValue !== null ? cellValue : '';

                                                        // Basic Data Validation and Highlighting
                                                        if (FIELD_DEFINITIONS && FIELD_DEFINITIONS[mapped_field_name] && cellValue !== null && cellValue !== "") {
                                                            const expectedType = FIELD_DEFINITIONS[mapped_field_name].expected_type;
                                                            let isValid = true;
                                                            const valueStr = String(cellValue).trim();

                                                            switch (expectedType) {
                                                                case 'date':
                                                                    // Check if it's a number (like Excel date serial) OR can be parsed as a date.
                                                                    // This is a very basic check. Robust date parsing is complex.
                                                                    if (!/^\d{5,}$/.test(valueStr) && isNaN(new Date(valueStr).getTime())) {
                                                                        isValid = false;
                                                                    }
                                                                    break;
                                                                case 'number':
                                                                case 'currency': // Basic check: treat like number. Allow symbols for now.
                                                                    // Remove common currency symbols and then check for number.
                                                                    // This regex removes $, €, £, ¥, commas and spaces.
                                                                    const numericValue = valueStr.replace(/[\$\€\£\¥,\s]/g, '');
                                                                    if (isNaN(parseFloat(numericValue)) || !isFinite(parseFloat(numericValue))) {
                                                                        isValid = false;
                                                                    }
                                                                    break;
                                                                case 'percentage':
                                                                    const percValue = valueStr.replace(/[%,\s]/g, '');
                                                                    if (isNaN(parseFloat(percValue)) || !isFinite(parseFloat(percValue))) {
                                                                        isValid = false;
                                                                    }
                                                                    break;
                                                                case 'string':
                                                                    // Most non-null/empty strings are fine.
                                                                    // Specific string format validation (e.g. email) is more advanced.
                                                                    break;
                                                                default:
                                                                    // No specific validation for unknown types
                                                                    break;
                                                            }
                                                            if (!isValid) {
                                                                cell.classList.add('data-validation-error');
                                                            }
                                                        }
                                                    });
                                                });
                                                dataDisplayContainer.appendChild(table);
                                                // Scroll to the new table
                                                dataDisplayContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                                        } else {
                                                addBotMessage(`No data was extracted for ${fileIdentifier} based on the current mappings or the file is empty.`);
                                                const noDataP = document.createElement('p');
                                                noDataP.textContent = 'No data was extracted or the file is empty.';
                                                dataDisplayContainer.appendChild(noDataP);
                                        }
                                    })
                                    .catch(error => {
                                        console.error('Error processing file:', error);
                                        addBotMessage(`Network or system error processing file ${fileIdentifier}: ${error.toString()}`);
                                        alert(`Error processing file: ${error.toString()}`);
                                    });
                                });


                                let currentChatbotOriginalHeader = null; // Variable to store context

                                // Add event listener for all chatbot help buttons within this table
                                fileEntryDiv.querySelectorAll('.chatbot-help-button').forEach(button => {
                                    button.addEventListener('click', function() {
                                        const originalHeader = this.getAttribute('data-original-header');
                                        const currentMappedField = this.getAttribute('data-current-mapped-field');
                                        currentChatbotOriginalHeader = originalHeader; // Store context

                                        // Ensure chatbot is visible
                                        const chatbotPanel = document.getElementById('chatbotPanel'); // Ensure we have the panel
                                        if (typeof window.toggleChatbot === 'function' && chatbotPanel && chatbotPanel.classList.contains('hidden')) {
                                            window.toggleChatbot();
                                        }

                                        if (typeof window.addBotMessage === 'function') {
                                            window.addBotMessage(`Looking for suggestions for header: "${originalHeader}" (currently mapped to: "${currentMappedField}")...`);

                                            fetch('/chatbot_suggest_mapping', {
                                                method: 'POST',
                                                headers: {
                                                    'Content-Type': 'application/json',
                                                },
                                                body: JSON.stringify({
                                                    original_header: originalHeader,
                                                    current_mapped_field: currentMappedField
                                                }),
                                            })
                                            .then(response => {
                                                if (!response.ok) {
                                                    throw new Error(`HTTP error! status: ${response.status}`);
                                                }
                                                return response.json();
                                            })
                                            .then(suggestions => {
                                                if (suggestions && suggestions.length > 0 && suggestions[0].suggested_field !== 'N/A') {
                                                    const suggestionsHtmlContainer = document.createElement('div');
                                                    suggestionsHtmlContainer.className = 'suggestions-list'; // For overall list styling

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
                                                    window.addBotMessage(suggestions[0].reason || "I couldn't find any alternative suggestions for this header.");
                                                } else {
                                                    window.addBotMessage("I couldn't find any alternative suggestions for this header.");
                                                }
                                            })
                                            .catch(error => {
                                                console.error('Error fetching suggestions:', error);
                                                window.addBotMessage(`Sorry, I encountered an error trying to get suggestions: ${error.message}`);
                                            });

                                        } else {
                                            console.error("addBotMessage function not found.");
                                        }
                                        // Enable chatbot input
                                        const chatbotInput = document.getElementById('chatbotInput');
                                        const chatbotSendButton = document.getElementById('chatbotSendButton');
                                        if(chatbotInput) chatbotInput.disabled = false;
                                        if(chatbotSendButton) chatbotSendButton.disabled = false;
                                    });
                                });

                                // Event listener for clicking on a suggestion (delegated to fileEntryDiv)
                                // This needs to be set up once per fileEntryDiv if suggestions are dynamically added.
                                // Or, more robustly, on a static parent like chatbotMessagesDiv in chatbot.js
                                // For now, let's attach it to chatbotMessagesDiv in chatbot.js as it's more central.
                                // The currentChatbotOriginalHeader will be used by that listener.
                            }

                            // Tooltip logic (can be part of this file or a separate utility)
                            // Create a single tooltip element, reuse it
                            let tooltipElement = document.getElementById('field-description-tooltip');
                            if (!tooltipElement) {
                                tooltipElement = document.createElement('div');
                                tooltipElement.id = 'field-description-tooltip';
                                tooltipElement.className = 'tooltip-hidden'; // Initially hidden
                                document.body.appendChild(tooltipElement); // Append to body to avoid z-index issues
                            }

                            fileEntryDiv.querySelectorAll('.field-tooltip-trigger').forEach(icon => {
                                icon.addEventListener('mouseover', function(event) {
                                    const fieldName = this.getAttribute('data-field-name');
                                    let tooltipContent = 'No information available.'; // Default content

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
                                        tooltipElement.className = 'tooltip-visible'; // Still show tooltip for "N/A"
                                        const rect = this.getBoundingClientRect();
                                        tooltipElement.style.left = (rect.left + window.scrollX + rect.width / 2) + 'px';
                                        tooltipElement.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                                        tooltipElement.style.transform = 'translateX(-50%)';
                                    } else {
                                        // fieldName is something else unexpected, or FIELD_DEFINITIONS[fieldName] is missing
                                        tooltipElement.className = 'tooltip-hidden'; // Hide if no relevant info
                                        return; // Early exit if no valid fieldName to show tooltip for
                                    }
                                    tooltipElement.innerText = tooltipContent; // Use innerText to preserve line breaks
                                });
                                icon.addEventListener('mouseout', function() {
                                    tooltipElement.className = 'tooltip-hidden'; // Hide it
                                    tooltipElement.style.transform = ''; // Reset transform
                                });
                                icon.addEventListener('click', function() {
                                    // Optional: toggle tooltip on click for mobile friendliness
                                    if (tooltipElement.classList.contains('tooltip-visible')) {
                                        tooltipElement.className = 'tooltip-hidden';
                                        tooltipElement.style.transform = '';
                                    } else {
                                        // Manually trigger the mouseover logic for content and positioning
                                        const mouseoverEvent = new MouseEvent('mouseover');
                                        this.dispatchEvent(mouseoverEvent);
                                    }
                                });
                            });

                            // Expose currentChatbotOriginalHeader for chatbot.js to use
                            // This is a bit of a hack; a more robust solution might involve custom events or a shared state module.
                            window.getCurrentChatbotOriginalHeader = function() {
                                return currentChatbotOriginalHeader;
                            };
                            window.clearCurrentChatbotOriginalHeader = function() {
                                currentChatbotOriginalHeader = null;
                            }


                            // Add dropdown for manual type selection
                            // Show dropdown if upload was technically successful but type is unknown/unsupported, or if user just wants to change it.
                            // Also show if there was an error in detection, allowing user to specify.
                            if (result.success || result.file_type === "unknown" || (result.file_type && result.file_type.startsWith("error_")) || (result.file_type && !supportedTypes.includes(result.file_type.toUpperCase())) ) {
                                const selectLabel = document.createElement('label');
                                selectLabel.textContent = ' Override Type: ';
                                selectLabel.htmlFor = `type-select-${index}`; // Use index for unique ID
                                fileEntryDiv.appendChild(selectLabel);

                                const typeSelect = document.createElement('select');
                                typeSelect.id = `type-select-${index}`; // Unique ID for the select element
                                typeSelect.name = `type-override-${result.filename}`; // Name can include filename

                                // Add a default "Select type" option
                                const defaultOption = document.createElement('option');
                                defaultOption.value = "";
                                defaultOption.textContent = "Select to override...";
                                typeSelect.appendChild(defaultOption);

                                supportedTypes.forEach(function(type) {
                                    const option = document.createElement('option');
                                    option.value = type;
                                    option.textContent = type;
                                    if (result.file_type && result.file_type.toUpperCase() === type) {
                                        option.selected = true;
                                    }
                                    typeSelect.appendChild(option);
                                });
                                fileEntryDiv.appendChild(typeSelect);
                            }
                            fileStatusesDiv.appendChild(fileEntryDiv);
                        });
                    } catch (e) {
                        fileStatusesDiv.innerHTML = `<p class="failure">Error parsing server response: ${e.toString()}</p>`;
                        console.error("Error parsing JSON:", e);
                        console.error("Server response:", xhr.responseText);
                    }
                } else {
                    fileStatusesDiv.innerHTML = `<p class="failure">Upload failed. Server responded with status ${xhr.status}: ${xhr.statusText}</p>`;
                     try {
                        const results = JSON.parse(xhr.responseText); // Attempt to parse error response too
                        results.forEach(function (result, index) { // Added index here
                            const fileEntryDiv = document.createElement('div'); // Create div even for errors
                            fileEntryDiv.className = 'file-entry';

                            const statusP = document.createElement('p');
                            let errorTypeDisplay = result.file_type || 'N/A';
                            if (result.file_type && result.file_type.startsWith("error_")) {
                                errorTypeDisplay = `Error (${result.file_type.split('_')[1]})`;
                            }
                            statusP.textContent = `${result.filename}: ${result.message} (Type: ${errorTypeDisplay})`;
                            statusP.className = 'failure'; // Always failure here
                            fileEntryDiv.appendChild(statusP);

                            // Optionally, add dropdowns even for failed individual uploads if needed
                            // For now, keeping it simpler: dropdowns primarily for successful/type-issue uploads

                            fileStatusesDiv.appendChild(fileEntryDiv);
                        });
                    } catch (e) {
                        console.error("Error parsing JSON error response:", e);
                    }
                }
            });

            xhr.addEventListener('error', function () {
                overallProgressBar.style.width = '0%';
                overallProgressBar.textContent = 'Error';
                etaDisplay.textContent = 'N/A';
                fileStatusesDiv.innerHTML = '<p class="failure">An error occurred during the upload. Please try again.</p>';
            });

            xhr.addEventListener('abort', function () {
                overallProgressBar.style.width = '0%';
                overallProgressBar.textContent = 'Aborted';
                etaDisplay.textContent = 'N/A';
                fileStatusesDiv.innerHTML = '<p class="failure">Upload aborted by the user or a network issue.</p>';
            });

            xhr.open('POST', '/upload', true);
            xhr.send(formData);
            fileStatusesDiv.innerHTML = '<p>Starting upload...</p>'; // Initial message
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
