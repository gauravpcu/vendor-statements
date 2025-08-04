/**
 * Comprehensive File Viewer for XLS, XLSX, CSV, and PDF files
 * Integrates with the existing upload system
 */

class FileViewer {
    constructor() {
        this.currentModal = null;
        this.initializePDFJS();
    }

    initializePDFJS() {
        // Configure PDF.js worker
        if (typeof pdfjsLib !== 'undefined') {
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        }
    }

    /**
     * Main method to view a file
     * @param {string} filename - The filename to view
     * @param {string} fileType - The file type (CSV, XLSX, XLS, PDF)
     */
    async viewFile(filename, fileType) {
        console.log(`[FileViewer] Opening file: ${filename}, type: ${fileType}`);

        try {
            this.showLoadingModal(filename);

            // Check if this is a converted file that should show the original PDF
            if (this.isConvertedFile(filename, fileType)) {
                console.log(`[FileViewer] Detected converted file, showing original PDF instead`);
                await this.viewOriginalPDF(filename);
                return;
            }

            switch (fileType.toUpperCase()) {
                case 'CSV':
                    await this.viewCSV(filename);
                    break;
                case 'XLSX':
                case 'XLS':
                    await this.viewSpreadsheet(filename);
                    break;
                case 'PDF':
                    await this.viewPDF(filename);
                    break;
                default:
                    throw new Error(`Unsupported file type: ${fileType}`);
            }
        } catch (error) {
            console.error('[FileViewer] Error viewing file:', error);
            this.showErrorModal(filename, error.message);
        }
    }

    /**
     * Check if this is a converted file (PDF converted to CSV)
     * @param {string} filename - The filename to check
     * @param {string} fileType - The reported file type
     */
    isConvertedFile(filename, fileType) {
        // If it's a CSV file that ends with "-converted.csv", it's likely a converted PDF
        return fileType.toUpperCase() === 'CSV' && filename.endsWith('-converted.csv');
    }

    /**
     * View the original PDF file for a converted CSV
     * @param {string} convertedFilename - The converted CSV filename
     */
    async viewOriginalPDF(convertedFilename) {
        // Extract the base name and try to find the original PDF
        const baseName = convertedFilename.replace('-converted.csv', '');
        const originalPDFName = baseName + '.pdf';

        console.log(`[FileViewer] Looking for original PDF: ${originalPDFName}`);

        try {
            // Try to load the original PDF
            const response = await fetch(`/view_uploaded_file/${encodeURIComponent(originalPDFName)}`);
            if (!response.ok) {
                // If original PDF not found, fall back to showing the CSV
                console.log(`[FileViewer] Original PDF not found, falling back to CSV view`);
                await this.viewCSV(convertedFilename);
                return;
            }

            const arrayBuffer = await response.arrayBuffer();
            const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

            // Show the PDF with a note that it's the original
            this.showPDFModal(originalPDFName, pdf, `Original PDF (converted file: ${convertedFilename})`);

        } catch (error) {
            console.log(`[FileViewer] Error loading original PDF, falling back to CSV:`, error);
            // Fallback to showing the CSV if PDF loading fails
            await this.viewCSV(convertedFilename);
        }
    }

