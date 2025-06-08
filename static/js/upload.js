document.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const overallProgressBar = document.getElementById('overallProgressBar');
    const etaDisplay = document.getElementById('eta');
    const fileStatusesDiv = document.getElementById('fileStatuses');

    let uploadStartTime;
    window.extractedDataCache = window.extractedDataCache || {}; // Initialize cache

    function displayMessage(message, isError = false) {
        // ... (implementation as before)
    }

    function executeSaveTemplateRequest(templateName, mappings, skipRows, overwrite = false, fileIdentifierForContext = null) {
        // ... (implementation as before)
    }

    window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) {
        // ... (implementation as before)
    };

    function renderMappingTable(fileEntryDiv, fileIdentifier, fileType, headers, fieldMappings, fileIndex) {
        // ... (implementation as before, including all table element creation and event listeners for elements within the table)
    }

    // --- Main XHR Load Handler for initial file upload processing ---
    if (uploadForm) {
        // ... (uploadForm submit listener and XHR setup as before) ...
        const xhr = new XMLHttpRequest(); // Re-added for context
        xhr.upload.addEventListener('progress', function (event) { /* ... */ }); // Re-added for context
        xhr.addEventListener('load', function () {
            // ... (UI updates like progress bar, eta) ...
            fileStatusesDiv.innerHTML = '';
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const results = JSON.parse(xhr.responseText);
                    results.forEach(function (result, fileIndex) {
                        const fileEntryDiv = document.createElement('div');
                        // ... (Setup fileEntryDiv, statusP, vendorNameContainer, skipRowsContainer, headersDisplayDiv as before) ...
                        // ... (Call renderMappingTable as before) ...
                        // ... (Add Process File button and Save Template button as before) ...

                        // Simplified structure for brevity, assuming the full UI for each file is built here
                        // including all buttons and input fields as per previous steps.

                        fileStatusesDiv.appendChild(fileEntryDiv);
                    });
                } catch (e) { displayMessage(`Error parsing server response: ${e.toString()}`, true); }
            } else { displayMessage(`Upload failed: Server status ${xhr.status}`, true); }
        });
        xhr.addEventListener('error', function () { /* ... */ });
        xhr.addEventListener('abort', function () { /* ... */ });
        // xhr.open('POST', '/upload', true); // This would be in the submit handler
        // xhr.send(formData);
        // fileStatusesDiv.innerHTML = '<p>Starting upload...</p>';
    }

    // --- Delegated Event Listeners for dynamically added buttons ---
    fileStatusesDiv.addEventListener('click', function(event) {
        const target = event.target;

        if (target.classList.contains('reload-headers-button')) {
            // ... (reload headers logic as before) ...
        } else if (target.classList.contains('process-file-button')) {
            // ... (process file data listener logic as before, including caching data in window.extractedDataCache[fileIdentifier]) ...
            // ... after successfully getting data and creating table:
            // if (data.data && data.data.length > 0) {
            //     ...
            //     window.extractedDataCache[fileIdentifier] = data.data; // Cache data
            //     ...
            //     const exportButton = dataDisplayContainer.querySelector('.export-to-excel-button');
            //     if (!exportButton) { /* create and append exportButton */ }
            // } else {
            //     window.extractedDataCache[fileIdentifier] = null; // Clear if no data
            // }
            // ...
        } else if (target.classList.contains('save-mappings-template-button')) {
            // ... (save template workflow trigger) ...
        } else if (target.classList.contains('btn-remember-yes') || target.classList.contains('btn-remember-no')) {
            // ... (remember mapping prompt listener logic) ...
        } else if (target.classList.contains('export-to-excel-button')) {
            const fileId = target.getAttribute('data-file-identifier');
            const dataToExport = window.extractedDataCache ? window.extractedDataCache[fileId] : null;

            if (!dataToExport || dataToExport.length === 0) {
                displayMessage("No data available to export. Please process the file first.", true);
                return;
            }

            const baseFilename = fileId.substring(0, fileId.lastIndexOf('.')) || fileId;
            const outputFilename = `${baseFilename}_exported_data.xlsx`;

            displayMessage(`Requesting Excel export for ${fileId}...`);

            fetch('/export_to_excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    data_to_export: dataToExport,
                    output_filename: outputFilename
                })
            })
            .then(async response => {
                if (response.ok) {
                    const disposition = response.headers.get('Content-Disposition');
                    let filenameFromServer = outputFilename; // Default to what we sent
                    if (disposition && disposition.includes('attachment')) {
                        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                        const matches = filenameRegex.exec(disposition);
                        if (matches != null && matches[1]) {
                            filenameFromServer = matches[1].replace(/['"]/g, '');
                        }
                    }

                    response.blob().then(blob => {
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = filenameFromServer;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        displayMessage(`Excel file "${filenameFromServer}" download initiated.`);
                    }).catch(blobError => {
                        console.error('Error processing blob for Excel export:', blobError);
                        displayMessage('Error processing file for download.', true);
                    });

                } else { // response not ok
                    try {
                        const errorData = await response.json(); // Try to parse JSON error from backend
                        displayMessage(`Export failed: ${errorData.error || response.statusText}`, true);
                    } catch (e) { // If response is not JSON or other parsing error
                        displayMessage(`Export failed with status: ${response.status}. Could not parse error details.`, true);
                    }
                }
            })
            .catch(error => {
                console.error('Fetch error exporting to Excel:', error);
                displayMessage(`Network error during Excel export: ${error.toString()}`, true);
            });
        }
    });

    function formatTime(seconds) { /* ... */ }
});
if (typeof window.addBotMessage !== 'function') { /* ... default addBotMessage ... */ }
