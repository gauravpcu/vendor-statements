function displayFilePreview(previewData) {
    // Create preview modal showing extracted text content
    const previewContainer = document.createElement('div');
    previewContainer.className = 'file-preview-modal';
    previewContainer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        `;

    const previewContent = document.createElement('div');
    previewContent.className = 'file-preview-content';
    previewContent.style.cssText = `
            background: white;
            border-radius: 12px;
            max-width: 90%;
            max-height: 90%;
            overflow-y: auto;
            padding: 24px;
            position: relative;
        `;

    // Close button
    const closeButton = document.createElement('button');
    closeButton.innerHTML = '✕';
    closeButton.style.cssText = `
            position: absolute;
            top: 12px;
            right: 12px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #666;
        `;
    closeButton.onclick = () => document.body.removeChild(previewContainer);

    // File info header
    const fileInfo = document.createElement('div');
    fileInfo.innerHTML = `
            <h3 style="margin: 0 0 16px 0; color: #2c3e50;">📄 Parsed Content: ${previewData.filename}</h3>
            <div style="display: flex; gap: 20px; margin-bottom: 20px; font-size: 14px; color: #666;">
                <span>📊 Size: ${formatFileSize(previewData.file_size)}</span>
                <span>📋 Type: ${previewData.file_type}</span>
                <span>📈 Rows: ${previewData.total_rows || 'Unknown'}</span>
                <span>🏷️ Headers: ${previewData.headers ? previewData.headers.length : 0}</span>
            </div>
            <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 6px; padding: 8px 12px; margin-bottom: 20px;">
                <strong>📋 Parsing Status:</strong> ${previewData.parsing_info || 'Content extracted successfully'}
            </div>
        `;

    previewContent.appendChild(closeButton);
    previewContent.appendChild(fileInfo);

    // Main extracted text content
    if (previewData.extracted_text) {
        const textSection = document.createElement('div');
        textSection.innerHTML = `
                <h4 style="color: #2c3e50; margin: 20px 0 10px 0;">📝 Extracted Content</h4>
                <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                    <pre style="
                        font-family: 'Courier New', monospace;
                        font-size: 12px;
                        line-height: 1.4;
                        margin: 0;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        color: #2c3e50;
                        max-height: 400px;
                        overflow-y: auto;
                    ">${previewData.extracted_text}</pre>
                </div>
            `;
        previewContent.appendChild(textSection);
    }

    // Headers section (as badges for quick reference)
    if (previewData.headers && previewData.headers.length > 0) {
        const headersSection = document.createElement('div');
        headersSection.innerHTML = `
                <h4 style="color: #2c3e50; margin: 20px 0 10px 0;">🏷️ Detected Headers (${previewData.headers.length})</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
                    ${previewData.headers.map((header, index) =>
            `<span style="background: #e3f2fd; color: #1976d2; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                            ${index + 1}. ${header}
                        </span>`
        ).join('')}
                </div>
            `;
        previewContent.appendChild(headersSection);
    }

    // Copy to clipboard button
    if (previewData.extracted_text) {
        const copySection = document.createElement('div');
        copySection.style.cssText = `
                text-align: center;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #dee2e6;
            `;

        const copyButton = document.createElement('button');
        copyButton.innerHTML = '📋 Copy Extracted Text';
        copyButton.style.cssText = `
                background: #3b82f6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
            `;

        copyButton.onclick = () => {
            navigator.clipboard.writeText(previewData.extracted_text).then(() => {
                copyButton.innerHTML = '✅ Copied!';
                copyButton.style.background = '#10b981';
                setTimeout(() => {
                    copyButton.innerHTML = '📋 Copy Extracted Text';
                    copyButton.style.background = '#3b82f6';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                copyButton.innerHTML = '❌ Copy Failed';
                copyButton.style.background = '#ef4444';
            });
        };

        copySection.appendChild(copyButton);
        previewContent.appendChild(copySection);
    }

    previewContainer.appendChild(previewContent);
    document.body.appendChild(previewContainer);

    // Close on background click
    previewContainer.addEventListener('click', (e) => {
        if (e.target === previewContainer) {
            document.body.removeChild(previewContainer);
        }
    });
}