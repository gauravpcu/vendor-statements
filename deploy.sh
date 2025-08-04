#!/bin/bash
# Quick deployment script for Vendor Statements Processor

set -e

EC2_IP="44.198.169.216"
KEY_PATH="~/.ssh/vendor-statements-key.pem"
CONTAINER="vendor-statements-app"

echo "🚀 Starting deployment to EC2..."

# Function to deploy a file
deploy_file() {
    local_file=$1
    remote_path=$2
    
    if [ ! -f "$local_file" ]; then
        echo "❌ File $local_file not found, skipping..."
        return
    fi
    
    echo "📤 Deploying $local_file..."
    scp -o StrictHostKeyChecking=no -i $KEY_PATH $local_file ec2-user@$EC2_IP:/tmp/$(basename $local_file)
    ssh -o StrictHostKeyChecking=no -i $KEY_PATH ec2-user@$EC2_IP "sudo docker cp /tmp/$(basename $local_file) $CONTAINER:$remote_path"
    echo "✅ $local_file deployed successfully"
}

# Function to restart container
restart_container() {
    echo "🔄 Restarting Docker container..."
    ssh -o StrictHostKeyChecking=no -i $KEY_PATH ec2-user@$EC2_IP "sudo docker restart $CONTAINER"
    echo "✅ Container restarted"
    
    echo "⏳ Waiting for application to start..."
    sleep 15
    
    # Test health
    if curl -s -f "http://$EC2_IP:8000/" > /dev/null; then
        echo "✅ Application is healthy and running!"
    else
        echo "⚠️  Application might still be starting up..."
    fi
}

# Parse command line arguments
RESTART_NEEDED=false
DEPLOYMENT_DONE=false

# If no arguments provided, show usage
if [ $# -eq 0 ]; then
    echo "❓ No deployment options specified."
    echo "Usage: $0 [--all|--templates|--js|--css|--backend] [--restart]"
    echo ""
    echo "Quick options:"
    echo "  $0 --all        # Deploy everything"
    echo "  $0 --templates  # Deploy only templates (most common)"
    exit 1
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            echo "📦 Deploying all files..."
            deploy_file "templates/index.html" "/app/templates/index.html"
            deploy_file "templates/manage_templates.html" "/app/templates/manage_templates.html"
            deploy_file "static/js/upload.js" "/app/static/js/upload.js"
            deploy_file "static/js/file-viewer.js" "/app/static/js/file-viewer.js"
            deploy_file "static/js/manage_templates.js" "/app/static/js/manage_templates.js"
            deploy_file "static/css/modern-ui.css" "/app/static/css/modern-ui.css"
            DEPLOYMENT_DONE=true
            shift
            ;;
        --templates)
            echo "📄 Deploying template files..."
            deploy_file "templates/index.html" "/app/templates/index.html"
            deploy_file "templates/manage_templates.html" "/app/templates/manage_templates.html"
            DEPLOYMENT_DONE=true
            shift
            ;;
        --js)
            echo "📜 Deploying JavaScript files..."
            deploy_file "static/js/upload.js" "/app/static/js/upload.js"
            deploy_file "static/js/file-viewer.js" "/app/static/js/file-viewer.js"
            deploy_file "static/js/manage_templates.js" "/app/static/js/manage_templates.js"
            DEPLOYMENT_DONE=true
            shift
            ;;
        --css)
            echo "🎨 Deploying CSS files..."
            deploy_file "static/css/modern-ui.css" "/app/static/css/modern-ui.css"
            DEPLOYMENT_DONE=true
            shift
            ;;
        --backend)
            echo "🐍 Deploying backend files..."
            deploy_file "app.py" "/app/app.py"
            RESTART_NEEDED=true
            DEPLOYMENT_DONE=true
            shift
            ;;
        --restart)
            RESTART_NEEDED=true
            shift
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Usage: $0 [--all|--templates|--js|--css|--backend] [--restart]"
            exit 1
            ;;
    esac
done

# Restart container if needed
if [ "$RESTART_NEEDED" = true ]; then
    restart_container
fi

# Show completion message if deployment was done
if [ "$DEPLOYMENT_DONE" = true ]; then
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo "🌐 Application URL: http://$EC2_IP:8000"
    echo "📋 Template Management: http://$EC2_IP:8000/manage_templates"
    echo ""
    echo "💡 If changes aren't visible, try clearing your browser cache (Ctrl+F5)"
fi