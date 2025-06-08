document.addEventListener('DOMContentLoaded', function() {
    const vendorsListContainer = document.getElementById('vendorsListContainer');
    const preferencesForVendorContainer = document.getElementById('preferencesForVendorContainer');
    const selectedVendorNameSpan = document.getElementById('selectedVendorName');
    const globalMessagesDiv = document.getElementById('globalMessages'); // For vendor list messages
    const specificPreferenceMessagesDiv = document.getElementById('specificPreferenceMessages'); // For specific preference table messages

    function showMessage(element, message, isError = false) {
        if (!element) return;
        element.textContent = message;
        element.className = 'message-area'; // Reset classes
        if (isError) {
            element.classList.add('error');
        } else {
            element.classList.add('success');
        }
        element.style.display = 'block';
        // Auto-hide message after some time
        setTimeout(() => { element.style.display = 'none'; }, 5000);
    }

    function clearContent(element, loadingText = "Loading...") {
        // Clear previous messages first
        const messageArea = element.id === 'vendorsListContainer' ? globalMessagesDiv : specificPreferenceMessagesDiv;
        if(messageArea) messageArea.style.display = 'none';

        // Clear main content and show loading
        const p = element.querySelector('p.loading-text') || document.createElement('p');
        p.className = 'loading-text';
        p.textContent = loadingText;
        element.innerHTML = ''; // Clear everything
        element.appendChild(p); // Add back loading message
    }

    function fetchAndDisplayVendors() {
        clearContent(vendorsListContainer, "Loading vendors...");
        preferencesForVendorContainer.style.display = 'none'; // Hide specific prefs section

        fetch('/list_vendors_with_preferences')
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error ${response.status} fetching vendors.`);
                return response.json();
            })
            .then(data => {
                const loadingP = vendorsListContainer.querySelector('p.loading-text');
                if(loadingP) loadingP.remove();

                if (data.error) {
                    throw new Error(data.error);
                }
                if (!data.vendors || data.vendors.length === 0) {
                    vendorsListContainer.innerHTML = '<p>No vendor preferences files found.</p>';
                    return;
                }

                const ul = document.createElement('ul');
                data.vendors.forEach(vendor => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <span class="vendor-name">${vendor.display_name}</span>
                        <span class="action-buttons">
                            <button class="view-prefs-btn" data-vendor-file-id="${vendor.vendor_file_id}" data-vendor-display-name="${vendor.display_name}">View/Manage Specific</button>
                            <button class="delete-all-prefs-btn" data-vendor-file-id="${vendor.vendor_file_id}" data-vendor-display-name="${vendor.display_name}">Delete All For Vendor</button>
                        </span>
                    `;
                    ul.appendChild(li);
                });
                vendorsListContainer.appendChild(ul);
            })
            .catch(error => {
                console.error('Error fetching vendors:', error);
                showMessage(globalMessagesDiv, `Error loading vendors: ${error.message}`, true);
                const loadingP = vendorsListContainer.querySelector('p.loading-text');
                if(loadingP) loadingP.textContent = ''; // Clear loading text on error
            });
    }

    function fetchAndDisplaySpecificPreferences(vendorFileId, vendorDisplayName) {
        clearContent(preferencesForVendorContainer, `Loading preferences for ${vendorDisplayName}...`);
        selectedVendorNameSpan.textContent = vendorDisplayName;
        preferencesForVendorContainer.style.display = 'block';

        // Backend /get_learned_preferences expects original vendor name for path parameter
        fetch(`/get_learned_preferences/${encodeURIComponent(vendorDisplayName)}`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error ${response.status} fetching specific preferences.`);
                return response.json();
            })
            .then(data => {
                const loadingP = preferencesForVendorContainer.querySelector('p.loading-text');
                if(loadingP) loadingP.remove();

                if (data.error) throw new Error(data.error);

                if (!data.preferences || data.preferences.length === 0) {
                    preferencesForVendorContainer.insertAdjacentHTML('beforeend', '<p>No specific preferences found for this vendor.</p>');
                    return;
                }

                const table = document.createElement('table');
                table.innerHTML = `
                    <thead>
                        <tr>
                            <th>Original Header</th>
                            <th>Mapped Field</th>
                            <th>Confirmations</th>
                            <th>Last Updated</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                `;
                const tbody = table.querySelector('tbody');
                data.preferences.forEach(pref => {
                    const tr = document.createElement('tr');
                    let formattedTimestamp = pref.last_updated || 'N/A';
                    if (formattedTimestamp !== 'N/A') {
                        try {
                            const date = new Date(formattedTimestamp);
                            if (!isNaN(date.getTime())) formattedTimestamp = date.toLocaleString();
                        } catch (e) { /* Do nothing, use original */ }
                    }

                    tr.innerHTML = `
                        <td>${pref.original_header}</td>
                        <td>${pref.mapped_field}</td>
                        <td>${pref.confirmation_count || 'N/A'}</td>
                        <td>${formattedTimestamp}</td>
                        <td>
                            <button class="delete-specific-pref-btn"
                                    data-vendor-file-id="${vendorFileId}"
                                    data-original-header="${pref.original_header}"
                                    data-vendor-display-name="${vendorDisplayName}">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
                preferencesForVendorContainer.appendChild(table);
            })
            .catch(error => {
                console.error('Error fetching specific preferences:', error);
                showMessage(specificPreferenceMessagesDiv, `Error loading preferences for ${vendorDisplayName}: ${error.message}`, true);
                 const loadingP = preferencesForVendorContainer.querySelector('p.loading-text');
                if(loadingP) loadingP.textContent = '';
            });
    }

    // Event delegation for vendor list actions
    vendorsListContainer.addEventListener('click', function(event) {
        const target = event.target;
        const vendorFileId = target.dataset.vendorFileId;
        const vendorDisplayName = target.dataset.vendorDisplayName;

        if (target.classList.contains('view-prefs-btn')) {
            fetchAndDisplaySpecificPreferences(vendorFileId, vendorDisplayName);
        } else if (target.classList.contains('delete-all-vendor-prefs-btn')) {
            if (window.confirm(`Are you sure you want to delete ALL preferences for vendor '${vendorDisplayName}' (file: ${vendorFileId})?`)) {
                fetch(`/delete_vendor_preferences/${encodeURIComponent(vendorFileId)}`, { method: 'DELETE' })
                    .then(response => response.json().then(data => ({ ok: response.ok, data })))
                    .then(result => {
                        if (result.ok) {
                            showMessage(globalMessagesDiv, result.data.message || 'Preferences deleted.', false);
                            fetchAndDisplayVendors(); // Refresh vendor list
                            preferencesForVendorContainer.style.display = 'none'; // Hide specific prefs section
                        } else {
                            throw new Error(result.data.error || 'Failed to delete preferences.');
                        }
                    })
                    .catch(error => {
                        console.error('Error deleting all preferences:', error);
                        showMessage(globalMessagesDiv, `Error: ${error.message}`, true);
                    });
            }
        }
    });

    // Event delegation for specific preferences table actions
    preferencesForVendorContainer.addEventListener('click', function(event) {
        const target = event.target;
        if (target.classList.contains('delete-specific-pref-btn')) {
            const vendorFileId = target.dataset.vendorFileId; // Needed to refresh display
            const originalHeader = target.dataset.originalHeader;
            const vendorDisplayName = target.dataset.vendorDisplayName; // For confirmation and POST body

            if (window.confirm(`Delete preference for header '${originalHeader}' for vendor '${vendorDisplayName}'?`)) {
                fetch('/delete_specific_vendor_preference', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ vendor_name: vendorDisplayName, original_header: originalHeader })
                })
                .then(response => response.json().then(data => ({ ok: response.ok, data })))
                .then(result => {
                    if (result.ok) {
                        showMessage(specificPreferenceMessagesDiv, result.data.message || 'Preference deleted.', false);
                        fetchAndDisplaySpecificPreferences(vendorFileId, vendorDisplayName); // Refresh this vendor's table
                    } else {
                        throw new Error(result.data.error || 'Failed to delete specific preference.');
                    }
                })
                .catch(error => {
                    console.error('Error deleting specific preference:', error);
                    showMessage(specificPreferenceMessagesDiv, `Error: ${error.message}`, true);
                });
            }
        }
    });

    // Initial call to load vendors
    fetchAndDisplayVendors();
});
