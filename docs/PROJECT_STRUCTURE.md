# Project Structure

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
