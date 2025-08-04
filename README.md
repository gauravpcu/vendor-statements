# 📊 Vendor Statements Processor

A modern, intelligent web application for processing vendor statements with automatic template matching and AI-powered field mapping. Deployed on AWS EC2 with Docker for production reliability.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![AWS](https://img.shields.io/badge/AWS-EC2-orange.svg)
![Docker](https://img.shields.io/badge/Docker-enabled-blue.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- 🚀 **Modern UI**: Clean, responsive interface with drag-and-drop file upload
- 🤖 **Smart Templates**: Automatic vendor detection and template application
- 📋 **Intelligent Mapping**: AI-powered field mapping with confidence scoring
- 📁 **Multi-format Support**: PDF, Excel (.xlsx, .xls), and CSV files
- 💾 **Template Management**: Create, edit, and manage reusable templates
- 🔄 **Real-time Processing**: Live progress tracking and status updates
- 📱 **Responsive Design**: Works seamlessly on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed locally (for building images)
- SSH key pair for EC2 access
- Azure OpenAI service configured

### EC2 Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/gauravpcu/vendor-statements.git
   cd vendor-statements
   ```

2. **Configure deployment**
   ```bash
   ./setup-ec2-deployment.sh
   ```

3. **Deploy to EC2**
   ```bash
   ./deploy-ec2.sh
   ```

4. **Manage your deployment**
   ```bash
   ./ec2-management.sh status
   ```

### Local Development

1. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.template .env
   # Edit .env with your configuration
   ```

4. **Run locally**
   ```bash
   python app.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:8000`

## 🏗️ Deployment

### Production EC2 Deployment

This application is designed for production deployment on AWS EC2 with Docker containers.

**Quick Deployment:**
```bash
./setup-ec2-deployment.sh  # Interactive setup
./deploy-ec2.sh           # Deploy to EC2
```

**Management Commands:**
```bash
./ec2-management.sh status    # Check deployment status
./ec2-management.sh logs      # View application logs
./ec2-management.sh update    # Update to latest version
./ec2-management.sh ssh       # SSH to EC2 instance
```

**For detailed deployment instructions, see:**
- [EC2 Deployment Guide](README-EC2-DEPLOYMENT.md) - Comprehensive deployment documentation
- [Console Setup Guide](ec2-console-setup-guide.md) - Manual AWS console setup

### Architecture

```
Internet → Security Group → EC2 Instance → Docker Container (Flask App)
                                ↓
                           EBS Volume (persistent storage)
                                ↓
                           S3 Bucket (file storage)
```

## 📖 Usage

### Basic Workflow

1. **Upload Files**: Drag and drop or click to select vendor statement files
2. **Auto-Processing**: The system automatically detects file types and applies matching templates
3. **Review Mappings**: Verify and adjust field mappings as needed
4. **Process Data**: Extract structured data from your statements
5. **Download Results**: Export processed data as Excel with standardized columns

### Template Management

- **Automatic Templates**: Files named with vendor prefixes (e.g., `Acme_Statement_2024.xlsx`) automatically apply matching templates
- **Manual Selection**: Choose templates from the dropdown for any file
- **Create Templates**: Save successful mappings as reusable templates
- **Template Library**: Manage your template collection from the Templates page

## 🏗️ Architecture

### Backend (Flask)
- **app.py**: Main Flask application
- **file_parser.py**: File processing and header extraction
- **header_mapper.py**: Intelligent field mapping
- **template system**: Automatic vendor detection and application

### Frontend (Modern UI)
- **modern-ui.css**: Responsive CSS framework
- **modern-upload.js**: Enhanced user experience
- **Real-time updates**: Progress tracking and notifications

### Data Flow
```
File Upload → Type Detection → Template Matching → Header Extraction → Field Mapping → Data Processing → Export
```

## 📁 Project Structure

```
vendor-statements/
├── 📁 docs/                    # Documentation
├── 📁 static/                  # Frontend assets
│   ├── 📁 css/                # Stylesheets
│   └── 📁 js/                 # JavaScript files
├── 📁 templates/               # HTML templates
├── 📁 templates_storage/       # Saved templates
├── 📁 uploads/                 # Uploaded files
├── 📁 tests/                   # Test files
├── 📄 app.py                   # Main Flask app
├── 📄 requirements.txt         # Dependencies
└── 📄 field_definitions.json   # Field mappings
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# Azure OpenAI (optional, for AI features)
AZURE_OAI_ENDPOINT=your_endpoint
AZURE_OAI_KEY=your_key
AZURE_OAI_DEPLOYMENT_NAME=your_deployment

# External API (optional)
INVOICE_VALIDATION_API_URL=your_api_url
INVOICE_VALIDATION_API_KEY=your_api_key
```

### Field Definitions

Edit `field_definitions.json` to customize available field mappings:

```json
{
  "InvoiceID": {
    "display_name": "Invoice ID",
    "description": "Unique invoice identifier"
  },
  "VendorName": {
    "display_name": "Vendor Name",
    "description": "Name of the vendor"
  }
}
```

## 🧪 Testing

Run the test suite:

```bash
python tests/test_template_functionality.py
```

## 🚀 Deployment

### Development
```bash
python app.py
```

### Production
```bash
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

### Docker
```bash
docker build -t vendor-statements .
docker run -p 8080:8080 vendor-statements
```

## 📚 Documentation

- [Template Usage Guide](docs/TEMPLATE_USAGE.md)
- [Implementation Details](docs/TEMPLATE_IMPLEMENTATION_SUMMARY.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Testing Results](docs/TESTING_RESULTS.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/vendor-statements/issues)
- 📖 Documentation: [docs/](docs/)

## 🎉 Acknowledgments

- Built with Flask and modern web technologies
- UI inspired by modern design principles
- Template system designed for real-world vendor statement processing

---

**Made with ❤️ for efficient vendor statement processing**