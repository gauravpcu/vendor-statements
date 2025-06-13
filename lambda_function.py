import json
import os
import logging
import serverless_wsgi

# Set up logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
