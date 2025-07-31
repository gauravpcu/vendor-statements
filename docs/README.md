# Vendor Statements Processing System

This system processes vendor statements from various formats (PDF, CSV, Excel) and standardizes the data for analysis.

## Architecture

The application is split into two components:

1. **Backend API** (FastAPI): Handles file processing, data extraction, and AI-based header mapping
2. **Frontend UI** (Node.js/Express): Provides the user interface and communicates with the backend API

## Backend (FastAPI)

The backend is built with FastAPI and provides the core functionality:

- File upload and processing
- Data extraction from PDFs, CSVs, and Excel files
- AI-powered header mapping using Azure OpenAI
- Template management for consistent mapping
- Data validation

### API Documentation

When running, the API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Frontend (Node.js)

The frontend is built with Node.js and Express, serving a web interface that communicates with the backend API:

- File upload interface
- Header mapping UI
- Template management
- Chatbot assistant for mapping help
- Data preview and download

## Setup and Running

### Prerequisites

- Python 3.10+
- Node.js 14+
- Azure OpenAI service (optional, for AI features)

### Installation

1. Install backend dependencies:
```bash
pip install -r requirements.txt
```

2. Install frontend dependencies:
```bash
cd frontend
npm install
```

### Running the Application

Use the provided script to start both applications:

```bash
./start_fullstack.sh
```

This will start:
- Backend API on http://localhost:8000
- Frontend UI on http://localhost:3000

### Running Components Separately

**Backend Only:**
```bash
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend Only:**
```bash
cd frontend
node server.js
```

## Docker Support

Build and run with Docker:

```bash
docker build -t vendor-statements .
docker run -p 8000:8000 vendor-statements
```

## Configuration

- Backend: Environment variables for Azure OpenAI integration
- Frontend: `.env` file in the frontend directory
