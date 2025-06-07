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

                            const statusP = document.createElement('p');
                            let typeDisplay = result.file_type;
                            if (result.file_type && result.file_type.startsWith("error_")) {
                                typeDisplay = `Error (${result.file_type.split('_')[1]})`;
                            } else if (!result.success && !supportedTypes.includes(result.file_type ? result.file_type.toUpperCase() : "")){
                                typeDisplay = `Unsupported (${result.file_type || 'unknown'})`;
                            }
                            statusP.textContent = `${result.filename}: ${result.message} (Type: ${typeDisplay})`;
                            statusP.className = result.success ? 'success' : 'failure';
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
                                result.field_mappings.forEach(function(mapping) {
                                    const row = tbody.insertRow();

                                    const cellOriginal = row.insertCell();
                                    cellOriginal.textContent = mapping.original_header;

                                    const cellMapped = row.insertCell();
                                    const selectElement = document.createElement('select');
                                    selectElement.className = 'mapped-field-select';
                                    selectElement.setAttribute('data-original-header', mapping.original_header);
                                    // Add a unique ID if needed, e.g., using file index and mapping index
                                    // selectElement.id = `map-select-${fileIndex}-${mappingIndex}`;

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

                                });
                                fileEntryDiv.appendChild(mappingsTable);
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
