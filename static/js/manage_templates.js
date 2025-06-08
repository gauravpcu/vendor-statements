document.addEventListener('DOMContentLoaded', function() {
    const templatesTableContainer = document.getElementById('templatesTableContainer');
    const loadingMessage = document.getElementById('loadingMessage');
    const errorMessageDiv = document.getElementById('errorMessage');

    function displayError(message) {
        if (loadingMessage) loadingMessage.style.display = 'none';
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
        // Clear previous table if any
        const existingTable = templatesTableContainer.querySelector('table');
        if (existingTable) existingTable.remove();
    }

    function displaySuccessMessage(message) {
        // For now, using alert. Could be a temporary div.
        alert(message);
    }

    function fetchAndDisplayTemplates() {
        if (loadingMessage) loadingMessage.style.display = 'block';
        errorMessageDiv.style.display = 'none'; // Hide previous errors

        fetch('/list_templates')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (loadingMessage) loadingMessage.style.display = 'none';

                // Clear only table, not error message div
                const existingTable = templatesTableContainer.querySelector('table');
                if (existingTable) existingTable.remove();

                if (!data.templates || !Array.isArray(data.templates) || data.templates.length === 0) {
                    templatesTableContainer.innerHTML = '<p>No templates found.</p>'; // Replace everything
                    return;
                }

                const table = document.createElement('table');
                table.innerHTML = `
                    <thead>
                        <tr>
                            <th>Template Name</th>
                            <th>Filename</th>
                            <th>Created On</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                    </tbody>
                `;
                const tbody = table.querySelector('tbody');

                data.templates.forEach(template => {
                    const tr = document.createElement('tr');

                    const nameTd = document.createElement('td');
                    nameTd.textContent = template.display_name;
                    tr.appendChild(nameTd);

                    const fileIdTd = document.createElement('td');
                    fileIdTd.textContent = template.file_id;
                    tr.appendChild(fileIdTd);

                    const timestampTd = document.createElement('td');
                    // Attempt to format timestamp for better readability if it's a valid ISO string
                    let formattedTimestamp = template.creation_timestamp || 'N/A';
                    if (formattedTimestamp !== 'N/A') {
                        try {
                            const date = new Date(formattedTimestamp);
                            // Check if date is valid after parsing
                            if (!isNaN(date.getTime())) {
                                formattedTimestamp = date.toLocaleString(); // User's local time and format
                            } else {
                                formattedTimestamp = template.creation_timestamp; // Show original if invalid
                            }
                        } catch (e) {
                            // If error in parsing, show original
                            formattedTimestamp = template.creation_timestamp;
                        }
                    }
                    timestampTd.textContent = formattedTimestamp;
                    tr.appendChild(timestampTd);

                    const actionsTd = document.createElement('td');
                    const deleteButton = document.createElement('button');
                    deleteButton.classList.add('delete-template-btn'); // Class for styling and event delegation
                    deleteButton.dataset.filename = template.file_id;
                    deleteButton.textContent = 'Delete';
                    actionsTd.appendChild(deleteButton);
                    tr.appendChild(actionsTd);

                    tbody.appendChild(tr);
                });

                // Make sure loading message is gone before adding table
                const currentLoadingMsg = document.getElementById('loadingMessage');
                if(currentLoadingMsg) currentLoadingMsg.remove();

                templatesTableContainer.appendChild(table);
            })
            .catch(error => {
                console.error('Error fetching templates:', error);
                displayError('Failed to load templates. ' + error.message);
            });
    }

    // Event listener for delete buttons (using event delegation)
    templatesTableContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('delete-template-btn')) {
            const templateFilename = event.target.dataset.filename;
            if (!templateFilename) {
                alert('Error: Template filename not found.');
                return;
            }

            if (window.confirm(`Are you sure you want to delete template '${templateFilename}'?`)) {
                fetch(`/delete_template/${encodeURIComponent(templateFilename)}`, {
                    method: 'DELETE',
                })
                .then(response => {
                    // Regardless of ok status, try to parse JSON, as error messages might be in JSON body
                    return response.json().then(data => ({ ok: response.ok, status: response.status, data }));
                })
                .then(result => {
                    if (result.ok) {
                        displaySuccessMessage(result.data.message || 'Template deleted successfully.');
                        fetchAndDisplayTemplates(); // Refresh the list
                    } else {
                        // Server responded with an error status code (4xx, 5xx)
                        const errorMsg = result.data.error || `Failed to delete template. Status: ${result.status}`;
                        alert(`Error: ${errorMsg}`); // Using alert for error feedback from delete
                        // Optionally, call fetchAndDisplayTemplates() even on error if the list might have changed
                        // or if some deletions might succeed while others fail (though less likely with single delete)
                    }
                })
                .catch(error => {
                    // Network error or issue with parsing the JSON response itself
                    console.error('Error deleting template:', error);
                    alert('An unexpected error occurred while trying to delete the template. ' + error.message);
                });
            }
        }
    });

    // Initial call to fetch and display templates
    fetchAndDisplayTemplates();
});
