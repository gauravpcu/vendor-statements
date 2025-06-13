import json
import os
import logging
import sys
import serverless_wsgi

# Set up logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure python-magic to use bundled magic file
# This needs to happen before any imports that use python-magic
try:
    # This will ensure python-magic-bin works correctly in Lambda environment
    if 'magic' not in sys.modules:
        import magic
        # If we're using python-magic-bin, ensure it can find its bundled magic file
        if hasattr(magic, '_magic_file') and not magic._magic_file:
            logger.info("Configuring python-magic-bin for AWS Lambda")
            # Get the directory where the magic module is installed
            magic_dir = os.path.dirname(magic.__file__)
            # Point to the bundled magic file
            magic_file = os.path.join(magic_dir, 'magic.mgc')
            if os.path.exists(magic_file):
                magic.magic_file = magic_file
                logger.info(f"Using magic file: {magic_file}")
except Exception as e:
    logger.error(f"Error configuring python-magic: {str(e)}")

# Import the Flask app
from app import app

# Handler for Lambda
def lambda_handler(event, context):
    """
    This is the main handler for AWS Lambda.
    It uses serverless-wsgi to transform API Gateway events into WSGI requests for the Flask app.
    """
    logger.info("Lambda function invoked")
    
    # Use serverless_wsgi to handle the event
    return serverless_wsgi.handle_request(app, event, context)
