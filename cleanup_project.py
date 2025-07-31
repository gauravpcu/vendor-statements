#!/usr/bin/env python3
"""
Project cleanup script to remove unnecessary files and organize the structure.
"""

import os
import shutil
import json

def cleanup_project():
    """Clean up unnecessary files and organize project structure."""
    
    print("🧹 Starting project cleanup...")
    
    # Files and directories to remove
    files_to_remove = [
        # Duplicate/unused CSS files
        'static/css/save_template_dialog.css',
        'static/css/template_button.css',
        
        # Test files (keep the main ones, remove redundant)
        'test_api_endpoints.py',
        'test_frontend_functionality.py',
        
        # Redundant frontend directory (we're using the main Flask app)
        'frontend/',
        
        # Scratch directory
        'scratch/',
        
        # AWS SAM build artifacts
        '.aws-sam/',
        
        # Logs directory (will be recreated as needed)
        'logs/',
        
        # Cache files
        '__pycache__/',
        
        # Redundant shell scripts
        'start_api.sh',
        'start_fullstack.sh',
        'update_frontend_config.sh',
        'build.sh',
        
        # Redundant documentation
        'README_AZURE_OAI_CONFIG.md',
        'README_LAMBDA_DEPLOYMENT.md',
        'LAMBDA_DEPLOYMENT.md',
    ]
    
    # Directories to create if they don't exist
    directories_to_create = [
        'docs/',
        'tests/',
        'config/',
    ]
    
    removed_count = 0
    
    # Remove unnecessary files
    for item in files_to_remove:
        if os.path.exists(item):
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    print(f"  ✅ Removed directory: {item}")
                else:
                    os.remove(item)
                    print(f"  ✅ Removed file: {item}")
                removed_count += 1
            except Exception as e:
                print(f"  ❌ Failed to remove {item}: {e}")
    
    # Create necessary directories
    for directory in directories_to_create:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"  ✅ Created directory: {directory}")
    
    # Move documentation files to docs/
    doc_files = [
        'TEMPLATE_USAGE.md',
        'TEMPLATE_IMPLEMENTATION_SUMMARY.md',
        'TESTING_RESULTS.md',
        'README.md'
    ]
    
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            dest_path = f"docs/{doc_file}"
            if not os.path.exists(dest_path):
                shutil.move(doc_file, dest_path)
                print(f"  ✅ Moved {doc_file} to docs/")
    
    # Move test file to tests/
    if os.path.exists('test_template_functionality.py'):
        dest_path = "tests/test_template_functionality.py"
        if not os.path.exists(dest_path):
            shutil.move('test_template_functionality.py', dest_path)
            print(f"  ✅ Moved test_template_functionality.py to tests/")
    
    # Create a proper project structure documentation
    create_project_structure_doc()
    
    print(f"\n🎉 Cleanup complete! Removed {removed_count} items.")
    print("📁 Project is now better organized with:")
    print("   - docs/ for documentation")
    print("   - tests/ for test files")
    print("   - config/ for configuration files")
    print("   - Removed redundant files and directories")

def create_project_structure_doc():
    """Create documentation about the project structure."""
    
    structure_doc = """# Project Structure

## 📁 Directory Overview

```
vendor-statements/
├── 📁 docs/                    # Documentation files
│   ├── README.md
│   ├── TEMPLATE_USAGE.md
│   └── TEMPLATE_IMPLEMENTATION_SUMMARY.md
├── 📁 static/                  # Frontend assets
│   ├── 📁 css/
│   │   ├── modern-ui.css      # Modern UI framework
│   │   └── style.css          # Legacy styles (for compatibility)
│   └── 📁 js/
│       ├── modern-upload.js   # Modern upload functionality
│       ├── upload.js          # Legacy upload (backup)
│       ├── manage_templates.js
│       └── chatbot.js
├── 📁 templates/               # HTML templates
│   ├── index.html             # Main upload page
│   ├── manage_templates.html  # Template management
│   └── manage_preferences.html
├── 📁 templates_storage/       # Saved templates
├── 📁 uploads/                 # Uploaded files
├── 📁 tests/                   # Test files
├── 📁 config/                  # Configuration files
├── 📄 app.py                   # Main Flask application
├── 📄 fastapi_app.py          # FastAPI version
└── 📄 requirements.txt        # Python dependencies
```

## 🚀 Key Files

### Backend
- **app.py**: Main Flask application with all routes
- **fastapi_app.py**: FastAPI version for API-only usage
- **file_parser.py**: File parsing and header extraction
- **header_mapper.py**: Intelligent field mapping
- **chatbot_service.py**: AI-powered assistance

### Frontend
- **static/css/modern-ui.css**: Modern, responsive UI framework
- **static/js/modern-upload.js**: Enhanced upload experience
- **templates/index.html**: Main application interface

### Configuration
- **field_definitions.json**: Available field mappings
- **requirements.txt**: Python dependencies
- **.env**: Environment variables (create from .env.example)

## 🎯 Usage

1. **Development**: `python app.py`
2. **Production**: Use gunicorn or similar WSGI server
3. **API Only**: Use `fastapi_app.py` with uvicorn

## 🧪 Testing

Run tests from the `tests/` directory:
```bash
python tests/test_template_functionality.py
```
"""
    
    with open('docs/PROJECT_STRUCTURE.md', 'w') as f:
        f.write(structure_doc)
    
    print("  ✅ Created docs/PROJECT_STRUCTURE.md")

if __name__ == "__main__":
    cleanup_project()