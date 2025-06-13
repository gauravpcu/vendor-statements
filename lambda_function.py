import json
import os
import logging
import sys
import serverless_wsgi

# Set up logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure python-magic to work in Lambda environment
# Multiple fallback strategies for handling libmagic in Lambda
try:
    logger.info("Setting up MAGIC environment for AWS Lambda")
    
    # Strategy 1: Try to use python-magic-bin-linux if it's installed
    try:
        import magic_bin_linux
        if hasattr(magic_bin_linux, 'find_library'):
            magic_lib_path = magic_bin_linux.find_library()
            if magic_lib_path:
                os.environ["MAGIC"] = magic_lib_path
                logger.info(f"Using magic library from python-magic-bin-linux: {magic_lib_path}")
    except ImportError:
        logger.info("python-magic-bin-linux not available, trying alternative strategies")
    
    # Strategy 2: Look for magic file in various locations
    possible_magic_file_paths = [
        '/var/task/magic.mgc',  # Lambda package root
        '/var/task/libmagic_fallback/magic.mgc',  # Our fallback directory
        '/opt/python/magic.mgc',  # Lambda layer
        '/opt/magic.mgc',  # Lambda layer root
        '/var/task/magic',  # Try without extension
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'magic.mgc')  # Same dir as lambda_function
    ]
    
    for path in possible_magic_file_paths:
        if os.path.exists(path):
            os.environ["MAGIC"] = path
            logger.info(f"Found magic file at: {path}")
            break
    
    # Now import magic, which will use the environment settings
    import magic
    logger.info(f"Successfully imported magic module: {magic.__file__}")
    
except Exception as e:
    logger.error(f"Error configuring python-magic: {str(e)}")
    
    # Strategy 3: Mock the magic module as a last resort
    if 'magic' not in sys.modules:
        logger.warning("Creating a mock magic module as fallback")
        
        class MockMagicException(Exception):
            pass
        
        class MockMagic:
            def from_file(self, filename, mime=False):
                # Basic MIME type detection based on file extension
                if mime:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in ['.xlsx', '.xls']: return 'application/vnd.ms-excel'
                    if ext in ['.csv']: return 'text/csv'
                    if ext in ['.pdf']: return 'application/pdf'
                    if ext in ['.jpg', '.jpeg']: return 'image/jpeg'
                    if ext in ['.png']: return 'image/png'
                    return 'application/octet-stream'
                return "unknown"
                
            def from_buffer(self, buffer, mime=False):
                if mime:
                    return 'application/octet-stream'
                return "unknown"
        
        sys.modules['magic'] = type('magic', (), {
            'Magic': MockMagic,
            'MagicException': MockMagicException,
        })

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
