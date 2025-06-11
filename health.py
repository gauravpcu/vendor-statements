"""
Simple standalone health check server for AWS App Runner.
This runs on a separate port (8081) to handle health checks separately from the main application.
"""
import os
import sys
import logging
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('health_check')

# Create a separate Flask app just for health checks
health_app = Flask(__name__)

@health_app.route('/health', methods=['GET'])
def health_check():
    """Minimal health check endpoint for AWS App Runner"""
    logger.info("Health check request received")
    return "", 200

@health_app.route('/', methods=['GET'])
def root():
    """Root endpoint that redirects to health"""
    logger.info("Root request received, redirecting to /health")
    return "", 200

if __name__ == "__main__":
    port = int(os.environ.get('HEALTH_PORT', 8081))
    logger.info(f"Starting health check server on port {port}")
    # Use 0.0.0.0 to listen on all interfaces
    health_app.run(host='0.0.0.0', port=port)
