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

                            // Add dropdown for manual type selection
                            // Show dropdown if upload was technically successful but type is unknown/unsupported, or if user just wants to change it.
                            // Also show if there was an error in detection, allowing user to specify.
                            if (result.success || result.file_type === "unknown" || result.file_type.startsWith("error_") || (result.file_type && !supportedTypes.includes(result.file_type.toUpperCase())) ) {
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