    /**
     * View CSV files
     */
    async viewCSV(filename) {
        try {
            const response = await fetch(`/view_uploaded_file/${encodeURIComponent(filename)}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

            const csvText = await response.text();
            const lines = csvText.split('\n');

            // Try to parse as structured data first
            try {
                const workbook = XLSX.read(csvText, { type: 'string' });
                const worksheet = workbook.Sheets[workbook.SheetNames[0]];
                const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

                if (jsonData.length > 0) {
                    this.showSpreadsheetModal(filename, jsonData, 'CSV');
                    return;
                }
            } catch (parseError) {
                console.log('[FileViewer] CSV structured parsing failed, showing raw content');
            }

            // Fallback to raw text display
            this.showRawTextModal(filename, csvText, 'CSV');

        } catch (error) {
            throw new Error(`Failed to load CSV file: ${error.message}`);
        }
    }

    /**
     * View Excel files (XLSX, XLS)
     */
    async viewSpreadsheet(filename) {
        try {
            const response = await fetch(`/view_uploaded_file/${encodeURIComponent(filename)}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

            const arrayBuffer = await response.arrayBuffer();
            const workbook = XLSX.read(arrayBuffer, { type: 'array' });

            // Get the first worksheet
            const worksheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[worksheetName];
            const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

            this.showSpreadsheetModal(filename, jsonData, 'Excel', workbook.SheetNames);

        } catch (error) {
            throw new Error(`Failed to load Excel file: ${error.message}`);
        }
    }

    /**
     * View PDF files
     */
    async viewPDF(filename) {
        try {
            const response = await fetch(`/view_uploaded_file/${encodeURIComponent(filename)}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

            const arrayBuffer = await response.arrayBuffer();
            const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

            this.showPDFModal(filename, pdf);

        } catch (error) {
            throw new Error(`Failed to load PDF file: ${error.message}`);
        }
    }

    /**
     * Show spreadsheet data in a modal
     */
    showSpreadsheetModal(filename, data, fileType, sheetNames = null) {
        const modal = this.createModal(filename, fileType);

        let content = '';

        // Add sheet selector if multiple sheets
        if (sheetNames && sheetNames.length > 1) {
            content += `
                <div class="file-viewer-controls">
                    <label>Sheet: </label>
                    <select id="sheetSelector" onchange="fileViewer.switchSheet('${filename}', this.value)">
                        ${sheetNames.map((name, index) =>
                `<option value="${index}" ${index === 0 ? 'selected' : ''}>${name}</option>`
            ).join('')}
                    </select>
                </div>
            `;
        }

        // Create table
        if (data.length > 0) {
            content += '<div style="overflow: auto; max-height: 60vh;">';
            content += '<table class="spreadsheet-viewer">';

            // Check if first row has data (indicates header row exists)
            const hasHeaderRow = data[0] && data[0].some(cell => cell !== null && cell !== undefined && cell !== '');

            // Headers
            if (data[0]) {
                content += '<thead><tr>';
                // Add line number header - show "1" if header exists, otherwise show row number
                const headerRowNumber = hasHeaderRow ? '1' : '';
                content += `<th style="background: #e9ecef; font-weight: bold; text-align: center; min-width: 40px;">${headerRowNumber}</th>`;
                data[0].forEach((cell, index) => {
                    content += `<th>Col ${String.fromCharCode(65 + index)}: ${this.escapeHtml(cell || '')}</th>`;
                });
                content += '</tr></thead>';
            }

            // Data rows (limit to first 100 rows for performance)
            content += '<tbody>';
            const maxRows = Math.min(data.length, 100);
            for (let i = 1; i < maxRows; i++) {
                if (data[i]) {
                    content += '<tr>';
                    // Add line number cell - start from 1 if no header, or from 2 if header exists
                    const rowNumber = hasHeaderRow ? i + 1 : i;
                    content += `<td style="background: #e9ecef; font-weight: bold; text-align: center; min-width: 40px; color: #495057;">${rowNumber}</td>`;
                    const maxCols = Math.max(data[0]?.length || 0, data[i].length);
                    for (let j = 0; j < maxCols; j++) {
                        content += `<td>${this.escapeHtml(data[i][j] || '')}</td>`;
                    }
                    content += '</tr>';
                }
            }
            content += '</tbody>';
            content += '</table>';
            content += '</div>';

            if (data.length > 100) {
                content += `<p style="text-align: center; color: #666; margin-top: 10px;">
                    Showing first 100 rows of ${data.length} total rows
                </p>`;
            }
        } else {
            content += '<div class="viewer-error">No data found in the file</div>';
        }

        modal.querySelector('.file-viewer-body').innerHTML = content;
        this.showModal(modal);
    }

    /**
     * Show PDF in a modal
     */
    async showPDFModal(filename, pdf, subtitle = null) {
        const modal = this.createModal(filename, 'PDF', subtitle);
        const container = modal.querySelector('.file-viewer-body');

        container.innerHTML = `
            <div class="file-viewer-controls">
                <span>Pages: ${pdf.numPages}</span>
                <button onclick="fileViewer.zoomPDF(0.8)" class="btn btn-sm btn-secondary">Zoom Out</button>
                <button onclick="fileViewer.zoomPDF(1.2)" class="btn btn-sm btn-secondary">Zoom In</button>
            </div>
            <div class="pdf-viewer-container" id="pdfContainer">
                <div class="viewer-loading">Loading PDF pages...</div>
            </div>
        `;

        this.showModal(modal);

        // Render PDF pages
        const pdfContainer = document.getElementById('pdfContainer');
        pdfContainer.innerHTML = '';

        // Render first 3 pages initially for performance
        const maxPages = Math.min(pdf.numPages, 3);
        for (let pageNum = 1; pageNum <= maxPages; pageNum++) {
            const page = await pdf.getPage(pageNum);
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');

            const viewport = page.getViewport({ scale: 1.2 });
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            canvas.className = 'pdf-page';

            await page.render({ canvasContext: context, viewport: viewport }).promise;
            pdfContainer.appendChild(canvas);
        }

        if (pdf.numPages > 3) {
            const moreInfo = document.createElement('div');
            moreInfo.innerHTML = `<p style="text-align: center; color: #666; margin: 20px;">
                Showing first 3 pages of ${pdf.numPages} total pages. 
                <a href="/view_uploaded_file/${encodeURIComponent(filename)}" target="_blank">Open full PDF</a>
            </p>`;
            pdfContainer.appendChild(moreInfo);
        }
    }

    /**
     * Show raw text content
     */
    showRawTextModal(filename, content, fileType) {
        const modal = this.createModal(filename, fileType);

        const lines = content.split('\n');
        const displayLines = lines.slice(0, 100); // Show first 100 lines

        modal.querySelector('.file-viewer-body').innerHTML = `
            <div class="csv-viewer">${this.escapeHtml(displayLines.join('\n'))}</div>
            ${lines.length > 100 ? `<p style="text-align: center; color: #666; margin-top: 10px;">
                Showing first 100 lines of ${lines.length} total lines
            </p>` : ''}
        `;

        this.showModal(modal);
    }

    /**
     * Create modal structure
     */
    createModal(filename, fileType, subtitle = null) {
        const modal = document.createElement('div');
        modal.className = 'file-viewer-modal';

        const subtitleHtml = subtitle ? `<p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">${this.escapeHtml(subtitle)}</p>` : '';

        modal.innerHTML = `
            <div class="file-viewer-content">
                <div class="file-viewer-header">
                    <div style="flex: 1;">
                        <h3 style="margin: 0;">📄 ${this.escapeHtml(filename)} (${fileType})</h3>
                        ${subtitleHtml}
                    </div>
                    <button class="file-viewer-close" onclick="fileViewer.closeModal()">&times;</button>
                </div>
                <div class="file-viewer-body">
                    <div class="viewer-loading">Loading file...</div>
                </div>
                <div class="file-viewer-controls">
                    <a href="/view_uploaded_file/${encodeURIComponent(filename)}" target="_blank" class="btn btn-primary btn-sm">
                        📥 Download/Open Original
                    </a>
                    <button onclick="fileViewer.closeModal()" class="btn btn-secondary btn-sm">Close</button>
                </div>
            </div>
        `;

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal();
            }
        });

        return modal;
    }

