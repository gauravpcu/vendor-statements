# Vendor Statements Processor - Deployment Guide

## 🚀 EC2 Deployment Instructions

This guide provides step-by-step instructions for deploying changes to the EC2 instance running the Vendor Statements Processor application.

### 📋 Prerequisites

- SSH key file: `~/.ssh/vendor-statements-key.pem`
- EC2 instance IP: `44.198.169.216`
- Docker container name: `vendor-statements-app`

### 🔧 Common Deployment Commands

#### 1. Deploy Static Files (CSS, JS)

```bash
# Upload CSS files
scp -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem static/css/modern-ui.css ec2-user@44.198.169.216:/tmp/modern-ui.css
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker cp /tmp/modern-ui.css vendor-statements-app:/app/static/css/modern-ui.css'

# Upload JavaScript files
scp -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem static/js/upload.js ec2-user@44.198.169.216:/tmp/upload.js
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker cp /tmp/upload.js vendor-statements-app:/app/static/js/upload.js'

# Upload file viewer
scp -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem static/js/file-viewer.js ec2-user@44.198.169.216:/tmp/file-viewer.js
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker cp /tmp/file-viewer.js vendor-statements-app:/app/static/js/file-viewer.js'

# Upload template management
scp -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem static/js/manage_templates.js ec2-user@44.198.169.216:/tmp/manage_templates.js
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker cp /tmp/manage_templates.js vendor-statements-app:/app/static/js/manage_templates.js'
```

#### 2. Deploy Templates (HTML)

```bash
# Upload main index page
scp -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem templates/index.html ec2-user@44.198.169.216:/tmp/index.html
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker cp /tmp/index.html vendor-statements-app:/app/templates/index.html'

# Upload template management page
scp -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem templates/manage_templates.html ec2-user@44.198.169.216:/tmp/manage_templates.html
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker cp /tmp/manage_templates.html vendor-statements-app:/app/templates/manage_templates.html'
```

#### 3. Deploy Backend Changes (Python)

```bash
# Upload main application file (requires container restart)
scp -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem app.py ec2-user@44.198.169.216:/tmp/app.py
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker cp /tmp/app.py vendor-statements-app:/app/app.py'

# Restart container after Python changes
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker restart vendor-statements-app'
```

### 🔄 Container Management

#### Restart Docker Container
```bash
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker restart vendor-statements-app'
```

#### Check Container Status
```bash
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker ps'
```

#### View Container Logs
```bash
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker logs vendor-statements-app --tail 50'
```

#### Check Application Health
```bash
curl -s -I "http://44.198.169.216:8000/" | head -3
curl -s "http://44.198.169.216:8000/health"
```

### 📁 File Structure on EC2

```
/app/
├── app.py                          # Main Flask application
├── templates/
│   ├── index.html                  # Main upload page
│   └── manage_templates.html       # Template management page
├── static/
│   ├── css/
│   │   └── modern-ui.css          # Main stylesheet
│   └── js/
│       ├── upload.js              # File upload functionality
│       ├── file-viewer.js         # File preview functionality
│       ├── manage_templates.js    # Template management
│       └── chatbot.js            # Chatbot functionality
└── storage/                       # Local file storage
```

### 🚨 When to Restart Container

**Restart Required:**
- Changes to `app.py` (Python backend)
- Changes to configuration files
- Environment variable updates
- New Python dependencies

**No Restart Needed:**
- Static files (CSS, JS)
- Template files (HTML)
- Client-side only changes

### 🔍 Troubleshooting

#### Check if files were deployed correctly
```bash
# Verify file exists and check timestamp
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker exec vendor-statements-app ls -la /app/templates/index.html'

# Check file content
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker exec vendor-statements-app cat /app/templates/index.html | grep -A 5 -B 5 "specific-content"'
```

#### Clear browser cache
If changes aren't visible:
- Hard refresh: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
- Clear browser cache: `Ctrl+Shift+Delete`
- Try incognito/private browsing window

#### Container not responding
```bash
# Check container status
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker ps -a'

# Restart if needed
ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@44.198.169.216 'sudo docker restart vendor-statements-app'

# Wait for startup and test
sleep 15 && curl -s -I "http://44.198.169.216:8000/"
```

### 📝 Quick Deployment Script

Create a local script `deploy.sh` for common deployments:

```bash
#!/bin/bash
# Quick deployment script

EC2_IP="44.198.169.216"
KEY_PATH="~/.ssh/vendor-statements-key.pem"
CONTAINER="vendor-statements-app"

# Function to deploy a file
deploy_file() {
    local_file=$1
    remote_path=$2
    
    echo "Deploying $local_file..."
    scp -o StrictHostKeyChecking=no -i $KEY_PATH $local_file ec2-user@$EC2_IP:/tmp/$(basename $local_file)
    ssh -o StrictHostKeyChecking=no -i $KEY_PATH ec2-user@$EC2_IP "sudo docker cp /tmp/$(basename $local_file) $CONTAINER:$remote_path"
    echo "✅ $local_file deployed"
}

# Deploy common files
deploy_file "templates/index.html" "/app/templates/index.html"
deploy_file "static/js/upload.js" "/app/static/js/upload.js"
deploy_file "static/css/modern-ui.css" "/app/static/css/modern-ui.css"

echo "🎉 Deployment complete!"
```

### 🌐 Application URLs

- **Main Application**: http://44.198.169.216:8000
- **Template Management**: http://44.198.169.216:8000/manage_templates
- **Health Check**: http://44.198.169.216:8000/health

### 📊 Current Application Features

- ✅ File upload with drag-and-drop support
- ✅ PDF, Excel, and CSV file processing
- ✅ Template management (Create, Read, Update, Delete)
- ✅ AI-powered header mapping
- ✅ File preview with line numbers
- ✅ Smart line numbering for skip rows configuration
- ✅ Responsive UI with modern design

---

## 🔧 Development Workflow

1. **Make changes** locally in your IDE
2. **Test changes** locally if possible
3. **Deploy files** using the commands above
4. **Restart container** if needed (Python changes)
5. **Test on production** at http://44.198.169.216:8000
6. **Clear browser cache** if changes aren't visible

---

*Last updated: August 4, 2025*