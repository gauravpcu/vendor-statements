from flask import Flask, render_template, request, jsonify
import os
import magic
import logging

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit

# --- Logger Setup ---
logger = logging.getLogger('upload_history')
logger.setLevel(logging.INFO)
# Prevent duplicate handlers if app reloads (common in debug mode)
if not logger.handlers:
    fh = logging.FileHandler('upload_history.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
# --- End Logger Setup ---

SUPPORTED_MIME_TYPES = {
    'application/pdf': 'PDF',
    'application/vnd.ms-excel': 'XLS',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'text/csv': 'CSV'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('files[]')
    results = []
    uploaded_file_count = 0

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # First check: total number of files
    if len(files) > 10:
        for file_storage in files: # Iterate over FileStorage objects
            results.append({
                "filename": file_storage.filename if file_storage else "Unknown",
                "success": False,
                "message": "Too many files uploaded (limit is 10). Upload cancelled for all files.",
                "file_type": "N/A"
            })
        return jsonify(results), 400

    # Check if any file is actually submitted
    if not any(file_storage and file_storage.filename for file_storage in files):
        return jsonify([{
            "filename": "N/A",
            "success": False,
            "message": "No files selected or files are empty.",
            "file_type": "N/A"
        }]), 400


    for file_storage in files:
        if file_storage and file_storage.filename: # Ensure file object and filename exist
            filename = file_storage.filename
            file_type = "unknown"
            message = ""
            success = False

            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                # Save before type checking to have access to the content on disk
                # Alternatively, read into a buffer: file_storage.stream.read(FIRST_CHUNK_SIZE)
                # but saving first is simpler if files are definitely going to be saved.
                file_storage.save(file_path)

                # Detect MIME type
                try:
                    mime_type = magic.from_file(file_path, mime=True)
                    detected_type_name = SUPPORTED_MIME_TYPES.get(mime_type)

                    if detected_type_name:
                        file_type = detected_type_name
                        success = True
                        message = "Upload successful."
                        uploaded_file_count += 1
                    else:
                        success = False
                        message = f"Unsupported file type: {mime_type}. Supported types are PDF, XLSX, XLS, CSV."
                        file_type = mime_type # Store the actual detected mime type if unsupported
                        # Optionally, delete the unsupported file: os.remove(file_path)
                except magic.MagicException as me: # Specific exception for python-magic
                    success = False
                    message = "Error detecting file type. The file may be corrupted or in an unreadable format."
                    file_type = "error_detection"
                    # Optionally, delete the problematic file: os.remove(file_path)
                except Exception as e_detect: # Catch other potential errors during detection
                    success = False
                    message = f"Error during file type detection: {str(e_detect)}"
                    file_type = "error_detection_general"

                results.append({
                    "filename": filename,
                    "success": success,
                    "message": message,
                    "file_type": file_type
                })

            except Exception as e_save: # Errors during file.save()
                results.append({
                    "filename": filename,
                    "success": False,
                    "message": f"Error saving file: {str(e_save)}",
                    "file_type": "error_saving"
                })

            # Log the result for this file
            log_message = (
                f"File: {filename}, "
                f"Status: {'Success' if success else 'Failure'}, "
                f"Type: {file_type}, "
                f"Message: {message}"
            )
            logger.info(log_message)

        # This else block might be redundant if using getlist and files always have a filename if present
        # else:
        #     results.append({
        #         "filename": "Unknown",
        #         "success": False,
        #         "message": "No file selected or file is empty.",
        #         "file_type": "N/A"
        #     })

    if uploaded_file_count == 0 and not any(r['success'] for r in results) and len(results) > 0 :
         # If no files were successfully uploaded and there are results, likely all failed some check
        return jsonify(results), 400 # Or 200 if partial success is an option for some files
    elif not results: # Should be caught by the "no files selected" check earlier
        return jsonify([{
            "filename": "N/A",
            "success": False,
            "message": "No files processed.", # Should not happen if files were submitted
            "file_type": "N/A"
        }]), 400


    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
