# Fallback implementation of file type detection when libmagic is not available
# This will be used only if all other methods fail

import os

def detect_mime_type(filepath):
    """
    Detect the MIME type of a file based on its extension.
    This is a very simple fallback for when libmagic is not available.
    """
    ext = os.path.splitext(filepath)[1].lower()
    
    # Common MIME types
    mime_types = {
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.csv': 'text/csv',
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.js': 'application/javascript',
        '.css': 'text/css',
        '.json': 'application/json'
    }
    
    return mime_types.get(ext, 'application/octet-stream')
