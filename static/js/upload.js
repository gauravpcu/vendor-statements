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
        // ... (implementation as before, confirmed to be fine from previous step)
    }

    window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) {
        // ... (implementation as before, confirmed to be fine from previous step)
    };

    function renderMappingTable(fileEntryDiv, fileIdentifier, fileType, headers, fieldMappings, fileIndex) {
        // ... (implementation as before - this should include re-attaching listener to .chatbot-help-button or ensuring delegation works)
    }

    let advTooltipElement;
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
            // 1. Confirm event.preventDefault() is called first.
            event.preventDefault();
            console.log("Upload form submission prevented."); // Diagnostic log

            try { // Start of new try...catch block
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

                xhr.upload.addEventListener('progress', function (event) {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        if(overallProgressBar) {
                            overallProgressBar.style.width = percentComplete.toFixed(2) + '%';
                            overallProgressBar.textContent = percentComplete.toFixed(2) + '%';
                        }
                    }
                });

                xhr.addEventListener('load', function () {
                    if(overallProgressBar) {
                        overallProgressBar.style.width = '100%';
                        overallProgressBar.textContent = '100%';
                    }
                    if(etaDisplay) etaDisplay.textContent = formatTime(0);

                    fileStatusesDiv.innerHTML = '';
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const results = JSON.parse(xhr.responseText);
                            results.forEach(function (result, fileIndex) {
                                // ... (rest of the UI generation for each file result as in previous versions)
                                // This includes creating fileEntryDiv, statusP, vendorNameContainer, skipRowsContainer,
                                // headersDisplayDiv, calling renderMappingTable, adding buttons, etc.
                                // For brevity, not repeating all that UI code here, but assuming it's present and correct.
                                // Key is that this part is now within the try...catch of the XHR load.
                                const fileEntryDiv = document.createElement('div'); // Placeholder for actual UI build
                                fileEntryDiv.className = 'file-entry';
                                fileEntryDiv.innerHTML = `<p>File: ${result.filename} - ${result.message}</p>`;
                                // In reality, this would call a function that builds the full file entry UI
                                // including renderMappingTable if mappings exist.
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

                xhr.addEventListener('error', function () {
                    console.error("XHR error event occurred.");
                    displayMessage('Upload network error. Please check your connection.', true);
                });
                xhr.addEventListener('abort', function () {
                    console.warn("XHR upload aborted.");
                    displayMessage('Upload aborted by the user or a network issue.', true);
                });

                xhr.open('POST', '/upload', true);
                console.log("Sending XHR request to /upload..."); // Diagnostic log
                xhr.send(formData);
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

    // ... (rest of the file: delegated event listeners, formatTime, global functions, etc.)
    // The delegated event listener for fileStatusesDiv should remain as is from previous versions.
    // The renderMappingTable function should also be as complete as in previous versions.
});

// Ensure addBotMessage is globally available
if (typeof window.addBotMessage !== 'function') {
    window.addBotMessage = function(content) {
        // ... (default implementation as before)
    };
}

// Ensure other window functions are defined if they are referenced elsewhere (like chatbot.js)
// window.promptToSaveTemplate = function(fileIdentifier) { /* defined in chatbot.js */ };
// window.triggerSaveTemplateWorkflow = function(fileIdentifier, contextElement) { /* defined above */ };
// window.getCurrentChatbotOriginalHeader = function() { /* defined in XHR load's forEach */ };
// window.setCurrentChatbotOriginalHeader = function(header, fileEntryElement) { /* defined in XHR load's forEach */ };
// window.clearCurrentChatbotOriginalHeader = function(fileEntryElement) { /* defined in XHR load's forEach */ };
// ... (other helper functions like formatTime)
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