    /**
     * Show loading modal
     */
    showLoadingModal(filename) {
        const modal = this.createModal(filename, 'Loading...');
        this.showModal(modal);
    }

    /**
     * Show error modal
     */
    showErrorModal(filename, errorMessage) {
        const modal = this.createModal(filename, 'Error');
        modal.querySelector('.file-viewer-body').innerHTML = `
            <div class="viewer-error">
                <h4>Error loading file</h4>
                <p>${this.escapeHtml(errorMessage)}</p>
                <p>Try using the "Download/Open Original" button below.</p>
            </div>
        `;
        this.showModal(modal);
    }

    /**
     * Show modal
     */
    showModal(modal) {
        this.closeModal(); // Close any existing modal
        this.currentModal = modal;
        document.body.appendChild(modal);
    }

    /**
     * Close current modal
     */
    closeModal() {
        if (this.currentModal) {
            document.body.removeChild(this.currentModal);
            this.currentModal = null;
        }
    }

    /**
     * Utility function to escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * PDF zoom functionality
     */
    zoomPDF(factor) {
        const pdfPages = document.querySelectorAll('.pdf-page');
        pdfPages.forEach(canvas => {
            const currentWidth = canvas.style.width || canvas.width + 'px';
            const newWidth = parseInt(currentWidth) * factor;
            canvas.style.width = newWidth + 'px';
        });
    }
}

// Initialize global file viewer
window.fileViewer = new FileViewer();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FileViewer;
}